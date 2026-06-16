"""
투자조언 엔진 — 점수를 '사람이 읽는 조언'으로.

  - advise(verdict): 종목별 내러티브 (강점·해자, 적정 매수가, 위험, 한 줄 조언)
  - portfolio(verdicts): 포트폴리오 차원 — 시장 온도, '지금 매수 / 목표가 대기 / 회피'
    버킷 분류, 섹터 분산 제안. 버핏식 "쌀 때 사서 오래 보유"를 실천형으로.
"""
from __future__ import annotations

from buffett import Verdict, is_financial


def money(v, currency: str) -> str:
    if v is None:
        return "-"
    c = "₩" if currency == "KRW" else "$"
    return f"{c}{v:,.0f}" if currency == "KRW" else f"{c}{v:,.2f}"


def conviction_stars(v: Verdict) -> str:
    score = 0
    if v.quality / 75 >= 0.6: score += 1
    if v.quality / 75 >= 0.75: score += 1
    mos = v.valuation.get("mos_pct")
    if mos is not None and mos > 0: score += 1
    if mos is not None and mos > 0.25: score += 1
    if v.metrics.fscore is not None and v.metrics.fscore >= 7: score += 1
    if v.flags: score = max(0, score - 1)
    score = max(1, min(score, 5))
    return "★" * score + "☆" * (5 - score)


def _growth_read(v: Verdict) -> str:
    ig = v.valuation.get("implied_growth")
    real = v.f.earnings_cagr
    if ig is None:
        return ""
    if real is None:
        return f"시장은 향후 연 {ig*100:.0f}% 성장을 가정 중."
    if ig <= real:
        return (f"시장은 연 {ig*100:.0f}% 성장만 가정 — 실제 이익성장({real*100:.0f}%)보다 "
                f"보수적이라 저평가 신호.")
    if ig <= real + 0.05:
        return f"시장 기대 성장률 {ig*100:.0f}%로 실적과 대체로 부합."
    return (f"시장은 연 {ig*100:.0f}% 성장을 기대 — 실적({real*100:.0f}%)이 "
            f"못 따라가면 하락 위험.")


