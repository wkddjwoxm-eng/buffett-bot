"""results_io.py — Verdict 직렬화 왕복 + 데이터 보호 안전장치 검증."""
import json

import results_io as RIO
from buffett import evaluate


def test_verdict_roundtrip_preserves_core(quality_cheap):
    v = evaluate(quality_cheap, fetch_tech=False)
    d = RIO._verdict_to_dict(v)
    back = RIO._verdict_from_dict(d)
    assert back.f.ticker == v.f.ticker
    assert back.f.name == v.f.name
    assert back.total == v.total
    assert back.rating == v.rating
    assert back.metrics.roic == v.metrics.roic
    # hist는 용량 절약을 위해 직렬화에서 제거된다
    assert back.f.hist == {}


def test_clean_strips_nan_and_inf():
    cleaned = RIO._clean({"a": float("nan"), "b": float("inf"), "c": 1.5, "d": [float("nan"), 2]})
    assert cleaned["a"] is None
    assert cleaned["b"] is None
    assert cleaned["c"] == 1.5
    assert cleaned["d"] == [None, 2]


def test_dump_market_refuses_to_shrink(tmp_path, monkeypatch, quality_cheap):
    """기존 결과의 60% 미만으로 줄어드는 수집은 덮어쓰기를 거부해야 한다."""
    monkeypatch.setattr(RIO, "CACHE_DIR", tmp_path)
    path = tmp_path / "results_testmkt.json"
    # 기존에 100종목이 있다고 가정
    path.write_text(json.dumps({"market": "testmkt", "count": 100, "verdicts": []}),
                    encoding="utf-8")

    v = evaluate(quality_cheap, fetch_tech=False)
    RIO.dump_market([v], "testmkt")  # 1종목 < 100×0.6 → 거부

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["count"] == 100  # 기존 데이터 보존


def test_dump_market_refuses_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(RIO, "CACHE_DIR", tmp_path)
    path = tmp_path / "results_testmkt.json"
    path.write_text(json.dumps({"market": "testmkt", "count": 80, "verdicts": []}),
                    encoding="utf-8")
    RIO.dump_market([], "testmkt")  # 0종목 → 거부
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["count"] == 80


def test_dump_market_writes_when_healthy(tmp_path, monkeypatch, quality_cheap):
    monkeypatch.setattr(RIO, "CACHE_DIR", tmp_path)
    vs = [evaluate(quality_cheap, fetch_tech=False) for _ in range(3)]
    RIO.dump_market(vs, "testmkt")
    loaded, ts = RIO.load_market("testmkt")
    assert loaded is not None and len(loaded) == 3
    assert ts is not None
