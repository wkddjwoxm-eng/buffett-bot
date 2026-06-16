"""
워런 버핏 / 벤저민 그레이엄식 장기 가치투자 점수화 엔진 (시장 무관)

버핏의 투자 원칙을 정량화해서 한 종목을 0~100점으로 채점한다.
입력은 시장(국장/미장)에 상관없이 동일한 형태(Fundamentals)로 정규화돼서 들어온다.

버핏 체크리스트 4기둥:
  1. 수익성·해자 (Profitability & Moat)   30점 — 높고 꾸준한 ROE, 두툼한 마진
  2. 재무 안정성 (Financial Strength)      25점 — 낮은 부채, 넉넉한 유동성, 꾸준한 FCF
  3. 성장성 (Growth)                       20점 — 매출·이익의 장기 우상향
  4. 밸류에이션·안전마진 (Margin of Safety) 25점 — 싸게 사는가 (PER/PBR/Graham/FCF수익률)

핵심 철학:
  - "훌륭한 기업을 적당한 가격에" > "그저 그런 기업을 헐값에"
    → 품질(1~3기둥)과 가격(4기둥)을 분리해서 본다.
  - 좋은 회사라도 지금이 비싸면 "기다려라" + 적정 매수가를 제시한다.
  - 가장 좋아하는 보유기간은 '영원히'. 단기 신호는 보지 않는다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Fundamentals:
    """시장 무관 정규화 펀더멘털. datafetch.py가 채워서 넘겨준다."""
    ticker: str
    name: str
    market: str                  # "KR" | "US"
    currency: str                # "KRW" | "USD"
    sector: str = "Unknown"
    industry: str = ""

    price: Optional[float] = None
    market_cap: Optional[float] = None

    # --- 수익성·해자 ---
    roe: Optional[float] = None          # 자기자본이익률 (소수, 0.15 = 15%)
    roe_history: list[float] = field(default_factory=list)  # 다년 ROE (일관성 평가용)
    gross_margin: Optional[float] = None     # 매출총이익률 (가격결정력 = 해자 프록시)
    operating_margin: Optional[float] = None # 영업이익률
    net_margin: Optional[float] = None       # 순이익률

    # --- 성장성 ---
    revenue_cagr: Optional[float] = None     # 매출 연평균성장률
    earnings_cagr: Optional[float] = None     # 순이익 연평균성장률

    # --- 재무 안정성 ---
    debt_to_equity: Optional[float] = None   # 부채비율 (소수, 0.5 = 50%)
    current_ratio: Optional[float] = None    # 유동비율
    fcf: Optional[float] = None              # 잉여현금흐름
    fcf_yield: Optional[float] = None        # FCF / 시가총액

    # --- 주주환원 ---
    dividend_yield: Optional[float] = None   # 배당수익률 (소수)

    # --- 밸류에이션 ---
    per: Optional[float] = None
    pbr: Optional[float] = None
    eps: Optional[float] = None              # 주당순이익
    bps: Optional[float] = None              # 주당순자산
    shares: Optional[float] = None           # 발행주식수

    # --- 다년 시계열 (최신→과거). metrics/valuation 모듈이 사용 ---
    #   키: net_income, revenue, gross_profit, equity, shares, ocf, fcf,
    #       ebit, pretax, tax, total_assets, current_assets, current_liabilities,
    #       total_debt, long_term_debt, cash, capex, dep_amort, change_in_wc
    hist: dict = field(default_factory=dict)

    note: str = ""                           # 데이터 품질 등 비고


# ─────────────────────────────────────────────────────────────────────────
# 점수화: 작은 헬퍼 (구간별 점수)
# ─────────────────────────────────────────────────────────────────────────
def _band(value: Optional[float], thresholds: list[tuple[float, float]],
          higher_is_better: bool = True) -> float:
    """
    value를 thresholds 구간에 매핑해서 점수 반환.
    thresholds: [(기준값, 점수), ...] 내림차순(높을수록 좋음 기준).
    예) higher=True, [(0.20,12),(0.15,9),(0.10,5)] → value>=0.20이면 12점.
    값이 없으면 0점(보수적).
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    if higher_is_better:
        for thr, pts in thresholds:
            if value >= thr:
                return pts
        return 0.0
    else:  # 낮을수록 좋음 (부채비율 등)
        for thr, pts in thresholds:
            if value <= thr:
                return pts
        return 0.0


