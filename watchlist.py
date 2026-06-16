"""
워치리스트 — 목표 매수가 트리거.

스크리닝에서 '우량하나 비쌈(대기)'으로 분류된 종목의 매수권장가를 저장해두고,
나중에 `--check`로 현재가가 목표가에 도달했는지 확인한다.
일회성 추천을 '지속형 조언'으로 바꾸는 장치.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

WATCH_FILE = Path(__file__).parent / "watchlist.json"


def load() -> dict:
    if WATCH_FILE.exists():
        try:
            return json.loads(WATCH_FILE.read_text())
        except Exception:
            return {}
    return {}


def save(data: dict):
    WATCH_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def add(ticker: str, name: str, currency: str, target: float, fair: float):
    data = load()
    data[ticker] = {
        "name": name, "currency": currency,
        "target": target, "fair": fair, "added": f"{date.today()}",
    }
    save(data)


def add_from_verdicts(verdicts) -> int:
    """
    대기(우량주 비쌈) 종목을 워치리스트에 등록. 등록 수 반환.
    단, 목표가까지 55% 넘게 빠져야 하는 '과도한 고평가'는 현실적 알람가가 아니라 제외.
    """
    n = 0
    for v in verdicts:
        buy = v.valuation.get("buy_below")
        if "대기" in v.rating and buy and v.f.price:
            drop_needed = (1 - buy / v.f.price)
            if drop_needed > 0.55:
                continue
            add(v.f.ticker, v.f.name, v.f.currency, buy, v.valuation.get("fair"))
            n += 1
    return n


def check(fetch_fn) -> list[str]:
    """저장된 워치리스트의 현재가를 다시 받아 목표가 도달 여부 점검."""
    data = load()
    lines = []
    for tk, w in data.items():
        f = fetch_fn(tk)
        if not f or not f.price:
            lines.append(f"  {w['name']} ({tk}): 가격 조회 실패")
            continue
        c = "₩" if w["currency"] == "KRW" else "$"
        price = f"{c}{f.price:,.0f}" if w["currency"] == "KRW" else f"{c}{f.price:,.2f}"
        target = f"{c}{w['target']:,.0f}" if w["currency"] == "KRW" else f"{c}{w['target']:,.2f}"
        if f.price <= w["target"]:
            lines.append(f"  🔔 {w['name']} ({tk}): 현재 {price} ≤ 목표 {target} — 매수 검토 구간 도달!")
        else:
            drop = (1 - w["target"] / f.price) * 100   # 목표가까지 필요한 하락폭
            lines.append(f"  · {w['name']} ({tk}): 현재 {price} (목표 {target}까지 -{drop:.0f}% 더 하락 필요)")
    return lines