# ─────────────────────────────────────────────────────────────────────────
# 섹터별 맥락 설명 (투자 포인트 배경)
# ─────────────────────────────────────────────────────────────────────────
_SECTOR_CONTEXT: dict[str, str] = {
    # 국장 섹터
    "반도체·IT장비":    "AI 서버·HBM 수요 폭증으로 고부가 메모리 단가 상승 사이클 진입. 장기적으로 AI 인프라 투자 확대의 최대 수혜 섹터.",
    "인터넷·플랫폼·게임": "국내 최대 플랫폼 해자 보유. 광고·커머스·콘텐츠 수익이 고정비 레버리지로 이익 극대화. 게임은 IP 자산가치가 핵심.",
    "2차전지·소재·화학": "글로벌 전기차 보급 확대로 배터리·양극재·전해질 수요 장기 성장 예상. 단, 과잉공급 리스크와 중국 경쟁 모니터링 필요.",
    "자동차·부품·타이어": "하이브리드·전기차 전환 가속으로 국내 완성차의 글로벌 경쟁력 재평가. 전장·ADAS 부품 비중 상승이 이익구조 개선 요인.",
    "금융·보험·증권":   "금리 정상화 이후 안정적 순이자마진 유지. 자산 건전성 높고 자본비율 여유 있는 은행·보험은 배당 투자 관점에서 매력적.",
    "필수소비재·식품·음료": "내수 가격 전가력 확보. 경기 방어적 성격으로 불황기에도 매출 안정. 브랜드 해자가 장기 수익성 핵심.",
    "바이오·제약·헬스케어": "글로벌 임상 성공 시 기업가치 도약 가능. CDMO·ADC·비만 치료제 등 고성장 파이프라인 보유 기업 주목. 단, 임상 실패 리스크 존재.",
    "지주·철강·소재":   "저PBR·고배당 밸류업 정책 수혜 대상. 핵심 계열사 가치 대비 지주사 할인율이 크면 갭 해소 여지 있음.",
    "통신":            "안정적 ARPU와 5G 인프라 활용한 B2B 신사업 성장 기대. 배당수익률 높아 방어적 현금흐름 투자처로 적합.",
    "조선·방산·기계":   "글로벌 선박 교체 사이클 + LNG선 수주 급증. 방산은 지정학적 리스크로 수주잔고 역대 최고. 장기 수주잔고가 매출 가시성 높임.",
    "항공·운수·물류":   "엔데믹 이후 여행 수요 정상화. 항공화물 단가는 정상화됐으나 해운은 중동 이슈로 변동성 잔존.",
    "건설·부동산":      "주택 착공 회복 시 이익 개선 기대. 해외 수주(중동·동남아) 늘리는 건설사는 차별화 포인트.",
    "유통·소비재·서비스": "엔데믹 소비 정상화 수혜. 온라인·오프라인 옴니채널 전략 성공 여부가 관건.",
    "에너지·유틸리티":  "신재생 에너지 전환 가속으로 전력 인프라 투자 확대. 한국전력은 요금 현실화 여부가 수익성 핵심 변수.",
    "미디어·엔터테인먼트": "K-콘텐츠 글로벌 수요 지속 강세. 아티스트·IP 파이프라인의 질과 팬덤 확장성이 장기 성장 척도.",
    # 미장 섹터
    "IT·반도체":       "AI 빅사이클 수혜 최전선. 클라우드·AI 인프라 투자가 10년 장기 추세로 굳혀지며 데이터센터·GPU·소프트웨어 모두 성장. 기술 해자가 강한 기업은 프리미엄 밸류에이션 정당화.",
    "커뮤니케이션":     "광고·스트리밍·플랫폼 구독경제 성장. 메가캡 플랫폼은 네트워크 효과로 해자 견고. 미디어 전통사는 스트리밍 전환 비용이 변수.",
    "경기소비재":       "소비자 지출 트렌드 변화 수혜 — 전기차·온라인 쇼핑·여행 회복. 금리 민감도 높아 경기 사이클과 동조화.",
    "필수소비재":       "브랜드 파워와 가격 전가력 보유. 인플레 환경에서도 이익 방어. 배당 성장주로 장기 복리 수익 적합.",
    "헬스케어":         "고령화·GLP-1 비만 치료제·AI 신약 개발로 구조적 성장. 규제 리스크가 있으나 특허 해자와 파이프라인이 장기 가치 보존.",
    "금융":            "금리 정상화로 순이자마진 개선. 대형 투자은행·자산운용은 자본시장 활황 수혜. 버핏이 장기 보유한 섹터 — 자본 효율성이 높은 금융주 선호.",
    "산업재":           "미국 제조업 리쇼어링·인프라 투자법(IRA·CHIPS) 수혜. 방산은 지정학적 긴장 지속으로 수주 호조. 물류·철도는 경기 선행 지표.",
    "에너지":           "에너지 전환 장기화로 전통 에너지 수요 당분간 유지. 셰일 생산성 개선으로 낮은 손익분기점. 배당·자사주 매입 통한 주주환원 강화.",
    "소재":            "인프라 투자와 에너지 전환에 필수 원자재 수요 증가. 구리·리튬·희토류 수급 불균형 지속.",
    "부동산":           "금리 하락 국면에서 리츠(REIT)는 배당 매력 부각. 데이터센터·물류·의료 리츠는 구조적 성장 수혜.",
    "유틸리티":         "AI 데이터센터 전력 수요 급증으로 전력 인프라 투자 확대. 방어적 배당주이면서 AI 테마 수혜라는 이중 매력.",
}


def _sector_context(v: Verdict) -> str:
    """섹터 맥락 설명 반환. universe 섹터명 우선, 없으면 yfinance 섹터 키워드 매칭."""
    sec = v.f.sector or ""
    # 직접 매칭
    if sec in _SECTOR_CONTEXT:
        return _SECTOR_CONTEXT[sec]
    # 부분 매칭
    for k, txt in _SECTOR_CONTEXT.items():
        if any(kw in sec for kw in k.split("·")):
            return txt
    # yfinance 영문 섹터 → 대략 매핑
    eng_map = {
        "Technology": "IT·반도체",
        "Communication": "커뮤니케이션",
        "Consumer Discretionary": "경기소비재",
        "Consumer Staples": "필수소비재",
        "Health Care": "헬스케어",
        "Financials": "금융",
        "Industrials": "산업재",
        "Energy": "에너지",
        "Materials": "소재",
        "Real Estate": "부동산",
        "Utilities": "유틸리티",
    }
    for eng, kor in eng_map.items():
        if eng.lower() in sec.lower():
            return _SECTOR_CONTEXT.get(kor, "")
    return ""