# ─────────────────────────────────────────────────────────────────────────
# 4기둥 채점
# ─────────────────────────────────────────────────────────────────────────
def score_profitability(f: Fundamentals, roic=None) -> tuple[float, list[str]]:
    """수익성·해자 — 30점. ROE·ROIC가 높고 꾸준한가 + 두툼한 마진."""
    notes = []
    s = 0.0

    # 금융업 전용: ROIC/매출총이익률 개념이 약함 → ROE + ROA(자산효율)로 본다
    if is_financial(f):
        roe_pts = _band(f.roe, [(0.15, 14), (0.12, 11), (0.10, 8), (0.08, 5), (0.05, 2)])
        s += roe_pts
        if f.roe is not None:
            notes.append(f"ROE {f.roe*100:.1f}% → {roe_pts:.0f}/14")
        ni = (f.hist.get("net_income") or [None])[0]
        ta = (f.hist.get("total_assets") or [None])[0]
        roa = (ni / ta) if (ni and ta) else None
        roa_pts = _band(roa, [(0.013, 13), (0.010, 10), (0.008, 7), (0.006, 4), (0.004, 2)])
        s += roa_pts
        if roa is not None:
            notes.append(f"ROA {roa*100:.2f}% → {roa_pts:.0f}/13")
        hist = [r for r in f.roe_history if r is not None]
        if len(hist) >= 3:
            above = sum(1 for r in hist if r >= 0.10)
            cons_pts = 3 * (above / len(hist))
            s += cons_pts
            notes.append(f"ROE 일관성 {above}/{len(hist)}년 → {cons_pts:.1f}/3")
        return min(s, 30.0), notes

    # ROE (10점) — 15% 이상이 버핏의 마지노선
    roe_pts = _band(f.roe, [(0.20, 10), (0.15, 7.5), (0.10, 4), (0.05, 1.5)])
    s += roe_pts
    if f.roe is not None:
        notes.append(f"ROE {f.roe*100:.1f}% → {roe_pts:.1f}/10")
    # ROIC (7점) — 투하자본이익률. 부채 레버리지를 걷어낸 진짜 자본효율 = 해자
    roic_pts = _band(roic, [(0.15, 7), (0.12, 5), (0.08, 3), (0.05, 1)])
    s += roic_pts
    if roic is not None:
        notes.append(f"ROIC {roic*100:.1f}% → {roic_pts:.0f}/7")
    # ROE 일관성 (3점)
    hist = [r for r in f.roe_history if r is not None]
    if len(hist) >= 3:
        above = sum(1 for r in hist if r >= 0.12)
        cons_pts = 3 * (above / len(hist))
        s += cons_pts
        notes.append(f"ROE 일관성 {above}/{len(hist)}년 → {cons_pts:.1f}/3")
    # 순이익률 (6점)
    nm_pts = _band(f.net_margin, [(0.20, 6), (0.10, 4), (0.05, 2)])
    s += nm_pts
    if f.net_margin is not None:
        notes.append(f"순이익률 {f.net_margin*100:.1f}% → {nm_pts:.0f}/6")
    # 매출총이익률 (4점) — 가격결정력(해자)의 대리지표
    gm_pts = _band(f.gross_margin, [(0.40, 4), (0.25, 2.5), (0.15, 1)])
    s += gm_pts
    if f.gross_margin is not None:
        notes.append(f"매출총이익률 {f.gross_margin*100:.1f}% → {gm_pts:.1f}/4")
    return min(s, 30.0), notes


def is_financial(f: Fundamentals) -> bool:
    """은행·보험·증권 등 금융업 — 부채/FCF를 일반 제조업 잣대로 보면 안 됨."""
    blob = f"{f.sector} {f.industry}".lower()
    return any(k in blob for k in ("financ", "bank", "insur", "capital market"))


