"""
yfinance 통합 펀더멘털 수집기 (국장 + 미장)

- 미장: AAPL, KO 처럼 티커 그대로
- 국장: 6자리코드 + ".KS"(코스피) / ".KQ"(코스닥)  예) 005930.KS

yfinance가 .info / .financials / .balance_sheet / .cashflow 를 두 시장 모두 제공한다.
국장은 PER/PBR/EPS/BPS가 .info에 비어있는 경우가 많아 재무제표에서 직접 계산한다.
  PER = 시가총액 / 순이익,  PBR = 시가총액 / 자기자본
  EPS = 순이익 / 발행주식,  BPS = 자기자본 / 발행주식

야후 API는 429(rate limit)를 자주 던지므로 재시도 + 당일 로컬 캐시를 둔다.
"""
from __future__ import annotations

import json
import math
import time
from datetime import date
from pathlib import Path
from typing import Optional

import yfinance as yf

from buffett import Fundamentals

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────
# 작은 헬퍼
# ─────────────────────────────────────────────────────────────────────────
def _num(x) -> Optional[float]:
    """NaN/None/이상값을 None으로 정리."""
    try:
        if x is None:
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _row(df, *names) -> list[float]:
    """재무제표 df에서 여러 후보 라벨 중 처음 매칭되는 행을 (최신→과거) 리스트로."""
    if df is None or df.empty:
        return []
    for n in names:
        if n in df.index:
            s = df.loc[n]
            return [_num(v) for v in list(s)]
    return []


def _cagr(series_new_to_old: list[Optional[float]]) -> Optional[float]:
    """최신→과거 순서 리스트에서 연평균성장률. 시작값이 양수여야 의미 있음."""
    vals = [v for v in series_new_to_old if v is not None]
    if len(vals) < 2:
        return None
    new, old = vals[0], vals[-1]
    n = len(vals) - 1
    if old is None or old <= 0 or new is None or new <= 0:
        return None
    return (new / old) ** (1 / n) - 1


# ─────────────────────────────────────────────────────────────────────────
# 단일 종목 정규화
# ─────────────────────────────────────────────────────────────────────────
def _normalize(ticker: str, info: dict, fin, bs, cf) -> Fundamentals:
    is_kr = ticker.endswith((".KS", ".KQ"))
    currency = "KRW" if is_kr else "USD"
    market = "KR" if is_kr else "US"

    price = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice")) \
        or _num(info.get("previousClose"))
    mcap = _num(info.get("marketCap"))
    shares = _num(info.get("sharesOutstanding"))

    # 재무제표 다년 시계열 (최신→과거) — hist 딕셔너리에 전부 적재
    hist = {
        "net_income": _row(fin, "Net Income", "Net Income Common Stockholders",
                           "Net Income From Continuing Operation Net Minority Interest"),
        "revenue": _row(fin, "Total Revenue", "Operating Revenue"),
        "gross_profit": _row(fin, "Gross Profit"),
        "ebit": _row(fin, "EBIT", "Operating Income"),
        "pretax": _row(fin, "Pretax Income"),
        "tax": _row(fin, "Tax Provision"),
        "equity": _row(bs, "Stockholders Equity", "Total Stockholder Equity",
                       "Common Stock Equity"),
        "total_assets": _row(bs, "Total Assets"),
        "current_assets": _row(bs, "Current Assets"),
        "current_liabilities": _row(bs, "Current Liabilities"),
        "total_debt": _row(bs, "Total Debt"),
        "long_term_debt": _row(bs, "Long Term Debt"),
        "cash": _row(bs, "Cash And Cash Equivalents",
                     "Cash Cash Equivalents And Short Term Investments"),
        "invested_capital": _row(bs, "Invested Capital"),
        "shares_bs": _row(bs, "Ordinary Shares Number", "Share Issued"),
        "ocf": _row(cf, "Operating Cash Flow", "Total Cash From Operating Activities"),
        "capex": _row(cf, "Capital Expenditure", "Capital Expenditures"),
        "dep_amort": _row(cf, "Depreciation And Amortization",
                          "Depreciation Amortization Depletion", "Depreciation"),
        "change_in_wc": _row(cf, "Change In Working Capital"),
    }

    ni_hist = hist["net_income"]
    rev_hist = hist["revenue"]
    eq_hist = hist["equity"]

    ni = ni_hist[0] if ni_hist else None
    eq = eq_hist[0] if eq_hist else None

    # PER/PBR/EPS/BPS — .info 우선, 없으면 재무제표로 계산 (주로 국장)
    per = _num(info.get("trailingPE"))
    pbr = _num(info.get("priceToBook"))
    eps = _num(info.get("trailingEps"))
    bps = _num(info.get("bookValue"))
    if per is None and mcap and ni and ni > 0:
        per = mcap / ni
    if pbr is None and mcap and eq and eq > 0:
        pbr = mcap / eq
    if eps is None and ni and shares:
        eps = ni / shares
    if bps is None and eq and shares:
        bps = eq / shares

    # ROE 다년 (순이익/자기자본)
    roe_hist = []
    for i in range(min(len(ni_hist), len(eq_hist))):
        n_, e_ = ni_hist[i], eq_hist[i]
        if n_ is not None and e_ and e_ > 0:
            roe_hist.append(n_ / e_)
    roe = _num(info.get("returnOnEquity"))
    if roe is None and roe_hist:
        roe = roe_hist[0]

    # FCF 다년 시계열 = 영업현금흐름 + 자본지출(음수저장)
    fcf_hist = []
    ocf_h, capex_h = hist["ocf"], hist["capex"]
    for i in range(min(len(ocf_h), len(capex_h))):
        o, c = ocf_h[i], capex_h[i]
        fcf_hist.append((o + c) if (o is not None and c is not None) else None)
    hist["fcf"] = fcf_hist
    # 최신 FCF — .info 우선, 없으면 계산값
    fcf = _num(info.get("freeCashflow"))
    if fcf is None and fcf_hist and fcf_hist[0] is not None:
        fcf = fcf_hist[0]
    fcf_yield = (fcf / mcap) if (fcf and mcap) else None

    # 부채비율/배당 단위 정규화
    #   yfinance 1.4.x: debtToEquity, dividendYield 모두 %단위(예 79.5, 0.37) → /100
    de = _num(info.get("debtToEquity"))
    de = de / 100 if de is not None else None
    div = _num(info.get("dividendYield"))
    div = div / 100 if div is not None else None

    return Fundamentals(
        ticker=ticker,
        name=info.get("shortName") or info.get("longName") or ticker,
        market=market,
        currency=currency,
        sector=info.get("sector") or "Unknown",
        industry=info.get("industry") or "",
        price=price,
        market_cap=mcap,
        roe=roe,
        roe_history=roe_hist,
        gross_margin=_num(info.get("grossMargins")),
        operating_margin=_num(info.get("operatingMargins")),
        net_margin=_num(info.get("profitMargins")),
        revenue_cagr=_cagr(rev_hist),
        earnings_cagr=_cagr(ni_hist),
        debt_to_equity=de,
        current_ratio=_num(info.get("currentRatio")),
        fcf=fcf,
        fcf_yield=fcf_yield,
        dividend_yield=div,
        per=per,
        pbr=pbr,
        eps=eps,
        bps=bps,
        shares=shares,
        hist=hist,
    )


