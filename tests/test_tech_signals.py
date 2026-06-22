"""tech_signals.py — 라벨/보정값 일관성 검증 (네트워크 없이 순수 로직만)."""
import pytest

import tech_signals as TS


@pytest.mark.parametrize("score,label", [
    (9, "강한 긍정 🚀"),
    (3, "긍정 ↑"),
    (0, "중립 →"),
    (-3, "부정 ↓"),
    (-9, "강한 부정 🚨"),
])
def test_label_bands(score, label):
    assert TS._label(score) == label


@pytest.mark.parametrize("score,adj", [
    (8, 3.0), (5, 2.0), (2, 1.0), (1, 0.0),
    (-2, -1.0), (-5, -2.0), (-8, -3.0),
])
def test_score_adj_bands(score, adj):
    assert TS._score_adj(score) == adj


def test_label_and_adj_agree_on_sign():
    """라벨이 긍정이면 보정도 양수, 부정이면 음수, 중립이면 0 — 불일치 없어야."""
    for score in range(-12, 13):
        label = TS._label(score)
        adj = TS._score_adj(score)
        if "긍정" in label:
            assert adj > 0, f"score={score}: {label} 인데 보정 {adj}"
        elif "부정" in label:
            assert adj < 0, f"score={score}: {label} 인데 보정 {adj}"
        else:
            assert adj == 0, f"score={score}: 중립인데 보정 {adj}"


def test_adj_capped_at_three():
    assert TS._score_adj(100) == 3.0
    assert TS._score_adj(-100) == -3.0