def score_strength(f: Fundamentals) -> tuple[float, list[str]]:
    """재무 안정성 — 25점. 빚이 적고 현금이 도는 회사."""
    # 금융업: 레버리지가 곧 사업모델이고 FCF 개념이 약함 → 일반 잣대 미적용, 중립 처리.
    if is_financial(f):
        return 15.0, ["금융업 → 부채/FCF 잣대 미적용, 중립 15/25 (ROE·PBR로 판단)"]
    notes = []
    s = 0.0
    # 부채비율 (10점) — 낮을수록 좋음
    de_pts = _band(f.debt_to_equity, [(0.30, 10), (0.50, 8), (1.00, 5), (2.00, 2)],
                   higher_is_better=False)
    s += de_pts
    if f.debt_to_equity is not None:
        notes.append(f"부채비율 {f.debt_to_equity*100:.0f}% → {de_pts:.0f}/10")
    # 유동비율 (7점)
    cr_pts = _band(f.current_ratio, [(2.0, 7), (1.5, 5), (1.0, 3)])
    s += cr_pts
    if f.current_ratio is not None:
        notes.append(f"유동비율 {f.current_ratio:.2f} → {cr_pts:.0f}/7")
    # FCF 수익률 (8점) — 잉여현금이 꾸준히 도는가
    fy_pts = _band(f.fcf_yield, [(0.07, 8), (0.04, 6), (0.01, 3), (0.0, 1)])
    s += fy_pts
    if f.fcf_yield is not None:
        notes.append(f"FCF수익률 {f.fcf_yield*100:.1f}% → {fy_pts:.0f}/8")
    return min(s, 25.0), notes


def score_growth(f: Fundamentals) -> tuple[float, list[str]]:
    """성장성 — 20점. 매출·이익이 장기적으로 우상향하는가."""
    notes = []
    s = 0.0
    rev_pts = _band(f.revenue_cagr, [(0.10, 10), (0.05, 6), (0.02, 3), (0.0, 1)])
    s += rev_pts
    if f.revenue_cagr is not None:
        notes.append(f"매출성장 {f.revenue_cagr*100:.1f}%/yr → {rev_pts:.0f}/10")
    eps_pts = _band(f.earnings_cagr, [(0.10, 10), (0.05, 6), (0.02, 3), (0.0, 1)])
    s += eps_pts
    if f.earnings_cagr is not None:
        notes.append(f"이익성장 {f.earnings_cagr*100:.1f}%/yr → {eps_pts:.0f}/10")
    return min(s, 20.0), notes


def score_valuation(f: Fundamentals, eff_per=None, cyclical=False) -> tuple[float, list[str]]:
    """밸류에이션·안전마진 — 25점. 지금 사면 싼가. 경기민감주는 정상화PER 사용."""
    notes = []
    s = 0.0
    # PER (10점) — 경기민감주는 정상화PER로 사이클 착시 보정
    use_per = eff_per if (cyclical and eff_per) else f.per
    per_pts = _band(use_per, [(10, 10), (15, 8), (20, 5), (25, 2)],
                    higher_is_better=False) if (use_per and use_per > 0) else 0.0
    s += per_pts
    if use_per:
        tag = "정상화PER" if (cyclical and eff_per) else "PER"
        notes.append(f"{tag} {use_per:.1f} → {per_pts:.0f}/10")
    # PBR (6점)
    pbr_pts = _band(f.pbr, [(1.5, 6), (3.0, 4), (5.0, 2)],
                    higher_is_better=False) if (f.pbr and f.pbr > 0) else 0.0
    s += pbr_pts
    if f.pbr:
        notes.append(f"PBR {f.pbr:.2f} → {pbr_pts:.0f}/6")
    # 그레이엄 수: PER×PBR < 22.5 면 방어적 투자자에게 합리적 (5점)
    if use_per and f.pbr and use_per > 0 and f.pbr > 0:
        gn = use_per * f.pbr
        gn_pts = 5 if gn < 22.5 else (3 if gn < 40 else (1 if gn < 60 else 0))
        s += gn_pts
        notes.append(f"PER×PBR {gn:.1f}(<22.5 이상적) → {gn_pts}/5")
    # 배당 (4점) — 주주환원 보너스
    div_pts = _band(f.dividend_yield, [(0.03, 4), (0.02, 3), (0.01, 1)])
    s += div_pts
    if f.dividend_yield:
        notes.append(f"배당수익률 {f.dividend_yield*100:.1f}% → {div_pts:.0f}/4")
    return min(s, 25.0), notes


