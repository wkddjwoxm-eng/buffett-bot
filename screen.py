#!/usr/bin/env python3
"""
버핏 봇 — 장기 가치투자 종목추천 / 투자조언 CLI (국장 + 미장)

사용법:
  python3 screen.py --market kr            # 국장 유니버스 스크리닝 + 포트폴리오 조언
  python3 screen.py --market us            # 미장
  python3 screen.py --market all           # 통합
  python3 screen.py 005930.KS AAPL KO      # 특정 종목 상세 조언
  python3 screen.py --market us --top 10   # 상세 조언 상위 10개
  python3 screen.py --market kr --watch     # 결과 중 '대기' 종목을 워치리스트에 등록
  python3 screen.py --check                 # 워치리스트 목표가 도달 점검
  python3 screen.py --market kr --no-cache  # 당일 캐시 무시

출력:
  1) 점수 랭킹 표 (총점 = 품질 75 + 가격 25, ROIC·F스코어 포함)
  2) 섹터별 평균 품질 — "어느 산업이 괜찮은지"
  3) 포트폴리오 조언 — 시장온도 / 지금매수 · 목표가대기 · 회피 / 섹터분산
  4) 상위 종목 상세 조언 — 적정가 범위·매수권장가·기대수익률·위험("어느 금액대가 좋을지")
"""
from __future__ import annotations

import argparse
import sys

import advisor
import watchlist as wl
from buffett import Verdict, evaluate
from datafetch import fetch, fetch_many
from universe import KR_UNIVERSE, US_UNIVERSE, get_universe

SECTOR_PHILOSOPHY = {
    "필수소비재": "버핏 최애. 브랜드·반복구매=해자, 불황에도 현금창출",
    "IT·플랫폼": "원칙은 '아는 사업만'. 애플은 소비재 브랜드로 봄",
    "헬스케어": "특허·규모의 해자. 경기방어적",
    "금융": "버핏의 본진(보험·카드·신용평가). ROE·ROA·자본배분이 핵심",
    "반도체·IT": "사이클 큼 — 저점 이익 때 PER 착시(정상화PER로 보정)",
    "2차전지·소재": "성장 매력 vs 자본집약·경쟁심화. 해자 검증 필요",
    "지주·소재": "자본집약·사이클. 저PBR 함정 주의",
    "통신": "현금흐름·고배당 안정형. 성장은 제한적",
}


def ticker_sector_map() -> dict[str, str]:
    m = {}
    for uni in (KR_UNIVERSE, US_UNIVERSE):
        for sector, items in uni.items():
            for tk, _ in items:
                m[tk] = sector
    return m


def print_ranking(verdicts: list[Verdict], sec_map: dict[str, str]):
    print("\n" + "=" * 92)
    print(" 버핏 점수 랭킹  (총점 100 = 품질 75 + 가격 25)")
    print("=" * 92)
    print(f"{'#':>2} {'종목':<16} {'섹터':<11} {'총점':>4} {'품질':>4} {'가격':>4}  "
          f"{'등급':<16} {'PER':>5} {'ROIC':>5} {'F':>3}")
    print("-" * 92)
    for i, v in enumerate(verdicts, 1):
        f, m = v.f, v.metrics
        sec = sec_map.get(f.ticker, f.sector)[:10]
        per = f"{f.per:.0f}" if f.per and f.per > 0 else "-"
        roic = f"{m.roic*100:.0f}%" if m.roic is not None else "-"
        fs = f"{m.fscore}" if m.fscore is not None else "-"
        print(f"{i:>2} {f.name[:15]:<16} {sec:<11} {v.total:>4.0f} {v.quality:>4.0f} "
              f"{v.value:>4.0f}  {v.rating:<16} {per:>5} {roic:>5} {fs:>3}")


