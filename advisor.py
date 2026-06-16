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
    """확신도 ★1~5 — 품질·안전마진·F스코어·위험을 종합."""
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
    """역DCF: 시장이 가정한 성장률 vs 실제 성장 해석."""
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


def advise(v: Verdict) -> list[str]:
    """종목 한 개의 조언 블록(여러 줄)."""
    f, m, val = v.f, v.metrics, v.valuation
    cur = f.currency
    out = []
    out.append(f"[{v.rating}]  {f.name} ({f.ticker})  ·  {f.sector}")
    out.append(f"   종합 {v.total:.0f}/100 (품질 {v.quality:.0f}/75 · 가격 {v.value:.0f}/25)  "
               f"확신도 {conviction_stars(v)}")

    # 해자/강점
    moat = []
    if f.roe is not None: moat.append(f"ROE {f.roe*100:.0f}%")
    if m.roic is not None: moat.append(f"ROIC {m.roic*100:.0f}%")
    if not is_financial(f) and f.gross_margin is not None:
        moat.append(f"매출총이익률 {f.gross_margin*100:.0f}%")
    if m.fscore is not None: moat.append(f"F-Score {m.fscore}/9")
    if moat:
        out.append("   🏰 강점: " + " · ".join(moat))

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
        out.append("   ⚑ 위험: " + " / ".join(v.flags))

    # 한 줄 조언
    out.append("   👉 " + _one_liner(v))
    return out


def _one_liner(v: Verdict) -> str:
    f, val = v.f, v.valuation
    cur = f.currency
    buy = val.get("buy_below")
    if v.rating == "회피":
        return "조언: 매수 대상에서 제외. " + (v.flags[0] if v.flags else "지표가 기준에 미달.")
    if f.price and buy and f.price <= buy:
        return f"조언: 지금 가격이 안전마진 구간. 분할 매수로 모아가도 좋은 자리."
    if "대기" in v.rating:
        if buy and f.price:
            down = (1 - buy / f.price) * 100
            if down > 55:
                return ("조언: 사업은 훌륭하나 현재가가 적정가치를 크게 초과(과도한 고평가). "
                        "지금은 관심 보류 — 큰 폭 조정이나 이익 레벨업을 확인하고 재검토.")
            return (f"조언: 사업은 훌륭하나 비쌈. {money(buy,cur)}(약 -{down:.0f}%)까지 "
                    f"눌릴 때를 노려 워치리스트에 등록.")
        return "조언: 우량하나 현재가가 부담. 조정 시 매수."
    if v.rating == "매수 검토":
        return "조언: 품질·가격 균형 양호. 추가 점검(해자 지속성·경영진) 후 분할 매수 검토."
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
    return "watch"   # 관망


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
    """포트폴리오 차원 실행 조언."""
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

    # 섹터 분산 제안
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
