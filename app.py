"""
버핏 봇 — 웹 UI (Streamlit)

워런 버핏식 장기 가치투자 스크리너의 웹 프론트엔드.
실행(로컬): streamlit run app.py
배포: GitHub → Streamlit Community Cloud

설계 노트
  - 모든 위젯 상호작용은 스크립트를 처음부터 재실행한다(Streamlit 특성).
    따라서 분석 결과(verdicts)는 st.session_state에 보관해 탭 전환·버튼 클릭 때
    데이터를 다시 수집하지 않는다.
  - 비주얼은 커스텀 CSS로 히어로/배지/카드/지표를 꾸민다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="버핏 봇 · 장기 가치투자 스크리너",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────
# 커스텀 스타일
# ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── 기본 크롬 정리 ───────────────────────────────────── */
#MainMenu, footer, header [data-testid="stToolbar"] {visibility: hidden;}
.block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px;}

/* ── 히어로 헤더 ─────────────────────────────────────── */
.hero {
    background: radial-gradient(1200px 400px at 0% 0%, rgba(0,212,255,.10), transparent 60%),
                radial-gradient(900px 360px at 100% 0%, rgba(0,255,136,.10), transparent 55%),
                linear-gradient(160deg, rgba(255,255,255,.05), rgba(255,255,255,.01));
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 22px;
    padding: 30px 34px;
    margin-bottom: 22px;
}
.hero h1 {
    margin: 0; font-size: 2.35rem; font-weight: 800; letter-spacing: -.02em;
    background: linear-gradient(120deg, #00ff88 0%, #00d4ff 55%, #a78bfa 100%);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p {margin: 8px 0 0; color: #9aa4b2; font-size: 1.02rem;}
.hero .tag {
    display:inline-block; margin-top:14px; padding:5px 13px; border-radius:999px;
    font-size:.8rem; color:#cbd5e1; background:rgba(255,255,255,.06);
    border:1px solid rgba(255,255,255,.1);
}

/* ── 등급 배지 ──────────────────────────────────────── */
.badge {
    display:inline-block; padding:4px 12px; border-radius:999px;
    font-size:.8rem; font-weight:700; letter-spacing:-.01em; white-space:nowrap;
}
.badge.strong-buy {background:linear-gradient(135deg,#00ff88,#00d4ff); color:#04210f;
    box-shadow:0 0 18px rgba(0,255,136,.35);}
.badge.buy   {background:rgba(0,255,136,.14); color:#34f5a0; border:1px solid rgba(0,255,136,.4);}
.badge.wait  {background:rgba(255,196,0,.12); color:#ffce4d; border:1px solid rgba(255,196,0,.38);}
.badge.hold  {background:rgba(160,170,185,.12); color:#c2cad6; border:1px solid rgba(160,170,185,.3);}
.badge.avoid {background:rgba(255,75,75,.12); color:#ff7a7a; border:1px solid rgba(255,75,75,.36);}

/* ── KPI 카드 행 ────────────────────────────────────── */
.kpi-row {display:flex; gap:14px; margin:6px 0 20px; flex-wrap:wrap;}
.kpi-card {
    flex:1; min-width:150px; padding:16px 18px; border-radius:16px;
    border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.03);
}
.kpi-card .num {font-size:2rem; font-weight:800; line-height:1; letter-spacing:-.02em;}
.kpi-card .lbl {margin-top:7px; font-size:.82rem; color:#9aa4b2;}
.kpi-card.buy   .num {color:#34f5a0;}
.kpi-card.wait  .num {color:#ffce4d;}
.kpi-card.avoid .num {color:#ff7a7a;}
.kpi-card.temp  .num {font-size:1.15rem; line-height:1.35; padding-top:4px;}

/* ── 종목 스포트라이트 카드 ──────────────────────────── */
.pick-card {
    background:linear-gradient(160deg, rgba(255,255,255,.05), rgba(255,255,255,.015));
    border:1px solid rgba(255,255,255,.09); border-radius:18px; padding:18px 20px;
    height:100%;
}
.pick-card.strong-buy {border-color:rgba(0,255,136,.5); box-shadow:0 0 26px rgba(0,255,136,.13);}
.pick-card.buy {border-color:rgba(0,255,136,.28);}
.pick-card.wait {border-color:rgba(255,196,0,.28);}
.pick-head {display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;}
.pick-rank {font-size:.85rem; font-weight:800; color:#7c8696;}
.pick-name {font-size:1.18rem; font-weight:800; letter-spacing:-.02em; color:#f1f5f9;}
.pick-sub {font-size:.78rem; color:#7c8696; margin-top:2px;}
.pick-score-row {display:flex; align-items:baseline; gap:10px; margin:12px 0 4px;}
.pick-score {font-size:2.1rem; font-weight:800; letter-spacing:-.03em;
    background:linear-gradient(120deg,#00ff88,#00d4ff); -webkit-background-clip:text;
    background-clip:text; -webkit-text-fill-color:transparent;}
.pick-score span {font-size:.95rem; color:#7c8696; -webkit-text-fill-color:#7c8696;}
.pick-stars {margin-left:auto; color:#ffce4d; font-size:1.05rem; letter-spacing:1px;}
.pick-grid {display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:14px;}
.pick-grid > div {background:rgba(0,0,0,.22); border-radius:11px; padding:9px 10px; min-width:0; overflow:hidden;}
.pick-grid label {display:block; font-size:.68rem; color:#7c8696; margin-bottom:3px; white-space:nowrap;}
.pick-grid b {font-size:.9rem; color:#e2e8f0; display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.pos {color:#34f5a0 !important;} .neg {color:#ff7a7a !important;}

/* ── 지표(st.metric) 카드화 ─────────────────────────── */
[data-testid="stMetric"] {
    background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.07);
    border-radius:13px; padding:13px 16px;
}
[data-testid="stMetricLabel"] p {color:#8b95a5 !important; font-size:.78rem !important;}

/* ── 탭 ─────────────────────────────────────────────── */
button[data-baseweb="tab"] {font-size:1rem; font-weight:600;}
[data-testid="stExpander"] {border-radius:14px; border:1px solid rgba(255,255,255,.08);}

/* ── 사이드바 ───────────────────────────────────────── */
[data-testid="stSidebar"] {background:rgba(255,255,255,.02); border-right:1px solid rgba(255,255,255,.06);}

.section-title {font-size:1.25rem; font-weight:800; letter-spacing:-.02em; margin:26px 0 6px;}
.section-sub {color:#8b95a5; font-size:.88rem; margin-bottom:14px;}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────────────
def money(v, currency: str) -> str:
    if v is None:
        return "—"
    c = "₩" if currency == "KRW" else "$"
    return f"{c}{v:,.0f}" if currency == "KRW" else f"{c}{v:,.2f}"


def rating_meta(rating: str):
    """(css_class, emoji, 짧은라벨) 반환."""
    if "강력" in rating:    return ("strong-buy", "🚀", "강력 매수")
    if "매수 검토" in rating: return ("buy", "✅", "매수 검토")
    if "대기" in rating:    return ("wait", "⏳", "우량주·대기")
    if "관망" in rating:    return ("hold", "👀", "관망")
    return ("avoid", "🚫", "회피")


def badge_html(rating: str) -> str:
    cls, emoji, short = rating_meta(rating)
    return f'<span class="badge {cls}">{emoji} {short}</span>'


def pick_card_html(v, rank: int, sec_map: dict, stars: str) -> str:
    f, val = v.f, v.valuation
    cls, emoji, short = rating_meta(v.rating)
    cur = f.currency
    sec = sec_map.get(f.ticker, f.sector)
    mos = val.get("mos_pct")
    mos_cls = "pos" if (mos is not None and mos > 0) else "neg"
    mos_txt = f"{mos*100:+.0f}%" if mos is not None else "—"
    er = val.get("exp_return")
    er_txt = f"{er*100:.0f}%" if er is not None else "—"
    return f"""