def _metric_narrative(v: Verdict) -> list[str]:
    """지표 기반 '왜 매수/주의인가' 설명 문장 생성."""
    f, m, val = v.f, v.metrics, v.valuation
    lines = []

    # PER 해석
    per = m.norm_per if m.norm_per is not None else f.per
    if per is not None and per > 0:
        if per < 10:
            lines.append(f"PER {per:.1f}배 — 이익 대비 주가가 매우 싼 구간. 시장이 과도하게 저평가 중.")
        elif per < 15:
            lines.append(f"PER {per:.1f}배 — 합리적인 밸류에이션. 이익 성장을 감안하면 매력적인 수준.")
        elif per < 25:
            lines.append(f"PER {per:.1f}배 — 적정~다소 높은 수준. 이익 성장이 뒷받침돼야 정당화 가능.")
        else:
            lines.append(f"PER {per:.1f}배 — 고평가 구간. 높은 성장률 지속이 전제되어야 함.")
    if m.norm_per and f.per and abs(m.norm_per - f.per) > 5:
        lines.append(f"(현재 PER {f.per:.1f}배 vs 정상화 PER {m.norm_per:.1f}배 — 사이클 저점이면 정상화 기준이 더 적합)")

    # PBR
    if f.pbr is not None and f.pbr > 0:
        if f.pbr < 1.0:
            lines.append(f"PBR {f.pbr:.1f}배 — 순자산 아래 가격. 청산가치 이하 매수로 하방 안전판 존재.")
        elif f.pbr < 2.0:
            lines.append(f"PBR {f.pbr:.1f}배 — 자산 대비 적정한 수준.")

    # ROIC
    if m.roic is not None:
        if m.roic >= 0.20:
            lines.append(f"ROIC {m.roic*100:.0f}% — 투하자본 대비 탁월한 수익률. 강력한 경제적 해자의 증거.")
        elif m.roic >= 0.12:
            lines.append(f"ROIC {m.roic*100:.0f}% — 자본비용을 초과하는 양질의 수익성 유지 중.")

    # ROE
    if f.roe is not None:
        if f.roe >= 0.20:
            lines.append(f"ROE {f.roe*100:.0f}% — 자기자본 대비 높은 이익 창출력. 버핏이 중시하는 핵심 지표.")

    # 매출총이익률 → 가격 결정력
    if f.gross_margin is not None and not is_financial(f):
        if f.gross_margin >= 0.50:
            lines.append(f"매출총이익률 {f.gross_margin*100:.0f}% — 높은 가격 결정력. 경쟁사가 쉽게 따라오기 어려운 제품력·브랜드 해자.")
        elif f.gross_margin >= 0.30:
            lines.append(f"매출총이익률 {f.gross_margin*100:.0f}% — 안정적인 제품 마진 유지 중.")

    # FCF
    if not is_financial(f) and f.fcf is not None:
        if f.fcf > 0:
            cur_sym = "₩" if f.currency == "KRW" else "$"
            lines.append(f"잉여현금흐름(FCF) {cur_sym}{abs(f.fcf)/1e8:.0f}억 흑자 — 배당·자사주·재투자 여력 충분.")
        elif f.fcf < 0:
            lines.append("FCF 적자 — 현재 투자 단계이거나 수익화 구조 검토 필요.")

    # 성장률
    if f.earnings_cagr is not None:
        if f.earnings_cagr >= 0.20:
            lines.append(f"이익 CAGR {f.earnings_cagr*100:.0f}% — 가파른 이익 성장세. 복리 효과로 장기 가치 상승 기대.")
        elif f.earnings_cagr >= 0.08:
            lines.append(f"이익 CAGR {f.earnings_cagr*100:.0f}% — 꾸준한 이익 성장. 안정적 장기 보유 적합.")
        elif f.earnings_cagr < -0.05:
            lines.append(f"이익 CAGR {f.earnings_cagr*100:.0f}% — 이익 감소 추세. 반등 조건 확인 필요.")

    # F-Score
    if m.fscore is not None:
        if m.fscore >= 7:
            lines.append(f"피오트로스키 F-Score {m.fscore}/9 — 재무 건전성 우수. 수익성·레버리지·효율성 모두 개선 추세.")
        elif m.fscore <= 3:
            lines.append(f"피오트로스키 F-Score {m.fscore}/9 — 재무 체력 취약. 여러 지표 동시 악화 중.")

    # 배당
    if f.dividend_yield and f.dividend_yield > 0.03:
        lines.append(f"배당수익률 {f.dividend_yield*100:.1f}% — 보유 중에도 안정적 현금흐름 수취 가능.")

    # 내부자 지분율
    if f.insider_pct is not None and f.insider_pct >= 0.10:
        lines.append(f"내부자 지분율 {f.insider_pct*100:.1f}% — 경영진이 직접 대규모 투자. 주주와 이해관계 일치.")
    elif f.insider_pct is not None and f.insider_pct >= 0.05:
        lines.append(f"내부자 지분율 {f.insider_pct*100:.1f}% — 경영진의 적정 수준 투자로 이해관계 어느 정도 일치.")

    # 자사주 매입
    if getattr(m, "buyback_signal", False):
        lines.append("최근 자사주 매입 감지 — 경영진이 주가를 저평가로 판단한 신호.")

    # 이자보상비율
    ic = getattr(m, "interest_coverage", None)
    if ic is not None:
        if ic >= 10:
            lines.append(f"이자보상비율 {ic:.1f}배 — 이자 부담 매우 낮음. 금리 상승에도 안전.")
        elif ic < 3:
            lines.append(f"이자보상비율 {ic:.1f}배 — 이자 부담이 큼. 금리 상승 시 수익성 악화 위험.")

    # 배당 성장 연속성
    div_streak = getattr(f, 'div_growth_streak', 0)
    if div_streak >= 10:
        lines.append(f"배당 {div_streak}년 연속 성장 — '배당 귀족' 수준. 버핏이 선호하는 주주환원 우선 기업.")
    elif div_streak >= 5:
        lines.append(f"배당 {div_streak}년 연속 성장 — 안정적인 주주환원 문화 정착.")
    elif div_streak >= 3:
        lines.append(f"배당 {div_streak}년 연속 성장 — 배당 성장 초기 진입.")

    # EPS 연속 성장
    eps_streak = getattr(f, 'eps_beat_streak', 0)
    if eps_streak >= 4:
        lines.append(f"분기 EPS {eps_streak}회 연속 성장 — 실적 모멘텀 강화 중.")
    elif eps_streak >= 2:
        lines.append(f"분기 EPS {eps_streak}회 연속 성장 — 최근 이익 회복세.")

    # D/E 개선
    if getattr(f, 'de_improving', False):
        lines.append("부채비율 개선 추세 — 재무구조가 점진적으로 좋아지는 중.")

    return lines