# ─────────────────────────────────────────────────────────────────────────
# 종합 평가  (고급 지표·밸류에이션은 metrics/valuation 모듈을 지연 임포트로 결합)
# ─────────────────────────────────────────────────────────────────────────
@dataclass
class Verdict:
    f: Fundamentals
    quality: float          # 1~3기둥 합 (최대 75)
    value: float            # 4기둥 (최대 25)
    total: float            # 0~100
    rating: str             # 강력매수후보 / 매수검토 / 우량주대기 / 관망 / 회피
    valuation: dict         # valuation.summary() 결과
    metrics: object         # metrics.Metrics (ROIC·오너이익·F스코어·플래그)
    reasons: list[str]      # 채점 근거
    price_comment: str      # 현재가 vs 적정가 코멘트
    flags: list[str]        # 레드플래그


def _has_severe_flag(flags: list[str]) -> bool:
    # 실제 적자(돈을 못 버는 회사)만 매수 대상에서 강제 제외.
    # 나머지(이익의 질·부채·희석 등)는 확신도를 낮추는 경고로만 취급.
    return any("적자 상태" in x for x in flags)


def evaluate(f: Fundamentals) -> Verdict:
    import metrics as _M           # 지연 임포트로 순환참조 회피
    import valuation as _V

    m = _M.compute(f)
    val = _V.summary(f, m)

    p, pn = score_profitability(f, m.roic)
    st, sn = score_strength(f)
    gr, gn = score_growth(f)
    va, vn = score_valuation(f, m.norm_per, m.cyclical)

    quality = p + st + gr            # 최대 75
    tech_adj = m.tech.score_adj if (m.tech and m.tech.score_adj) else 0.0
    total = quality + va + tech_adj  # 최대 103 (tech ±3 보정 반영)
    quality_pct = quality / 75
    severe = _has_severe_flag(m.flags)
    fscore_ok = (m.fscore is None) or (m.fscore >= 4)

    # 품질·가격·위험을 함께 본다 — 버핏식 등급
    if severe or quality_pct < 0.40:
        rating = "회피"
    elif quality_pct >= 0.70 and va >= 15 and fscore_ok:
        rating = "★ 강력 매수 후보"
    elif quality_pct >= 0.60 and va >= 10 and fscore_ok:
        rating = "매수 검토"
    elif quality_pct >= 0.70 and va < 10:
        rating = "우량주 · 가격 비쌈(대기)"   # 좋은 회사지만 지금은 비싸다
    elif quality_pct >= 0.45:
        rating = "관망"
    else:
        rating = "회피"

    # 현재가 vs 적정가치 코멘트
    pc = ""
    fair, buy = val.get("fair"), val.get("buy_below")
    if fair and f.price:
        c = "₩" if f.currency == "KRW" else "$"
        dec = 0 if f.currency == "KRW" else 2
        money = lambda v: f"{c}{v:,.{dec}f}"  # noqa: E731
        if f.price <= buy:
            pc = f"현재가 {money(f.price)} ≤ 매수권장가 {money(buy)} → 안전마진 충분 ✅"
        elif f.price <= fair:
            pc = (f"현재가 {money(f.price)}, 적정가치 {money(fair)}. "
                  f"매수권장가 {money(buy)}까지 눌리면 매력적")
        else:
            over = (f.price / fair - 1) * 100
            pc = (f"현재가 {money(f.price)}, 적정가치 {money(fair)} "
                  f"대비 {over:.0f}% 비쌈 → 매수권장가 {money(buy)} 이하 대기")

    reasons = (["[수익성·해자]"] + pn + ["[재무안정]"] + sn
               + ["[성장성]"] + gn + ["[밸류에이션]"] + vn)
    return Verdict(f=f, quality=quality, value=va, total=total, rating=rating,
                   valuation=val, metrics=m, reasons=reasons, price_comment=pc,
                   flags=m.flags)
