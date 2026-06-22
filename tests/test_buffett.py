"""buffett.py — 점수 밴드·4기둥·금융특례·종합등급 불변식 검증."""
import pytest

import buffett as B
from buffett import Fundamentals, evaluate


# ── _band ───────────────────────────────────────────────────────────────────
def test_band_higher_is_better():
    thr = [(0.20, 12), (0.15, 9), (0.10, 5)]
    assert B._band(0.25, thr) == 12
    assert B._band(0.15, thr) == 9
    assert B._band(0.09, thr) == 0
    assert B._band(None, thr) == 0
    assert B._band(float("nan"), thr) == 0


def test_band_lower_is_better():
    thr = [(0.30, 10), (0.50, 8), (1.00, 5)]
    assert B._band(0.20, thr, higher_is_better=False) == 10
    assert B._band(0.60, thr, higher_is_better=False) == 5
    assert B._band(2.00, thr, higher_is_better=False) == 0


# ── is_financial ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("sector,industry,expected", [
    ("금융·보험·증권", "Banks", True),
    ("Financials", "Insurance", True),
    ("Technology", "Semiconductors", False),
    ("필수소비재", "Beverages", False),
])
def test_is_financial(sector, industry, expected):
    f = Fundamentals("T", "n", "KR", "KRW", sector=sector, industry=industry)
    assert B.is_financial(f) is expected


# ── 4기둥 점수 상한/하한 ─────────────────────────────────────────────────────
def test_each_pillar_within_cap(quality_cheap):
    from metrics import compute
    m = compute(quality_cheap, fetch_tech=False)
    p, _ = B.score_profitability(quality_cheap, m.roic)
    st, _ = B.score_strength(quality_cheap)
    gr, _ = B.score_growth(quality_cheap)
    va, _ = B.score_valuation(quality_cheap, m.norm_per, m.cyclical)
    assert 0 <= p <= 30
    assert 0 <= st <= 25
    assert 0 <= gr <= 20
    assert 0 <= va <= 25


def test_growth_zero_for_missing():
    f = Fundamentals("T", "n", "KR", "KRW")  # CAGR 결측
    gr, _ = B.score_growth(f)
    assert gr == 0


def test_financial_strength_is_neutral_for_bank(bank):
    st, notes = B.score_strength(bank)
    assert st == 15.0
    assert any("금융업" in n for n in notes)


# ── 종합 평가 불변식 ─────────────────────────────────────────────────────────
def test_loss_maker_is_avoided(loss_maker):
    v = evaluate(loss_maker, fetch_tech=False)
    assert v.rating == "회피"
    assert any("적자" in fl for fl in v.flags)


def test_quality_cheap_scores_high(quality_cheap):
    v = evaluate(quality_cheap, fetch_tech=False)
    assert v.quality / 75 >= 0.70          # 고품질
    assert v.rating != "회피"
    assert 0 <= v.total <= 110
    # 종합 = 품질 + 가격 + 기술보정(없음)
    assert v.total == pytest.approx(v.quality + v.value, abs=3.001)


def test_verdict_carries_valuation_and_metrics(quality_cheap):
    v = evaluate(quality_cheap, fetch_tech=False)
    assert isinstance(v.valuation, dict)
    assert v.valuation.get("fair") is not None
    assert v.metrics.roic is not None
    assert v.price_comment  # 현재가 vs 적정가 코멘트가 비어있지 않음


def test_severe_flag_helper():
    assert B._has_severe_flag(["적자 상태 — 순이익 마이너스"]) is True
    assert B._has_severe_flag(["발행주식 10% 증가 추세 — 주주가치 희석"]) is False