def print_sector_summary(verdicts: list[Verdict], sec_map: dict[str, str]):
    print("\n" + "=" * 92)
    print(" 섹터별 평균 품질 점수  —  '어느 산업이 괜찮은지'")
    print("=" * 92)
    by_sec: dict[str, list[Verdict]] = {}
    for v in verdicts:
        by_sec.setdefault(sec_map.get(v.f.ticker, v.f.sector), []).append(v)
    rows = []
    for sec, vs in by_sec.items():
        avg_q = sum(x.quality for x in vs) / len(vs)
        avg_t = sum(x.total for x in vs) / len(vs)
        best = max(vs, key=lambda x: x.total)
        rows.append((avg_q, sec, avg_t, len(vs), best))
    rows.sort(reverse=True)
    for avg_q, sec, avg_t, n, best in rows:
        bar = "█" * round(avg_q / 75 * 24)
        print(f"  {sec:<11} 품질 {avg_q:4.0f}/75 |{bar:<24}| 총점 {avg_t:4.0f}  "
              f"({n}종목, 대표 {best.f.name[:14]})")
        if sec in SECTOR_PHILOSOPHY:
            print(f"              └ {SECTOR_PHILOSOPHY[sec]}")


def print_details(verdicts: list[Verdict]):
    print("\n" + "=" * 92)
    print(" 📋 종목별 상세 조언  —  '어느 금액대가 좋을지'")
    print("=" * 92)
    for v in verdicts:
        print()
        for line in advisor.advise(v):
            print(line)
        if v.metrics.fscore_detail:
            passed = [d[2:] for d in v.metrics.fscore_detail if d.startswith("✓")]
            print(f"   📊 F-Score 통과: {', '.join(passed) if passed else '없음'}")


def run(tickers, detail_all, top, use_cache, do_watch):
    sec_map = ticker_sector_map()
    print(f"\n📊 {len(tickers)}개 종목 펀더멘털 수집 중 (yfinance, 캐시 사용={use_cache})...")
    funds = fetch_many(tickers, use_cache=use_cache)
    if not funds:
        print("수집된 종목이 없습니다. 네트워크/티커를 확인하세요.")
        return
    verdicts = sorted((evaluate(f) for f in funds), key=lambda v: v.total, reverse=True)

    print_ranking(verdicts, sec_map)
    print_sector_summary(verdicts, sec_map)
    for line in advisor.portfolio(verdicts, sec_map):
        print(line)

    show = verdicts if detail_all else verdicts[:top]
    print_details(show)

    if do_watch:
        n = wl.add_from_verdicts(verdicts)
        print(f"\n  📌 '대기' 종목 {n}개를 워치리스트에 등록했습니다. "
              f"나중에 `python3 screen.py --check`로 목표가 도달을 확인하세요.")

    print("\n" + "=" * 92)
    print(" ⚠️  교육·연구용 참고 점수입니다. 자동매매가 아니라 후보를 추려주는 스크리너예요.")
    print("    실제 매수 전 사업보고서·해자의 지속성·경영진의 자본배분을 직접 검증하세요.")
    print("=" * 92)


def run_check():
    print("\n🔔 워치리스트 목표가 점검\n" + "-" * 60)
    lines = wl.check(lambda tk: fetch(tk, use_cache=False))
    if not lines:
        print("  워치리스트가 비어 있습니다. `--watch`로 먼저 등록하세요.")
    for ln in lines:
        print(ln)


def main():
    ap = argparse.ArgumentParser(description="버핏식 장기 가치투자 스크리너 / 투자조언")
    ap.add_argument("tickers", nargs="*", help="분석할 티커 (예: AAPL 005930.KS)")
    ap.add_argument("--market", choices=["kr", "us", "all"], help="유니버스 전체 스크리닝")
    ap.add_argument("--top", type=int, default=8, help="상세 조언할 상위 종목 수 (기본 8)")
    ap.add_argument("--watch", action="store_true", help="'대기' 종목을 워치리스트 등록")
    ap.add_argument("--check", action="store_true", help="워치리스트 목표가 도달 점검")
    ap.add_argument("--no-cache", action="store_true", help="당일 캐시 무시")
    args = ap.parse_args()

    if args.check:
        run_check(); return
    if args.market:
        tickers = [tk for tk, _, _ in get_universe(args.market)]
        run(tickers, False, args.top, not args.no_cache, args.watch)
    elif args.tickers:
        run(args.tickers, True, len(args.tickers), not args.no_cache, args.watch)
    else:
        ap.print_help()
        print("\n예) python3 screen.py --market kr")
        sys.exit(1)


if __name__ == "__main__":
    main()