<div class="pick-card {cls}">
  <div class="pick-head">
    <span class="pick-rank">#{rank}</span>
    <span class="badge {cls}">{emoji} {short}</span>
  </div>
  <div class="pick-name">{f.name[:20]}</div>
  <div class="pick-sub">{f.ticker} · {sec}</div>
  <div class="pick-score-row">
    <div class="pick-score">{v.total:.0f}<span>/100</span></div>
    <div class="pick-stars">{stars}</div>
  </div>
  <div class="pick-grid">
    <div><label>현재가</label><b>{money(f.price, cur)}</b></div>
    <div><label>적정가</label><b>{money(val.get('fair'), cur)}</b></div>
    <div><label>안전마진</label><b class="{mos_cls}">{mos_txt}</b></div>
    <div><label>기대수익</label><b>{er_txt}</b></div>
  </div>
</div>
"""


def _render_detail(v):
    """종목 상세 조언 블록 (스포트라이트 카드 클릭 + Tab4에서 공용)."""
    from advisor import _one_liner
    f, m, val = v.f, v.metrics, v.valuation
    cur = f.currency
    tech = getattr(m, "tech", None)
    fmt = lambda x: money(x, cur)

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총점", f"{v.total:.0f} / 100")
        c1.metric("확신도", advisor.conviction_stars(v))
        c2.metric("ROE", f"{f.roe*100:.1f}%" if f.roe else "—")
        c2.metric("ROIC", f"{m.roic*100:.1f}%" if m.roic else "—")
        c3.metric("현재가", fmt(f.price))
        c3.metric("적정가치", fmt(val.get("fair")))
        mos = val.get("mos_pct")
        er = val.get("exp_return")
        c4.metric("안전마진", f"{mos*100:+.0f}%" if mos is not None else "—",
                  delta=("싸다" if (mos or 0) > 0 else "비싸다"),
                  delta_color="normal" if (mos or 0) > 0 else "inverse")
        c4.metric("기대 연수익률", f"{er*100:.0f}%" if er is not None else "—")

        sc = val.get("scenarios", {})
        if sc:
            st.divider()
            d1, d2, d3 = st.columns(3)
            d1.metric("🐻 약세", fmt(sc.get("bear")))
            d2.metric("📊 기본", fmt(sc.get("base")))
            d3.metric("🐂 강세", fmt(sc.get("bull")))
            st.caption(f"💰 매수 권장가 **{fmt(val.get('buy_below'))}** 이하 (안전마진 25%)")

        ig = val.get("implied_growth")
        real = f.earnings_cagr
        if ig is not None:
            if real is not None and ig <= real:
                st.success(f"📈 역DCF: 시장은 연 {ig*100:.0f}% 성장 가정 — 실제({real*100:.0f}%)보다 낮아 **저평가 신호**")
            elif real is not None:
                st.warning(f"📈 역DCF: 시장은 연 {ig*100:.0f}% 기대 — 실적({real*100:.0f}%)이 못 따라가면 하락 위험")
            else:
                st.info(f"📈 역DCF: 시장이 가정한 성장률 연 {ig*100:.0f}%")

        if tech and tech.news_count > 0:
            st.divider()
            t1, t2 = st.columns([1, 2])
            lc = "🟢" if "긍정" in tech.label else ("🔴" if "부정" in tech.label else "⚪")
            t1.markdown(f"**📡 기술·사업 신호**  \n{lc} **{tech.label}**")
            t1.caption(f"뉴스 {tech.news_count}건 스캔")
            if tech.positive_hits:
                t2.markdown("**✅ 긍정:** " + " · ".join(tech.positive_hits))
            if tech.negative_hits:
                t2.markdown("**⚠️ 부정:** " + " · ".join(tech.negative_hits))

        if v.flags:
            st.error("⚑ 위험: " + "  /  ".join(v.flags))
        if m.fscore is not None:
            passed = [d[2:] for d in m.fscore_detail if d.startswith("✓")]
            st.caption(f"📊 F-Score {m.fscore}/9 통과: " + (", ".join(passed) if passed else "없음"))
        st.info(f"👉 {_one_liner(v)}")


def ticker_sector_map() -> dict:
    from universe import KR_UNIVERSE, US_UNIVERSE
    m = {}
    for uni in (KR_UNIVERSE, US_UNIVERSE):
        for sector, items in uni.items():
            for tk, _ in items:
                m[tk] = sector
    return m


# ─────────────────────────────────────────────────────────────────────────
# 사이드바 — 입력
# ─────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📈 버핏 봇")
    st.caption("워런 버핏식 장기 가치투자 스크리너")
    st.divider()

    mode = st.radio("분석 모드", ["유니버스 스크리닝", "직접 종목 입력"])
    if mode == "유니버스 스크리닝":
        market = st.selectbox("마켓", ["국장 (KR)", "미장 (US)", "전체 (All)"])
        market_code = {"국장 (KR)": "kr", "미장 (US)": "us", "전체 (All)": "all"}[market]
        custom_tickers = []
    else:
        from search_db import search as stock_search

        search_q = st.text_input(
            "🔎 회사 이름으로 검색",
            placeholder="예: 삼성, 애플, 현대, Tesla...",
            key="search_q",
        )

        # 검색 결과 → 선택
        if search_q:
            hits = stock_search(search_q, max_results=12)
            if hits:
                chosen = st.multiselect(
                    "검색 결과 (선택하면 분석 목록에 추가)",
                    options=[h["display"] for h in hits],
                    default=st.session_state.get("chosen_display", []),
                    key="chosen_display",
                    help="시총 큰 종목이 위에 표시됩니다",
                )
            else:
                st.caption("검색 결과 없음 — 다른 이름으로 시도해보세요.")
                chosen = st.session_state.get("chosen_display", [])
        else:
            chosen = st.session_state.get("chosen_display", [])

        # display 문자열에서 티커 추출: "삼성전자 (005930.KS)" → "005930.KS"
        import re
        custom_tickers = []
        for d in (chosen or []):
            m = re.search(r'\(([^)]+)\)$', d)
            if m:
                custom_tickers.append(m.group(1))

        if custom_tickers:
            st.caption(f"분석 목록: **{', '.join(custom_tickers)}**")
        market_code = "custom"

    st.divider()
    top_n = st.slider("상세 조언 상위 종목 수", 3, 20, 8)
    use_cache = st.toggle("당일 캐시 사용 (빠름)", value=True)
    fetch_tech = st.toggle("기술변곡점 뉴스 분석", value=True)

    st.divider()
    run_btn = st.button("🔍 분석 시작", type="primary", use_container_width=True)

    st.caption("📌 워치리스트")
    c1, c2 = st.columns(2)
    watch_btn = c1.button("💾 저장", use_container_width=True)
    check_btn = c2.button("🔔 점검", use_container_width=True)

    st.divider()
    st.caption("⚠️ 교육·연구용 참고 도구. 투자 책임은 본인에게 있습니다.")


# ─────────────────────────────────────────────────────────────────────────
# 워치리스트 점검 (분석 없이 즉시)
# ─────────────────────────────────────────────────────────────────────────
if check_btn:
    import watchlist as wl
    from datafetch import fetch

    st.markdown('<div class="hero"><h1>🔔 워치리스트 점검</h1>'
                '<p>저장한 목표가에 현재가가 도달했는지 확인합니다.</p></div>',
                unsafe_allow_html=True)
    data = wl.load()
    if not data:
        st.info("워치리스트가 비어 있습니다. 먼저 분석 후 '대기' 종목을 저장하세요.")
    else:
        with st.spinner("현재가 조회 중..."):
            lines = wl.check(lambda tk: fetch(tk, use_cache=False))
        for ln in lines:
            (st.success if "🔔" in ln else st.info)(ln.strip())
    st.stop()


# ─────────────────────────────────────────────────────────────────────────
# 분석 실행 → session_state 보관 (재실행 시 재수집 방지)
# ─────────────────────────────────────────────────────────────────────────
def run_analysis(tickers: list[str], use_cache: bool, fetch_tech: bool):
    from buffett import evaluate
    from datafetch import fetch

    bar = st.progress(0.0, text="데이터 수집 준비 중…")
    funds = []
    for i, tk in enumerate(tickers):
        bar.progress((i + 1) / len(tickers), text=f"수집 중 · {tk}  ({i+1}/{len(tickers)})")
        f = fetch(tk, use_cache=use_cache)
        if f:
            funds.append(f)
    bar.progress(1.0, text="버핏 점수 계산 중…")
    verdicts = sorted((evaluate(f, fetch_tech=fetch_tech) for f in funds),
                      key=lambda v: v.total, reverse=True)
    bar.empty()
    return verdicts


if run_btn:
    if market_code == "custom":
        tickers = custom_tickers
    else:
        from universe import get_universe
        tickers = [tk for tk, _, _ in get_universe(market_code)]

    if not tickers:
        st.warning("분석할 티커를 입력하거나 마켓을 선택하세요.")
        st.stop()

    st.session_state["verdicts"] = run_analysis(tickers, use_cache, fetch_tech)
    st.session_state["sec_map"] = ticker_sector_map()
    st.session_state["analyzed"] = True


# ─────────────────────────────────────────────────────────────────────────
# 랜딩 (분석 전)
# ─────────────────────────────────────────────────────────────────────────
if not st.session_state.get("analyzed"):
    st.markdown("""
    <div class="hero">
      <h1>버핏 봇</h1>
      <p>워런 버핏 · 벤저민 그레이엄의 가치투자 원칙을 정량화해 국장·미장을 같은 잣대로 채점합니다.<br>
      <b>어느 산업이 좋은지</b>, <b>지금 사도 되는 가격인지</b>, <b>무엇을·얼마에·왜</b> 사고 피할지 조언합니다.</p>
      <span class="tag">왼쪽에서 마켓을 고르고 ‘🔍 분석 시작’을 누르세요</span>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(3)
    cards = [
        ("🏆", "버핏 100점 채점", "수익성·해자 30 / 재무안정 25 / 성장 20 / 밸류 25 + 기술신호 ±3"),
        ("💰", "입체 적정가", "시나리오 DCF·역DCF·안전마진·기대 연수익률로 ‘살 가격’ 제시"),
        ("📡", "기술변곡점 탐지", "최신 뉴스에서 HBM·AI·수주 등 모멘텀 신호를 점수에 반영"),
        ("🏭", "섹터 진단", "어느 산업이 괜찮은지 평균 품질·관점 비교"),
        ("💼", "포트폴리오 조언", "시장 온도 + 지금매수·목표가대기·회피 버킷 분류"),
        ("📌", "워치리스트", "‘대기’ 종목 목표가 저장 → 도달 시 알림"),
    ]
    for i, (ico, t, d) in enumerate(cards):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="pick-card" style="margin-bottom:14px;">
              <div style="font-size:1.6rem">{ico}</div>
              <div style="font-weight:800;font-size:1.05rem;margin:6px 0 4px">{t}</div>
              <div style="color:#8b95a5;font-size:.85rem;line-height:1.5">{d}</div>
            </div>""", unsafe_allow_html=True)

    st.info('💡 *"훌륭한 기업을 적당한 가격에 사라. 그저 그런 기업을 헐값에 사는 것보다 낫다."* — 워런 버핏')
    st.stop()


# ─────────────────────────────────────────────────────────────────────────
# 결과 렌더링
# ─────────────────────────────────────────────────────────────────────────
import advisor

verdicts = st.session_state["verdicts"]
sec_map = st.session_state["sec_map"]

if not verdicts:
    st.error("수집된 종목이 없습니다. 네트워크나 티커를 확인하세요.")
    st.stop()

# ── 히어로 + KPI ──────────────────────────────────────────────────────────
n = len(verdicts)
buys = [v for v in verdicts if advisor._bucket(v) == "buy"]
waits = [v for v in verdicts if advisor._bucket(v) == "wait"]
avoids = [v for v in verdicts if advisor._bucket(v) == "avoid"]
strong = [v for v in verdicts if "강력" in v.rating]
ers = [v.valuation.get("exp_return") for v in verdicts if v.valuation.get("exp_return") is not None]
avg_er = (sum(ers) / len(ers) * 100) if ers else None

buy_ratio = len(buys) / n if n else 0
if buy_ratio < 0.15:
    temp = "🥶 비싼 장<br><span style='font-size:.78rem;color:#8b95a5'>현금 들고 기다릴 때</span>"
elif buy_ratio < 0.35:
    temp = "😐 선별적 기회<br><span style='font-size:.78rem;color:#8b95a5'>소수만 골라 담기</span>"
else:
    temp = "🔥 우호적 국면<br><span style='font-size:.78rem;color:#8b95a5'>분산 매수 검토</span>"

st.markdown(f"""
<div class="hero">
  <h1>📊 분석 결과</h1>
  <p>{n}개 종목을 버핏 잣대로 채점했습니다. {'강력 매수 ' + str(len(strong)) + '종목 발견!' if strong else '오늘은 강력 매수 등급이 없습니다 — 정상입니다.'}</p>