def advise(v: Verdict) -> list[str]:
    """종목 한 개의 조언 블록(여러 줄)."""
    f, m, val = v.f, v.metrics, v.valuation
    cur = f.currency
    out = []
    out.append(f"[{v.rating}]  {f.name} ({f.ticker})  ·  {f.sector}")
    out.append(f"   종합 {v.total:.0f}/100 (품질 {v.quality:.0f}/75 · 가격 {v.value:.0f}/25)  "
               f"확신도 {conviction_stars(v)}")

    # 섹터 맥락 — "왜 이 섹터가 지금 좋은가"
    ctx = _sector_context(v)
    if ctx:
        out.append(f"   🌐 섹터 배경: {ctx}")

    # 지표 기반 내러티브 — "왜 이 종목이 싸거나 좋은가"
    metric_lines = _metric_narrative(v)
    if metric_lines:
        out.append("   📊 주요 지표 해석:")
        for ln in metric_lines:
            out.append(f"      • {ln}")

    # 강점 요약 (한 줄)
    moat = []
    if f.roe is not None: moat.append(f"ROE {f.roe*100:.0f}%")
    if m.roic is not None: moat.append(f"ROIC {m.roic*100:.0f}%")
    per = m.norm_per if m.norm_per is not None else f.per
    if per is not None and per > 0: moat.append(f"PER {per:.1f}배")
    if f.pbr is not None and f.pbr > 0: moat.append(f"PBR {f.pbr:.1f}배")
    if not is_financial(f) and f.gross_margin is not None:
        moat.append(f"매출총이익률 {f.gross_margin*100:.0f}%")
    if m.fscore is not None: moat.append(f"F-Score {m.fscore}/9")
    if moat:
        out.append("   🏰 지표 요약: " + " · ".join(moat))

    # 가격 — 시나리오 범위 + 매수권장 + 안전마진
    sc = val.get("scenarios", {})
    if val.get("fair"):
        rng = ""
        if sc.get("bear") and sc.get("bull"):
            rng = f" (약세 {money(sc['bear'],cur)} ~ 강세 {money(sc['bull'],cur)})"
        line = (f"   💰 현재가 {money(f.price,cur)} | 적정가치 {money(val['fair'],cur)}{rng} | "
                f"매수권장 {money(val['buy_below'],cur)} 이하")
        out.append(line)
        mos = val.get("mos_pct")
        extra = []
        if mos is not None:
            extra.append(f"안전마진 {mos*100:+.0f}%")
        if val.get("exp_return") is not None:
            extra.append(f"기대 연수익률 {val['exp_return']*100:.0f}%")
        if m.cyclical:
            extra.append("정상화이익 기준(사이클 보정)")
        if extra:
            out.append("      " + " · ".join(extra))
    gr = _growth_read(v)
    if gr:
        out.append(f"      📈 {gr}")

    # 기술변곡점 신호
    tech = getattr(v.metrics, "tech", None)
    if tech and tech.news_count > 0:
        hits = []
        if tech.positive_hits:
            hits.append("긍정: " + ", ".join(tech.positive_hits[:3]))
        if tech.negative_hits:
            hits.append("부정: " + ", ".join(tech.negative_hits[:3]))
        detail = f"  ({' / '.join(hits)})" if hits else ""
        out.append(f"   📡 기술·사업 신호: {tech.label}{detail}  (뉴스 {tech.news_count}건 스캔)")

    # 위험
    if v.flags:
        out.append("   ⚑ 위험 요인: " + " / ".join(v.flags))

    # 최종 한 줄 조언
    out.append("   👉 " + _one_liner(v))
    return out


