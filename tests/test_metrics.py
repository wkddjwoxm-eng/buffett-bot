"""metrics.py — ROIC·오너이익·정상화·F-Score·레드플래그 검증.

순수 계산 함수는 정확값(approx)으로, 판정 함수는 불변식으로 잠근다.
"""
import math

import pytest

import metrics as M
from buffett import Fundamentals


# ── effective_tax ─────────────────────────────────────────────────────────
def test_effective_tax_uses_actual_ratio():
    f = Fundamentals("T", "n", "KR", "KRW", hist={"tax": [30], "pretax": [100]})
    assert M.effective_tax(f) == pytest.approx(0.30)


def test_effective_tax_falls_back_when_out_of_range():
    # 음수 세율, 40% 초과, 결측 → 기본값(DEFAULT_TAX)
    for tax, pretax in [(-10, 100), (50, 100), (None, 100), (10, 0)]:
        f = Fundamentals("T", "n", "KR", "KRW", hist={"tax": [tax], "pretax": [pretax]})
        assert M.effective_tax(f) == M.DEFAULT_TAX


# ── ROIC ──────────────────────────────────────────────────────────────────
def test_roic_from_components():
    # EBIT 100, 실효세율 0.22 → NOPAT 78. 투하자본 = 부채200+자본800-현금100 = 900.
    f = Fundamentals("T", "n", "KR", "KRW", hist={
        "ebit": [100], "tax": [22], "pretax": [100],
        "total_debt": [200], "equity": [800], "cash": [100],
    })
    assert M.roic(f) == pytest.approx(78 / 900, rel=1e-6)


def test_roic_none_when_invested_capital_nonpositive():
    f = Fundamentals("T", "n", "KR", "KRW", hist={
        "ebit": [100], "total_debt": [0], "equity": [50], "cash": [100],
    })
    assert M.roic(f) is None  # 50-100 = -50 ≤ 0


# ── 오너이익 ────────────────────────────────────────────────────────────────
def test_owner_earnings_maintenance_capex_capped_at_dep():
    # 순이익100 + 감가상각50 - 유지보수capex min(80,50)=50 → 100
    f = Fundamentals("T", "n", "KR", "KRW", hist={
        "net_income": [100], "dep_amort": [50], "capex": [-80],
    })
    assert M.owner_earnings(f) == pytest.approx(100)


def test_owner_earnings_none_without_net_income():
    f = Fundamentals("T", "n", "KR", "KRW", hist={"dep_amort": [50]})
    assert M.owner_earnings(f) is None


# ── 정상화 ──────────────────────────────────────────────────────────────────
def test_normalized_uses_multiyear_average():
    f = Fundamentals("T", "n", "KR", "KRW", market_cap=800, shares=10,
                     hist={"net_income": [100, 80, 60], "equity": [400]})
    out = M.normalized(f)
    assert out["norm_ni"] == pytest.approx(80)        # (100+80+60)/3
    assert out["norm_eps"] == pytest.approx(8)        # 80/10
    assert out["norm_per"] == pytest.approx(10)       # 800/80
    assert out["norm_roe"] == pytest.approx(0.2)      # 80/400


def test_cyclical_distortion_true_for_volatile_peak():
    f = Fundamentals("T", "n", "KR", "KRW",
                     hist={"net_income": [150, 50, 100, 90]})
    assert M.is_cyclical_distortion(f) is True


def test_cyclical_distortion_false_for_steady_grower():
    f = Fundamentals("T", "n", "KR", "KRW",
                     hist={"net_income": [120, 110, 100, 90]})
    assert M.is_cyclical_distortion(f) is False


# ── 피오트로스키 F-Score ────────────────────────────────────────────────────
def test_piotroski_perfect_nine():
    f = Fundamentals("T", "n", "KR", "KRW", hist={
        "net_income":          [100, 50],
        "ocf":                 [120, 60],
        "total_assets":        [1000, 1000],
        "long_term_debt":      [100, 200],
        "current_assets":      [300, 200],
        "current_liabilities": [100, 100],
        "revenue":             [1000, 900],
        "gross_profit":        [400, 315],   # gm 0.40 vs 0.35
        "shares_bs":           [100, 100],
    })
    score, detail = M.piotroski(f)
    assert score == 9
    assert len(detail) == 9
    assert all(d.startswith("✓") for d in detail)


def test_piotroski_none_without_two_years():
    f = Fundamentals("T", "n", "KR", "KRW",
                     hist={"net_income": [100], "total_assets": [1000]})
    assert M.piotroski(f) == (None, [])


# ── 레드플래그 ──────────────────────────────────────────────────────────────
def test_red_flags_loss_detected(loss_maker):
    flags = M.red_flags(loss_maker)
    assert any("적자 상태" in x for x in flags)


def test_red_flags_clean_for_healthy(quality_cheap):
    flags = M.red_flags(quality_cheap)
    assert not any("적자 상태" in x for x in flags)


def test_red_flags_financial_skips_fcf_debt_rules():
    # 금융업은 FCF 적자/부채 급증 잣대를 적용하지 않는다
    f = Fundamentals("B", "은행", "KR", "KRW", sector="금융", industry="Banks",
                     hist={
                         "net_income": [100, 90], "ocf": [50, 40],
                         "fcf": [-999, -999],
                         "total_debt": [1000, 100], "equity": [500, 500],
                         "revenue": [200, 190],
                     })
    flags = M.red_flags(f)
    assert not any("FCF" in x or "부채" in x for x in flags)


# ── compute 통합 ────────────────────────────────────────────────────────────
def test_compute_offline_is_self_consistent(quality_cheap):
    m = M.compute(quality_cheap, fetch_tech=False)
    assert m.roic is not None and m.roic > 0
    assert m.owner_earnings is not None and m.owner_earnings > 0
    # 오너이익수익률 = 오너이익 / 시총
    assert m.owner_earnings_yield == pytest.approx(
        m.owner_earnings / quality_cheap.market_cap, rel=1e-6)
    assert m.fscore is not None and 0 <= m.fscore <= 9
    assert not math.isnan(m.roic)