</div>
<div class="kpi-row">
  <div class="kpi-card temp"><div class="num">{temp}</div><div class="lbl">시장 온도</div></div>
  <div class="kpi-card buy"><div class="num">{len(buys)}</div><div class="lbl">✅ 지금 매수</div></div>
  <div class="kpi-card wait"><div class="num">{len(waits)}</div><div class="lbl">⏳ 목표가 대기</div></div>
  <div class="kpi-card avoid"><div class="num">{len(avoids)}</div><div class="lbl">🚫 회피</div></div>
  <div class="kpi-card"><div class="num">{f'{avg_er:.0f}%' if avg_er is not None else '—'}</div><div class="lbl">평균 기대수익률</div></div>
</div>
""", unsafe_allow_html=True)

# ── 스포트라이트: 강력매수 또는 톱픽 ──────────────────────────────────────
spotlight = strong if strong else buys
title = "🚀 강력 매수 후보" if strong else "✅ 지금 사도 좋은 후보 (Top 3)"
if spotlight:
    st.markdown(f'<div class="section-title">{title}</div>'
                f'<div class="section-sub">안전마진과 품질을 함께 갖춘 순서</div>',
                unsafe_allow_html=True)
    spot = sorted(spotlight, key=lambda v: (v.valuation.get("exp_return") or -9, v.total), reverse=True)[:3]
    cols = st.columns(len(spot))
    for i, (col, v) in enumerate(zip(cols, spot), 1):
        with col:
            st.markdown(pick_card_html(v, i, sec_map, advisor.conviction_stars(v)),
                        unsafe_allow_html=True)
            key = f"spot_detail_{v.f.ticker}"
            is_open = st.session_state.get(key, False)
            btn_label = "▲ 상세 조언 닫기" if is_open else "📋 상세 조언 보기"
            if st.button(btn_label, key=f"btn_{v.f.ticker}", use_container_width=True):
                st.session_state[key] = not is_open
                st.rerun()

    # 상세 조언 패널 (카드 아래 전체 너비로 표시)
    for v in spot:
        if st.session_state.get(f"spot_detail_{v.f.ticker}"):
            _render_detail(v)
else:
    st.markdown('<div class="section-title">⏳ 지금은 매수 신호 없음</div>', unsafe_allow_html=True)
    st.info("안전마진을 주는 종목이 없습니다. 버핏: *기다림도 전략이다.* "
            "아래 ‘목표가 대기’에서 우량주의 목표 매수가를 확인하세요.")

st.markdown("<br>", unsafe_allow_html=True)

# ── 탭 ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🏆 전체 랭킹", "🏭 섹터 진단", "💼 포트폴리오", "📋 상세 조언"])

# Tab1: 랭킹
with tab1:
    st.markdown('<div class="section-sub">총점 100 = 품질 75 + 가격 25 (+ 기술신호 ±3)</div>',
                unsafe_allow_html=True)
    rows = []
    for i, v in enumerate(verdicts, 1):
        f, m = v.f, v.metrics
        tech = getattr(m, "tech", None)
        _, emoji, short = rating_meta(v.rating)
        mos = v.valuation.get("mos_pct")
        er = v.valuation.get("exp_return")
        rows.append({
            "#": i,
            "종목": f.name[:18],
            "섹터": sec_map.get(f.ticker, f.sector)[:10],
            "총점": round(v.total, 1),
            "품질": round(v.quality, 1),
            "등급": f"{emoji} {short}",
            "안전마진": round(mos * 100, 0) if mos is not None else None,
            "기대수익": round(er * 100, 0) if er is not None else None,
            "ROIC": round(m.roic * 100, 0) if m.roic is not None else None,
            "F": m.fscore if m.fscore is not None else None,
            "기술신호": tech.label if (tech and tech.news_count > 0) else "—",
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df, use_container_width=True, hide_index=True, height=560,
        column_config={
            "총점": st.column_config.ProgressColumn("총점", min_value=0, max_value=100,
                                                   format="%.0f"),
            "품질": st.column_config.NumberColumn("품질/75", format="%.0f"),
            "안전마진": st.column_config.NumberColumn("안전마진%", format="%+.0f%%"),
            "기대수익": st.column_config.NumberColumn("기대수익%", format="%.0f%%"),
            "ROIC": st.column_config.NumberColumn("ROIC%", format="%.0f%%"),
        },
    )

# Tab2: 섹터
with tab2:
    st.markdown('<div class="section-sub">어느 산업이 괜찮은지 — 평균 품질 순</div>',
                unsafe_allow_html=True)
    SECTOR_PHILOSOPHY = {
        "필수소비재": "버핏 최애. 브랜드·반복구매=해자, 불황에도 현금창출",
        "IT·플랫폼": "원칙은 '아는 사업만'. 애플은 소비재 브랜드로 봄",
        "헬스케어": "특허·규모의 해자. 경기방어적",
        "금융": "버핏의 본진(보험·카드·신용평가). ROE·ROA·자본배분이 핵심",
        "반도체·IT": "사이클 큼 — 저점 이익 때 PER 착시(정상화PER로 보정)",
        "2차전지·소재": "성장 매력 vs 자본집약·경쟁심화. 해자 검증 필요",
        "지주·소재": "자본집약·사이클. 저PBR 함정 주의",
        "통신": "현금흐름·고배당 안정형. 성장은 제한적",
    }
    by_sec: dict[str, list] = {}
    for v in verdicts:
        by_sec.setdefault(sec_map.get(v.f.ticker, v.f.sector), []).append(v)
    sec_rows = []
    for sec, vs in by_sec.items():
        best = max(vs, key=lambda x: x.total)
        sec_rows.append({
            "섹터": sec,
            "평균 품질": round(sum(x.quality for x in vs) / len(vs), 1),
            "평균 총점": round(sum(x.total for x in vs) / len(vs), 1),
            "종목수": len(vs),
            "대표 종목": best.f.name[:16],
            "투자 관점": SECTOR_PHILOSOPHY.get(sec, ""),
        })
    sec_rows.sort(key=lambda x: -x["평균 품질"])
    sec_df = pd.DataFrame(sec_rows)
    st.dataframe(
        sec_df, use_container_width=True, hide_index=True,
        column_config={
            "평균 품질": st.column_config.ProgressColumn("평균 품질", min_value=0,
                                                      max_value=75, format="%.0f"),
        },
    )
    st.bar_chart(sec_df.set_index("섹터")[["평균 품질", "평균 총점"]], use_container_width=True)

# Tab3: 포트폴리오
with tab3:
    st.markdown('<div class="section-sub">지금 무엇을, 얼마에, 왜</div>', unsafe_allow_html=True)

    if buys:
        st.markdown("#### ✅ 지금 사도 좋은 후보")
        for v in sorted(buys, key=lambda v: (v.valuation.get("exp_return") or -9), reverse=True)[:8]:
            sec = sec_map.get(v.f.ticker, v.f.sector)
            er = v.valuation.get("exp_return")
            er_s = f" · 기대수익 {er*100:.0f}%" if er is not None else ""
            cc = st.columns([3, 2, 2, 3])
            cc[0].markdown(f"**{v.f.name[:16]}** {badge_html(v.rating)}", unsafe_allow_html=True)
            cc[1].markdown(f"`{sec}`")
            cc[2].markdown(f"{money(v.f.price, v.f.currency)} → {money(v.valuation.get('fair'), v.f.currency)}")
            cc[3].markdown(f"{advisor.conviction_stars(v)}{er_s}")
    else:
        st.info("지금은 안전마진을 주는 매수 후보가 없습니다. (기다림도 전략)")

    if waits:
        st.markdown("#### ⏳ 목표가 대기 (우량하나 비쌈)")
        for v in waits[:8]:
            buy = v.valuation.get("buy_below")
            down = (1 - buy / v.f.price) * 100 if (buy and v.f.price) else None
            if down is not None and down > 55:
                txt = f"과도한 고평가 (목표가 −{down:.0f}%), 관심 보류"
            elif down is not None:
                txt = f"목표 {money(buy, v.f.currency)} (−{down:.0f}%)"
            else:
                txt = "목표가 산정 불가"
            cc = st.columns([3, 4, 2])
            cc[0].markdown(f"**{v.f.name[:16]}**")
            cc[1].markdown(f"{money(v.f.price, v.f.currency)} · {txt}")
            cc[2].markdown(f"품질 {v.quality:.0f}/75")

    if avoids:
        st.markdown("#### 🚫 회피")
        for v in avoids[:6]:
            why = v.flags[0] if v.flags else "지표 기준 미달"
            st.markdown(f"- **{v.f.name[:16]}** — {why}")

    # 섹터 분산
    if buys:
        secs: dict[str, int] = {}
        for v in buys[:8]:
            s = sec_map.get(v.f.ticker, v.f.sector)
            secs[s] = secs.get(s, 0) + 1
        st.markdown("#### 🧩 분산 제안")
        if len(secs) == 1:
            st.warning(f"매수 후보가 '{list(secs)[0]}' 한 섹터에 쏠림 — 다른 섹터도 함께 담아 위험 분산.")
        else:
            dist = ", ".join(f"{k} {c}" for k, c in sorted(secs.items(), key=lambda x: -x[1]))
            st.success(f"매수 후보 섹터 분포: {dist} → 3~5종목으로 분산, 한 종목 과다 비중 주의.")

    st.info("🧭 버핏 원칙: 안전마진 확보 → 소수 우량주 집중 → 오래 보유. "
            "남이 탐욕스러울 때 두려워하고, 두려워할 때 욕심내라.")

    st.divider()
    if watch_btn or st.button("💾 '대기' 종목 목표가 워치리스트 저장", use_container_width=True):
        import watchlist as wl
        cnt = wl.add_from_verdicts(verdicts)
        st.success(f"✅ '대기' 종목 {cnt}개를 워치리스트에 저장했습니다. "
                   f"사이드바 '🔔 점검'으로 목표가 도달을 확인하세요.")

# Tab4: 상세
with tab4:
    st.markdown(f'<div class="section-sub">상위 {min(top_n, len(verdicts))}개 종목 심층 분석</div>',
                unsafe_allow_html=True)
    show = verdicts[:top_n]
    for idx, v in enumerate(show):
        _, emoji, short = rating_meta(v.rating)
        with st.expander(f"{emoji} {v.f.name} ({v.f.ticker})  ·  {short}  ·  {v.total:.0f}점",
                         expanded=(idx == 0)):
            _render_detail(v)

st.divider()
st.caption("⚠️ 교육·연구용 참고 도구입니다. 자동매매가 아니며, 실제 매수 전 사업보고서·해자의 지속성·"
           "경영진의 자본배분을 직접 검증하세요.  \"리스크는 자신이 무엇을 하는지 모르는 데서 온다.\" — 워런 버핏")