def _one_liner(v: Verdict) -> str:
    f, m, val = v.f, v.metrics, v.valuation
    cur = f.currency
    buy = val.get("buy_below")
    per = m.norm_per if m.norm_per is not None else f.per
    per_str = f" (PER {per:.0f}배)" if per and per > 0 else ""

    if v.rating == "회피":
        return "조언: 매수 대상에서 제외. " + (v.flags[0] if v.flags else "지표가 기준에 미달.")
    if f.price and buy and f.price <= buy:
        return (f"조언: 지금 가격이 안전마진 구간{per_str}. "
                f"분할 매수로 모아가도 좋은 자리. 3~5년 보유 관점 추천.")
    if "대기" in v.rating:
        if buy and f.price:
            down = (1 - buy / f.price) * 100
            if down > 55:
                return ("조언: 사업은 훌륭하나 현재가가 적정가치를 크게 초과(과도한 고평가). "
                        "지금은 관심 보류 — 큰 폭 조정이나 이익 레벨업을 확인하고 재검토.")
            return (f"조언: 사업은 훌륭하나 비쌈{per_str}. {money(buy,cur)}(약 -{down:.0f}%)까지 "
                    f"눌릴 때를 노려 워치리스트에 등록.")
        return "조언: 우량하나 현재가가 부담. 조정 시 매수."
    if v.rating == "매수 검토":
        return (f"조언: 품질·가격 균형 양호{per_str}. "
                f"추가 점검(해자 지속성·경영진) 후 분할 매수 검토.")
    return "조언: 적극적 매수 신호는 아님. 더 싼 가격이나 실적 개선을 기다리며 관찰."


# ─────────────────────────────────────────────────────────────────────────
# 포트폴리오 차원
# ─────────────────────────────────────────────────────────────────────────
def _bucket(v: Verdict) -> str:
    f, val = v.f, v.valuation
    buy = val.get("buy_below")
    if v.rating == "회피":
        return "avoid"
    if v.rating in ("★ 강력 매수 후보", "매수 검토"):
        return "buy"
    if f.price and buy and f.price <= buy:
        return "buy"
    if "대기" in v.rating:
        return "wait"
    return "watch"


