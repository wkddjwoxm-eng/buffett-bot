"""
고급 지표 — 버핏/그레이엄 정통 도구 + 위험 경고 엔진.

datafetch가 채운 다년 시계열(Fundamentals.hist)을 입력으로:
  - ROIC          투하자본이익률 — 해자(자본효율)의 진짜 척도
  - 오너이익        Owner Earnings — 버핏이 보는 '진짜 벌어들이는 현금'
  - 정상화 이익     경기민감주의 사이클 저점/고점 착시를 다년 평균으로 보정
  - F-Score        피오트로스키 9점 — 재무가 좋아지고 있는가
  - 레드플래그       희석·부채급증·마진하락·이익의 질 등 위험 신호
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from buffett import Fundamentals, is_financial
import tech_signals as _TS

DEFAULT_TAX = 0.22   # 실효세율 추정 불가 시 기본값


# ─────────────────────────────────────────────────────────────────────────
# 시계열 헬퍼
# ─────────────────────────────────────────────────────────────────────────
def _h(f: Fundamentals, key: str) -> list:
    return [v for v in f.hist.get(key, [])]


def _at(series: list, i: int) -> Optional[float]:
    return series[i] if (series and len(series) > i and series[i] is not None) else None


def _avg(series: list, n: int = 5) -> Optional[float]:
    vals = [v for v in series[:n] if v is not None]
    return sum(vals) / len(vals) if vals else None


def _ratio(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b


# ─────────────────────────────────────────────────────────────────────────
# 핵심 지표
# ─────────────────────────────────────────────────────────────────────────
def effective_tax(f: Fundamentals) -> float:
    tax = _at(_h(f, "tax"), 0)
    pretax = _at(_h(f, "pretax"), 0)
    r = _ratio(tax, pretax)
    if r is None or r < 0 or r > 0.4:
        return DEFAULT_TAX
    return r


def roic(f: Fundamentals) -> Optional[float]:
    """ROIC = 세후영업이익(NOPAT) / 투하자본. >12%면 자본을 잘 굴리는 회사."""
    ebit = _at(_h(f, "ebit"), 0)
    ic = _at(_h(f, "invested_capital"), 0)
    if ic is None:  # 없으면 총부채 + 자기자본 - 현금
        debt = _at(_h(f, "total_debt"), 0) or 0
        eq = _at(_h(f, "equity"), 0)
        cash = _at(_h(f, "cash"), 0) or 0
        ic = (debt + eq - cash) if eq is not None else None
    if ebit is None or ic is None or ic <= 0:
        return None
    nopat = ebit * (1 - effective_tax(f))
    return nopat / ic


def owner_earnings(f: Fundamentals) -> Optional[float]:
    """
    버핏의 오너이익 ≈ 순이익 + 감가상각 - 유지보수 capex.
    유지보수 capex는 보수적으로 min(|capex|, 감가상각)으로 근사
    (감가상각 = 자산 유지에 필요한 재투자 수준이라는 고전적 가정).
    성장 capex는 제외 → 성장기업의 진짜 현금창출력을 FCF보다 잘 반영.
    """
    ni = _at(_h(f, "net_income"), 0)
    da = _at(_h(f, "dep_amort"), 0) or 0
    capex = _at(_h(f, "capex"), 0)
    if ni is None:
        return None
    capex_abs = abs(capex) if capex is not None else da
    maint = min(capex_abs, da) if da else capex_abs
    return ni + da - maint


def normalized(f: Fundamentals) -> dict:
    """
    경기민감주 보정: 다년 평균 순이익으로 정상화 이익/EPS/PER 산출.
    그레이엄·실러(CAPE)의 '평균이익' 발상.
    """
    ni_avg = _avg(_h(f, "net_income"))
    out = {"norm_ni": ni_avg}
    if ni_avg and f.shares:
        out["norm_eps"] = ni_avg / f.shares
    if ni_avg and f.market_cap and ni_avg > 0:
        out["norm_per"] = f.market_cap / ni_avg
    # 정상화 ROE = 평균순이익 / 최근 자기자본
    eq = _at(_h(f, "equity"), 0)
    if ni_avg and eq:
        out["norm_roe"] = ni_avg / eq
    return out


def is_cyclical_distortion(f: Fundamentals) -> bool:
    """
    경기민감주 착시 판정: (1) 과거에 이익이 크게 꺾인 해가 있고(=변동성),
    (2) 현재 이익이 다년 평균과 20%+ 벌어진 경우만 True.
    꾸준히 우상향하는 성장주는 제외(정상화로 성장을 깎지 않기 위해).
    """
    ni = [v for v in _h(f, "net_income") if v is not None]
    ni_avg = _avg(_h(f, "net_income"))
    if len(ni) < 3 or not ni_avg or ni_avg <= 0:
        return False
    had_decline = any(ni[i] < ni[i + 1] * 0.85 for i in range(len(ni) - 1))  # 최신→과거
    deviates = abs(ni[0] / ni_avg - 1) > 0.20
    return had_decline and deviates


# ─────────────────────────────────────────────────────────────────────────
# 피오트로스키 F-Score (0~9)
# ─────────────────────────────────────────────────────────────────────────
def piotroski(f: Fundamentals) -> tuple[Optional[int], list[str]]:
    ni = _h(f, "net_income"); ocf = _h(f, "ocf")
    ta = _h(f, "total_assets"); ltd = _h(f, "long_term_debt")
    ca = _h(f, "current_assets"); cl = _h(f, "current_liabilities")
    rev = _h(f, "revenue"); gp = _h(f, "gross_profit")
    sh = _h(f, "shares_bs")
    if _at(ni, 1) is None or _at(ta, 1) is None:
        return None, []   # 2년치 없으면 계산 불가

    score = 0
    passed = []
    def add(cond, label):
        nonlocal score
        if cond:
            score += 1; passed.append("✓ " + label)
        else:
            passed.append("· " + label)

    roa0 = _ratio(_at(ni, 0), _at(ta, 0))
    roa1 = _ratio(_at(ni, 1), _at(ta, 1))
    add((_at(ni, 0) or 0) > 0, "순이익 흑자")
    add((_at(ocf, 0) or 0) > 0, "영업현금흐름 흑자")
    add(roa0 is not None and roa1 is not None and roa0 > roa1, "ROA 개선")
    add(_at(ocf, 0) is not None and _at(ni, 0) is not None
        and _at(ocf, 0) > _at(ni, 0), "영업현금흐름>순이익(이익의 질)")
    ltd0 = _ratio(_at(ltd, 0), _at(ta, 0)); ltd1 = _ratio(_at(ltd, 1), _at(ta, 1))
    add(ltd0 is not None and ltd1 is not None and ltd0 <= ltd1, "장기부채비율 하락")
    cr0 = _ratio(_at(ca, 0), _at(cl, 0)); cr1 = _ratio(_at(ca, 1), _at(cl, 1))
    add(cr0 is not None and cr1 is not None and cr0 > cr1, "유동비율 개선")
    add(_at(sh, 0) is not None and _at(sh, 1) is not None
        and _at(sh, 0) <= _at(sh, 1) * 1.01, "주식수 미증가(희석 없음)")
    gm0 = _ratio(_at(gp, 0), _at(rev, 0)); gm1 = _ratio(_at(gp, 1), _at(rev, 1))
    add(gm0 is not None and gm1 is not None and gm0 > gm1, "매출총이익률 개선")
    at0 = _ratio(_at(rev, 0), _at(ta, 0)); at1 = _ratio(_at(rev, 1), _at(ta, 1))
    add(at0 is not None and at1 is not None and at0 > at1, "자산회전율 개선")
    return score, passed


# ─────────────────────────────────────────────────────────────────────────
# 레드플래그
# ─────────────────────────────────────────────────────────────────────────
def red_flags(f: Fundamentals) -> list[str]:
    flags = []
    fin = is_financial(f)   # 금융업은 OCF·FCF·부채 잣대가 일반 기업과 다름
    ni = _h(f, "net_income"); ocf = _h(f, "ocf"); fcf = _h(f, "fcf")
    debt = _h(f, "total_debt"); eq = _h(f, "equity"); sh = _h(f, "shares_bs")
    rev = _h(f, "revenue")

    if (_at(ni, 0) or 0) < 0:
        flags.append("적자 상태 — 순이익 마이너스")
    elif _at(ni, 0) is not None and _at(ni, 1) is not None and _at(ni, 1) > 0 \
            and _at(ni, 0) < _at(ni, 1) * 0.7:
        flags.append(f"순이익 전년比 {(_at(ni,0)/_at(ni,1)-1)*100:.0f}% 급감")

    if not fin:
        # 이익의 질: 흑자인데 영업현금흐름이 순이익에 한참 못 미침
        if _at(ni, 0) and _at(ni, 0) > 0 and _at(ocf, 0) is not None \
                and _at(ocf, 0) < _at(ni, 0) * 0.5:
            flags.append("영업현금흐름이 순이익보다 크게 적음 — 이익의 질 의심")
        if _at(fcf, 0) is not None and _at(fcf, 0) < 0:
            flags.append("잉여현금흐름(FCF) 적자 — 버는 것보다 쓰는 게 많음")
        # 부채 급증
        if _at(debt, 0) is not None and _at(debt, 1) is not None and _at(debt, 1) > 0 \
                and _at(debt, 0) > _at(debt, 1) * 1.4 \
                and _at(eq, 0) and _at(debt, 0) > _at(eq, 0) * 0.3:
            flags.append(f"총부채 전년比 {(_at(debt,0)/_at(debt,1)-1)*100:.0f}% 급증")

    # 주식수 희석 — 단발 데이터 잡음(예: 우선주 포함 한 해만 튐) 배제 위해
    # 최소 2개 기간에서 의미있게(>2%) 증가했고 총 7%+ 늘었을 때만 '추세'로 인정.
    svals = [x for x in sh if x is not None]
    if len(svals) >= 3:
        ups = sum(1 for i in range(len(svals) - 1) if svals[i] > svals[i + 1] * 1.02)
        grew = svals[0] > svals[-1] * 1.07
        if ups >= 2 and grew:
            flags.append(f"발행주식 {(svals[0]/svals[-1]-1)*100:.0f}% 증가 추세 — 주주가치 희석")

    # 순이익률 2년 연속 하락
    nm = [_ratio(_at(ni, i), _at(rev, i)) for i in range(3)]
    if all(x is not None for x in nm) and nm[0] < nm[1] < nm[2]:
        flags.append("순이익률 2년 연속 하락 — 수익성 둔화")

    return flags


# ─────────────────────────────────────────────────────────────────────────
# 집계
# ─────────────────────────────────────────────────────────────────────────
@dataclass
class Metrics:
    roic: Optional[float] = None
    owner_earnings: Optional[float] = None
    owner_earnings_yield: Optional[float] = None   # OE / 시총
    norm_per: Optional[float] = None
    norm_eps: Optional[float] = None
    norm_roe: Optional[float] = None
    cyclical: bool = False
    fscore: Optional[int] = None
    fscore_detail: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    tech: Optional[object] = None   # tech_signals.TechSignal


def compute(f: Fundamentals, fetch_tech: bool = True) -> Metrics:
    oe = owner_earnings(f)
    norm = normalized(f)
    fs, fdetail = piotroski(f)
    tech = _TS.analyze(f.ticker) if fetch_tech else _TS.TechSignal()
    return Metrics(
        roic=roic(f),
        owner_earnings=oe,
        owner_earnings_yield=(oe / f.market_cap) if (oe and f.market_cap) else None,
        norm_per=norm.get("norm_per"),
        norm_eps=norm.get("norm_eps"),
        norm_roe=norm.get("norm_roe"),
        cyclical=is_cyclical_distortion(f),
        fscore=fs,
        fscore_detail=fdetail,
        flags=red_flags(f),
        tech=tech,
    )
