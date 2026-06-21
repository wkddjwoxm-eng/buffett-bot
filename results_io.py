"""
사전수집 결과 직렬화 — 전체 종목 분석을 미리 계산해 JSON으로 저장/로드.

precompute.py가 매일 오전 8시·오후 8시에 전체 유니버스를 분석해
cache/results_kr.json, cache/results_us.json 으로 저장한다.
app.py는 이 파일을 즉시 읽어 '버튼 없이' 분석 결과를 보여준다.

Verdict(=Fundamentals+Metrics+TechSignal+valuation dict)를 통째로 직렬화한다.
같은 레포에서 배포되므로 클래스 정의가 일치 → 안전하게 복원 가능.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, fields
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from buffett import Fundamentals, Verdict
from metrics import Metrics
from tech_signals import TechSignal

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

_KST = timezone(timedelta(hours=9))


def _now_kst_str() -> str:
    return datetime.now(tz=_KST).strftime("%Y년 %m월 %d일 %H:%M KST 기준")


def _clean(o):
    """numpy 스칼라 → 파이썬 기본형, NaN/Inf → None 으로 재귀 정리."""
    # numpy 스칼라 처리
    try:
        import numpy as np
        if isinstance(o, np.generic):
            o = o.item()
    except Exception:
        pass
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return None
        return o
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def _verdict_to_dict(v: Verdict) -> dict:
    d = asdict(v)               # f, metrics, tech 까지 재귀 변환됨
    # 다년 시계열(hist)은 렌더링에 불필요하고 용량만 큼 → 제거
    if isinstance(d.get("f"), dict):
        d["f"]["hist"] = {}
    return _clean(d)


def _existing_count(path: Path) -> int:
    """기존 결과 파일의 종목 수(없으면 0)."""
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return int(payload.get("count") or len(payload.get("verdicts", [])))
    except Exception:
        return 0


def dump_market(verdicts: list[Verdict], market: str,
                generated_at: Optional[str] = None,
                min_keep_ratio: float = 0.6) -> Path:
    """결과를 cache/results_{market}.json 으로 저장.

    안전장치: 이번 수집이 비정상적으로 적으면(0개거나 기존의 60% 미만)
    기존 좋은 데이터를 덮어쓰지 않는다. (GitHub Actions IP가 야후에
    rate-limit 당해 빈 결과가 나오는 사고로부터 데이터를 보호)
    """
    path = CACHE_DIR / f"results_{market}.json"
    new_n = len(verdicts)
    old_n = _existing_count(path)

    if new_n == 0:
        print(f"  ⛔ [{market}] 수집 0개 — 기존 {old_n}개 데이터 보존(덮어쓰기 취소)")
        return path
    if old_n > 0 and new_n < old_n * min_keep_ratio:
        print(f"  ⛔ [{market}] 수집 {new_n}개 < 기존 {old_n}개의 {int(min_keep_ratio*100)}% "
              f"— rate-limit 의심, 기존 데이터 보존(덮어쓰기 취소)")
        return path

    import time as _time
    payload = {
        "market": market,
        "generated_at": generated_at or _now_kst_str(),
        "generated_epoch": _time.time(),   # 신선도 계산용(기계 판독)
        "count": new_n,
        "verdicts": [_verdict_to_dict(v) for v in verdicts],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"  ✅ [{market}] {new_n}개 저장 (기존 {old_n}개)")
    return path


def market_age_hours(market: str) -> Optional[float]:
    """결과 파일이 마지막으로 갱신된 후 경과 시간(시간 단위). 없으면 None."""
    import time as _time
    path = CACHE_DIR / f"results_{market}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        epoch = payload.get("generated_epoch")
        if epoch:
            return max(0.0, (_time.time() - float(epoch)) / 3600.0)
    except Exception:
        pass
    # epoch 없으면 파일 mtime으로 추정
    try:
        return max(0.0, (_time.time() - path.stat().st_mtime) / 3600.0)
    except Exception:
        return None


def _filter(cls, d: dict) -> dict:
    """dataclass 필드명에 해당하는 키만 남김 (스키마 변동에 안전)."""
    names = {f.name for f in fields(cls)}
    return {k: val for k, val in (d or {}).items() if k in names}


def _verdict_from_dict(d: dict) -> Verdict:
    f = Fundamentals(**_filter(Fundamentals, d.get("f") or {}))

    md = dict(d.get("metrics") or {})
    tech_d = md.pop("tech", None)
    tech = TechSignal(**_filter(TechSignal, tech_d)) if tech_d else None
    metrics = Metrics(tech=tech, **_filter(Metrics, md))

    return Verdict(
        f=f,
        quality=d.get("quality") or 0.0,
        value=d.get("value") or 0.0,
        total=d.get("total") or 0.0,
        rating=d.get("rating") or "관망",
        valuation=d.get("valuation") or {},
        metrics=metrics,
        reasons=d.get("reasons") or [],
        price_comment=d.get("price_comment") or "",
        flags=d.get("flags") or [],
    )


def load_market(market: str) -> tuple[Optional[list], Optional[str]]:
    """cache/results_{market}.json 로드 → (verdicts, generated_at) 또는 (None, None)."""
    path = CACHE_DIR / f"results_{market}.json"
    if not path.exists():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        verdicts = [_verdict_from_dict(d) for d in payload.get("verdicts", [])]
        # 점수 내림차순 정렬 보장
        verdicts.sort(key=lambda v: v.total, reverse=True)
        return verdicts, payload.get("generated_at")
    except Exception:
        return None, None
