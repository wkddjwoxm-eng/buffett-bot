"""
전체 종목 사전 분석 — 매일 오전 8시·오후 8시 KST 자동 실행 (GitHub Actions).

유니버스 전체(국장·미장)를 버핏 점수로 분석해 결과를 통째로 저장한다.
  cache/results_kr.json,  cache/results_us.json
app.py는 이 파일을 즉시 읽어 '버튼 없이' 분석 결과를 보여준다.

기존 prefetch.py(원시 데이터만 캐시)와 달리, 점수·적정가·조언까지 전부 계산해 저장한다.
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from universe import get_universe
from datafetch import fetch
from buffett import evaluate
import results_io
import json
from pathlib import Path

_CACHE_DIR = Path(__file__).parent / "cache"


def collect_market_indicators() -> dict:
    """환율·기준금리 수집 후 cache/market_indicators.json 저장."""
    result = {"usd_krw": None, "jpy_krw_100": None, "us_rate": None, "kr_rate": "2.75%"}
    try:
        import yfinance as yf
        def _px(ticker):
            tk = yf.Ticker(ticker)
            v = tk.fast_info.get("lastPrice") or tk.info.get("regularMarketPrice")
            return float(v) if v else None
        usd = _px("USDKRW=X")
        jpy = _px("JPYKRW=X")
        irx = _px("^IRX")
        if usd: result["usd_krw"] = f"₩{usd:,.0f}"
        if jpy: result["jpy_krw_100"] = f"₩{jpy*100:,.1f}"
        if irx: result["us_rate"] = f"{irx:.2f}%"
    except Exception as e:
        print(f"  [indicators] 수집 실패: {e}")
    _CACHE_DIR.mkdir(exist_ok=True)
    (_CACHE_DIR / "market_indicators.json").write_text(
        json.dumps(result, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  [indicators] USD={result['usd_krw']} JPY100={result['jpy_krw_100']} US={result['us_rate']}")
    return result

# 뉴스(기술변곡점)까지 수집할지 — 환경변수로 끌 수 있음 (속도/요청량 조절)
FETCH_TECH = os.environ.get("PRECOMPUTE_TECH", "1") != "0"

_KST = timezone(timedelta(hours=9))


def precompute_market(market: str, workers: int = 16) -> int:
    tickers = [tk for tk, _, _ in get_universe(market)]
    total = len(tickers)
    print(f"[precompute] {market.upper()} — {total}개 종목 분석 시작 "
          f"(workers={workers}, tech={FETCH_TECH})")

    funds = []
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, tk, True): tk for tk in tickers}
        for fut in as_completed(futures):
            done += 1
            tk = futures[fut]
            try:
                f = fut.result()
                if f:
                    funds.append(f)
            except Exception as e:
                print(f"  ✗ {tk}: {e}")
            if done % 50 == 0:
                print(f"  수집 {done}/{total} (성공 {len(funds)})")

    print(f"[precompute] {market.upper()} 점수 계산 중… ({len(funds)}개)")
    verdicts = []
    for f in funds:
        try:
            verdicts.append(evaluate(f, fetch_tech=FETCH_TECH))
        except Exception as e:
            print(f"  ✗ evaluate {f.ticker}: {e}")
    verdicts.sort(key=lambda v: v.total, reverse=True)

    ts = datetime.now(tz=_KST).strftime("%Y년 %m월 %d일 %H:%M KST 기준")
    path = results_io.dump_market(verdicts, market, generated_at=ts)
    print(f"[precompute] {market.upper()} 완료 → {path.name} "
          f"({len(verdicts)}개, {ts})")
    return len(verdicts)


def precompute_all(workers: int = 16) -> None:
    collect_market_indicators()
    for mk in ("kr", "us"):
        precompute_market(mk, workers=workers)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("kr", "us"):
        precompute_market(target)
    else:
        precompute_all()
