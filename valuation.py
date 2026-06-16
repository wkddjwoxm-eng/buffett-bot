"""
밸류에이션 — "어느 금액대가 좋을지"를 입체적으로.

기존 단일 적정가치에 더해:
  - 오너이익 기반 2단계 DCF로 약세/기본/강세 시나리오 → 내재가치 '범위'
  - 역DCF: 지금 가격은 향후 몇 %의 성장을 가정하는가 (시장의 기대치)
  - 기대 연수익률: 오너이익수익률 + 성장 (멀티플 불변 가정, 버핏·멍거식)
  - 안전마진(%): 적정가치 대비 현재가가 얼마나 싼가
경기민감주는 정상화 이익으로 그레이엄/이익기반 적정가를 계산해 착시를 보정한다.
"""
from __future__ import annotations

import math
from typing import Optional

from buffett import Fundamentals
from metrics import Metrics

DISCOUNT_RATE = 0.10       # 기본 할인율 (요구수익률)
TERMINAL_GROWTH = 0.025    # 영구성장률
MARGIN_OF_SAFETY = 0.25    # 안전마진 25%
HORIZON = 10               # DCF 1단계 기간(년)


def graham_number(eps: Optional[float], bps: Optional[float]) -> Optional[float]:
    """√(22.5 × EPS × BPS). 방어적 투자자의 적정가 상한."""
    if eps and bps and eps > 0 and bps > 0:
        return math.sqrt(22.5 * eps * bps)
    return None


def two_stage_dcf(cash_ps: float, growth: float,
                  discount: float = DISCOUNT_RATE,
                  terminal: float = TERMINAL_GROWTH,
                  years: int = HORIZON) -> Optional[float]:
    """주당 현금흐름을 1단계 성장 + 영구성장 터미널로 할인한 주당 내재가치."""
    if not cash_ps or cash_ps <= 0:
        return None
    g = max(min(growth, 0.18), -0.05)
    if discount <= terminal:
        discount = terminal + 0.03
    pv, cash = 0.0, cash_ps
    for yr in range(1, years + 1):
        cash *= (1 + g)
        pv += cash / ((1 + discount) ** yr)
    terminal_val = cash * (1 + terminal) / (discount - terminal)
    pv += terminal_val / ((1 + discount) ** years)
    return pv


def _base_cash_ps(f: Fundamentals, m: Metrics) -> Optional[float]:
    """DCF 기준 주당 현금흐름: 오너이익 > FCF > 순이익 순으로 선택."""
    shares = f.shares or ((f.market_cap / f.price) if (f.market_cap and f.price) else None)
    if not shares:
        return None
    base = m.owner_earnings or f.fcf
    if base and base > 0:
        return base / shares
    if f.eps and f.eps > 0:   # 최후: EPS
        return f.eps
    return None


def _growth(f: Fundamentals) -> float:
    """성장 가정: 이익 CAGR을 보수적으로 [0, 12%] 캡. 없으면 4%."""
    g = f.earnings_cagr
    if g is None:
        g = f.revenue_cagr
    if g is None:
        return 0.04
    return max(min(g, 0.12), 0.0)


def scenarios(f: Fundamentals, m: Metrics) -> dict:
    """약세/기본/강세 내재가치 (성장·할인율 차등)."""
    cash_ps = _base_cash_ps(f, m)
    if not cash_ps:
        return {}
    g = _growth(f)
    out = {
        "bear": two_stage_dcf(cash_ps, max(g - 0.04, 0.0), discount=0.11),
        "base": two_stage_dcf(cash_ps, g, discount=0.10),
        "bull": two_stage_dcf(cash_ps, min(g + 0.03, 0.15), discount=0.09),
    }
    return {k: v for k, v in out.items() if v}


def reverse_dcf(f: Fundamentals, m: Metrics) -> Optional[float]:
    """현재가를 정당화하려면 향후 10년 몇 % 성장이 필요한가 (시장의 기대 성장률)."""
    cash_ps = _base_cash_ps(f, m)
    if not cash_ps or not f.price:
        return None
    lo, hi = -0.10, 0.50
    for _ in range(60):
        mid = (lo + hi) / 2
        val = two_stage_dcf(cash_ps, mid)
        if val is None:
            return None
        if val < f.price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def expected_return(f: Fundamentals, m: Metrics) -> Optional[float]:
    """기대 연수익률 ≈ 오너이익수익률 + 성장 (멀티플 불변 가정)."""
    oe_yield = m.owner_earnings_yield
    if oe_yield is None and f.fcf and f.market_cap:
        oe_yield = f.fcf / f.market_cap
    if oe_yield is None:
        if f.per and f.per > 0:
            oe_yield = 1 / f.per
        else:
            return None
    return oe_yield + _growth(f)


def summary(f: Fundamentals, m: Metrics) -> dict:
    """
    종합 밸류에이션 묶음.
    fair: 적정가치(여러 방법의 중앙값), buy_below: 안전마진 매수가,
    methods: 산출 내역, scenarios/implied_growth/exp_return/mos_pct 추가.
    """
    # 경기민감주는 정상화 EPS로 착시 보정
    eps = m.norm_eps if (m.cyclical and m.norm_eps) else f.eps
    methods = {}
    g = graham_number(eps, f.bps)
    if g:
        methods["graham"] = g
    if eps and eps > 0:
        methods["earnings"] = eps * 15        # 보수적 목표 PER 15
    sc = scenarios(f, m)
    if sc.get("base"):
        methods["dcf"] = sc["base"]

    vals = sorted(v for v in methods.values() if v and v > 0)
    fair = buy_below = None
    if vals:
        n = len(vals)
        fair = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        buy_below = fair * (1 - MARGIN_OF_SAFETY)

    mos_pct = (1 - f.price / fair) if (fair and f.price) else None  # +면 적정가보다 쌈
    return {
        "fair": fair,
        "buy_below": buy_below,
        "methods": methods,
        "scenarios": sc,
        "implied_growth": reverse_dcf(f, m),
        "exp_return": expected_return(f, m),
        "mos_pct": mos_pct,
        "used_normalized": bool(m.cyclical and m.norm_eps),
    }
