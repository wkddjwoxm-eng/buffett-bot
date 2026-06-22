"""valuation.py — 그레이엄수·2단계 DCF·역DCF·기대수익률·요약 검증."""
import math

import pytest

import valuation as V
from metrics import compute


# ── 그레이엄 수 ─────────────────────────────────────────────────────────────
def test_graham_number_formula():
    # √(22.5 × 10 × 80) = √18000 ≈ 134.16
    assert V.graham_number(10, 80) == pytest.approx(math.sqrt(18000))


def test_graham_number_none_for_nonpositive():
    assert V.graham_number(-1, 80) is None
    assert V.graham_number(10, 0) is None
    assert V.graham_number(None, 80) is None


# ── 2단계 DCF ───────────────────────────────────────────────────────────────
def test_dcf_none_for_nonpositive_cash():
    assert V.two_stage_dcf(0, 0.10) is None
    assert V.two_stage_dcf(-5, 0.10) is None


def test_dcf_monotonic_in_growth():
    low = V.two_stage_dcf(10, 0.02)
    high = V.two_stage_dcf(10, 0.12)
    assert low is not None and high is not None
    assert high > low


def test_dcf_monotonic_in_discount():
    cheap_money = V.two_stage_dcf(10, 0.08, discount=0.08 + 0.01)
    dear_money = V.two_stage_dcf(10, 0.08, discount=0.15)
    assert cheap_money > dear_money  # 할인율 낮을수록 현재가치 큼


def test_dcf_growth_is_capped():
    # 성장률 18% 초과는 18%로 캡 → 동일 결과
    assert V.two_stage_dcf(10, 0.30) == pytest.approx(V.two_stage_dcf(10, 0.18))


# ── 역DCF ──────────────────────────────────────────────────────────────────
def test_reverse_dcf_recovers_growth(quality_cheap):
    m = compute(quality_cheap, fetch_tech=False)
    implied = V.reverse_dcf(quality_cheap, m)
    assert implied is not None
    # 역산한 성장률을 다시 DCF에 넣으면 현재가 부근으로 수렴해야 한다
    cash_ps = V._base_cash_ps(quality_cheap, m)
    recon = V.two_stage_dcf(cash_ps, implied)
    assert recon == pytest.approx(quality_cheap.price, rel=0.05)


# ── 기대수익률 ──────────────────────────────────────────────────────────────
def test_expected_return_is_yield_plus_growth(quality_cheap):
    m = compute(quality_cheap, fetch_tech=False)
    er = V.expected_return(quality_cheap, m)
    assert er is not None
    assert er == pytest.approx(m.owner_earnings_yield + V._growth(quality_cheap), rel=1e-6)


# ── 종합 요약 ───────────────────────────────────────────────────────────────
def test_summary_fair_is_median_and_buy_has_margin(quality_cheap):
    m = compute(quality_cheap, fetch_tech=False)
    s = V.summary(quality_cheap, m)
    methods = s["methods"]
    assert "graham" in methods and "earnings" in methods
    vals = sorted(v for v in methods.values() if v and v > 0)
    n = len(vals)
    expect_fair = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    assert s["fair"] == pytest.approx(expect_fair)
    # 매수권장가는 적정가에 안전마진 25% 적용
    assert s["buy_below"] == pytest.approx(s["fair"] * (1 - V.MARGIN_OF_SAFETY))


def test_summary_margin_of_safety_sign(quality_cheap):
    m = compute(quality_cheap, fetch_tech=False)
    s = V.summary(quality_cheap, m)
    # mos_pct = 1 - price/fair. 적정가보다 싸면 +.
    assert s["mos_pct"] == pytest.approx(1 - quality_cheap.price / s["fair"], rel=1e-6)