def market_temperature(verdicts: list[Verdict]) -> list[str]:
    n = len(verdicts)
    buy = sum(1 for v in verdicts if _bucket(v) == "buy")
    wait = sum(1 for v in verdicts if _bucket(v) == "wait")
    avoid = sum(1 for v in verdicts if _bucket(v) == "avoid")
    buy_ratio = buy / n if n else 0
    ers = [v.valuation.get("exp_return") for v in verdicts if v.valuation.get("exp_return") is not None]
    avg_er = (sum(ers) / len(ers)) if ers else None

    out = [f"🌡️  시장 온도: {n}종목 중 지금매수 {buy} · 우량주대기 {wait} · 회피 {avoid}"]
    if avg_er is not None:
        out.append(f"    유니버스 평균 기대 연수익률 ≈ {avg_er*100:.0f}%")
    if buy_ratio < 0.15:
        out.append("    → 살 게 별로 없는 '비싼 장'. 버핏: 무리하지 말고 현금 들고 기다릴 때.")
    elif buy_ratio < 0.35:
        out.append("    → 선별적 기회 존재. 안전마진 확실한 소수만 골라 담을 국면.")
    else:
        out.append("    → 저평가 종목이 꽤 보이는 우호적 국면. 분산해서 적극 매수 검토.")
    return out


def portfolio(verdicts: list[Verdict], sec_map: dict) -> list[str]:
    vs = sorted(verdicts, key=lambda v: (v.valuation.get("exp_return") or -9, v.total),
                reverse=True)
    out = ["", "=" * 92, " 💼 포트폴리오 조언  —  '지금 무엇을, 얼마에, 왜'", "=" * 92]
    out += market_temperature(verdicts)

    buys = [v for v in vs if _bucket(v) == "buy"]
    waits = [v for v in vs if _bucket(v) == "wait"]
    avoids = [v for v in vs if _bucket(v) == "avoid"]

    out.append("\n  ✅ 지금 사도 좋은 후보 (안전마진 또는 품질·가격 균형):")
    if buys:
        for v in buys[:8]:
            sec = sec_map.get(v.f.ticker, v.f.sector)
            er = v.valuation.get("exp_return")
            er_s = f"기대수익 {er*100:.0f}%" if er is not None else ""
            out.append(f"     • {v.f.name[:16]:16} [{sec}]  {money(v.f.price,v.f.currency)} "
                       f"→ 적정 {money(v.valuation.get('fair'),v.f.currency)}  {er_s}  {conviction_stars(v)}")
    else:
        out.append("     (없음 — 지금은 안전마진을 주는 종목이 없다. 기다림도 전략이다.)")

    out.append("\n  ⏳ 목표가 대기 워치리스트 (우량하나 비쌈 — 이 가격에 알람):")
    if waits:
        for v in waits[:8]:
            buy = v.valuation.get("buy_below")
            down = (1 - buy / v.f.price) * 100 if (buy and v.f.price) else None
            if down is not None and down > 55:
                out.append(f"     • {v.f.name[:16]:16} 현재 {money(v.f.price,v.f.currency)} — "
                           f"과도한 고평가(목표가 -{down:.0f}%), 관심 보류  품질 {v.quality:.0f}/75")
            else:
                d_s = f"(-{down:.0f}%)" if down is not None else ""
                out.append(f"     • {v.f.name[:16]:16} 현재 {money(v.f.price,v.f.currency)} → "
                           f"목표 {money(buy,v.f.currency)} {d_s}  품질 {v.quality:.0f}/75")
    else:
        out.append("     (없음)")

    if avoids:
        out.append("\n  🚫 회피:")
        for v in avoids[:6]:
            why = v.flags[0] if v.flags else "지표 기준 미달"
            out.append(f"     • {v.f.name[:16]:16} — {why}")

    if buys:
        secs = {}
        for v in buys[:8]:
            secs.setdefault(sec_map.get(v.f.ticker, v.f.sector), 0)
            secs[sec_map.get(v.f.ticker, v.f.sector)] += 1
        out.append("\n  🧩 분산 제안:")
        if len(secs) == 1:
            out.append(f"     매수 후보가 '{list(secs)[0]}' 한 섹터에 쏠림 — 다른 섹터도 함께 담아 위험 분산.")
        else:
            top = sorted(secs.items(), key=lambda x: -x[1])
            out.append("     매수 후보 섹터 분포: " + ", ".join(f"{k} {c}" for k, c in top)
                       + " → 3~5종목으로 분산, 한 종목 비중 과다 주의.")
    out.append("\n  🧭 버핏 원칙: 안전마진 확보 → 소수 우량주 집중 → 오래 보유. "
               "남이 탐욕스러울 때 두려워하고, 두려워할 때 욕심내라.")
    return out