# ─────────────────────────────────────────────────────────────────────────
# 캐시 직렬화
# ─────────────────────────────────────────────────────────────────────────
CACHE_VERSION = "v2"   # 스키마 변경 시 올리면 자동 재수집


def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker.replace('.', '_')}_{CACHE_VERSION}_{date.today():%Y%m%d}.json"


def _to_dict(f: Fundamentals) -> dict:
    return f.__dict__.copy()


def _from_dict(d: dict) -> Fundamentals:
    return Fundamentals(**d)


# ─────────────────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────────────────
def fetch(ticker: str, use_cache: bool = True, retries: int = 3) -> Optional[Fundamentals]:
    """티커 하나의 정규화 펀더멘털을 가져온다. 실패 시 None."""
    cp = _cache_path(ticker)
    if use_cache and cp.exists():
        try:
            return _from_dict(json.loads(cp.read_text()))
        except Exception:
            pass

    last_err = None
    for attempt in range(retries):
        try:
            t = yf.Ticker(ticker)
            info = t.info
            if not info or info.get("marketCap") is None and info.get("currentPrice") is None:
                raise ValueError("빈 응답(상장폐지/티커오류 가능)")
            f = _normalize(ticker, info, t.financials, t.balance_sheet, t.cashflow)
            cp.write_text(json.dumps(_to_dict(f), ensure_ascii=False))
            return f
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (attempt + 1))   # 429 백오프
    print(f"  ⚠️  {ticker} 수집 실패: {repr(last_err)[:120]}")
    return None


def fetch_many(tickers: list[str], use_cache: bool = True,
               pause: float = 0.4) -> list[Fundamentals]:
    """여러 티커를 순차 수집(야후 rate limit 배려). 실패 종목은 건너뜀."""
    out = []
    for i, tk in enumerate(tickers, 1):
        print(f"  [{i}/{len(tickers)}] {tk} ...", flush=True)
        f = fetch(tk, use_cache=use_cache)
        if f:
            out.append(f)
        time.sleep(pause)
    return out
