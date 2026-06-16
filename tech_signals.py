"""
기술변곡점 탐지 — yfinance 뉴스 키워드 기반.

종목별 최신 뉴스(제목+요약)를 스캔해서 기술/사업 모멘텀 변화 신호를 감지한다.
긍정 신호(HBM·AI·수주·특허 등)와 부정 신호(소송·적자·구조조정 등)를 가중합산해
TechSignal 객체로 반환한다. 점수는 buffett.evaluate()에서 보너스/패널티로 반영된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────
# 키워드 사전 (영문·한국어 혼용)
# ─────────────────────────────────────────────────────────────────────────
POSITIVE: dict[str, int] = {
    # 기술 변곡점 — 가중치 높음
    "HBM": 4, "high bandwidth memory": 4,
    "AI": 3, "artificial intelligence": 3, "generative ai": 3,
    "quantum": 3, "양자": 3,
    "autonomous driving": 3, "자율주행": 3, "fsd": 2,
    "next-generation": 2, "차세대": 2, "breakthrough": 2, "혁신": 1,
    "platform": 1, "ecosystem": 1, "플랫폼": 1,
    # 사업 이벤트
    "patent": 1, "특허": 1,
    "partnership": 2, "파트너십": 2, "MOU": 1, "협약": 1,
    "contract win": 2, "수주": 2, "대규모 수주": 3,
    "record revenue": 2, "record earnings": 2, "사상 최대": 2, "역대 최고": 2,
    "beat": 1, "어닝 서프라이즈": 2, "실적 호조": 2, "실적 개선": 1,
    "expansion": 1, "증설": 1, "capacity": 1,
    "acquisition": 1, "인수": 1, "merger": 1,
    "fda approval": 3, "approval": 2, "승인": 2, "허가": 2,
    "new product": 1, "launch": 1, "출시": 1, "신제품": 2,
    "buyback": 2, "자사주": 1, "dividend increase": 2, "배당 증가": 2,
    "upgrade": 2, "목표가 상향": 2, "투자의견 상향": 2,
}

NEGATIVE: dict[str, int] = {
    # 법적·규제 리스크
    "recall": -2, "리콜": -2,
    "lawsuit": -2, "소송": -2, "class action": -3,
    "fine": -1, "penalty": -2, "과징금": -2,
    "investigation": -2, "조사": -1, "압수수색": -3, "수사": -2,
    "sanction": -2, "제재": -2, "ban": -2,
    # 재무·사업 위기
    "bankruptcy": -4, "파산": -4, "부도": -4, "워크아웃": -3,
    "fraud": -4, "횡령": -4, "배임": -4, "회계부정": -4,
    "miss": -1, "어닝 쇼크": -3, "실적 부진": -2, "실적 악화": -2,
    "guidance cut": -2, "실적 하향": -2, "guidance lowered": -2,
    "layoff": -1, "대규모 감원": -2, "구조조정": -1,
    "ceo resign": -2, "대표 사임": -2, "경영진 교체": -1,
    "delay": -1, "지연": -1, "출시 연기": -2,
    "oversupply": -2, "공급과잉": -2, "재고 급증": -2,
    "downgrade": -2, "투자의견 하향": -2, "목표가 하향": -2,
    "market share loss": -2, "시장점유율 하락": -2,
    "competition intensifies": -1, "경쟁 심화": -1,
    "tariff": -1, "관세": -1,
    "impairment": -2, "손상차손": -2, "대규모 손실": -2,
}


# ─────────────────────────────────────────────────────────────────────────
# 결과 객체
# ─────────────────────────────────────────────────────────────────────────
@dataclass
class TechSignal:
    score: int = 0                            # 순 점수 (양수=긍정, 음수=부정)
    label: str = "중립 →"                     # 표시 레이블
    positive_hits: list[str] = field(default_factory=list)   # 감지된 긍정 키워드
    negative_hits: list[str] = field(default_factory=list)   # 감지된 부정 키워드
    news_count: int = 0                       # 스캔한 뉴스 수
    score_adj: float = 0.0                    # buffett 총점 보정값 (-3~+3)


def _label(score: int) -> str:
    if score >= 8:  return "강한 긍정 🚀"
    if score >= 4:  return "긍정 ↑"
    if score <= -8: return "강한 부정 🚨"
    if score <= -3: return "부정 ↓"
    return "중립 →"


def _score_adj(score: int) -> float:
    """총점(100점) 보정: 너무 크면 펀더멘털 점수가 묻힘 → 최대 ±3점으로 제한."""
    if score >= 8:  return 3.0
    if score >= 4:  return 2.0
    if score >= 2:  return 1.0
    if score <= -8: return -3.0
    if score <= -3: return -2.0
    if score <= -1: return -1.0
    return 0.0


# ─────────────────────────────────────────────────────────────────────────
# 분석 함수
# ─────────────────────────────────────────────────────────────────────────
def analyze(ticker: str, max_news: int = 15) -> TechSignal:
    """yfinance 최신 뉴스에서 키워드를 스캔해 TechSignal 반환."""
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker).news or []
    except Exception:
        return TechSignal()

    pos_hits: list[str] = []
    neg_hits: list[str] = []
    total = 0
    count = min(len(raw), max_news)

    for item in raw[:count]:
        # yfinance 뉴스 구조: content.title / content.summary (또는 구버전 title)
        content = item.get("content", {})
        if isinstance(content, dict):
            text = (content.get("title", "") + " " + content.get("summary", "")).lower()
        else:
            text = str(item.get("title", "")).lower()

        for kw, w in POSITIVE.items():
            if kw.lower() in text and kw not in pos_hits:
                total += w
                pos_hits.append(kw)

        for kw, w in NEGATIVE.items():
            if kw.lower() in text and kw not in neg_hits:
                total += w   # w는 음수
                neg_hits.append(kw)

    return TechSignal(
        score=total,
        label=_label(total),
        positive_hits=pos_hits[:6],
        negative_hits=neg_hits[:6],
        news_count=count,
        score_adj=_score_adj(total),
    )
