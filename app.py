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
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────
# 커스텀 스타일
# ─────────────────────────────────────────────────────────────────────────
import base64 as _b64, pathlib as _pl
_bg_path = _pl.Path(__file__).parent / "assets" / "buffett.jpg"
if _bg_path.exists():
    _bg_b64 = _b64.b64encode(_bg_path.read_bytes()).decode()
    _bg_css = f"""
    [data-testid="stAppViewContainer"] > div:first-child {{
        background-image:
            linear-gradient(to right, rgba(10,14,22,0.92) 40%, rgba(10,14,22,0.35) 70%, rgba(10,14,22,0.1) 100%),
            url("data:image/jpeg;base64,{_bg_b64}");
        background-size: 55% auto;
        background-repeat: no-repeat;
        background-position: right top;
        background-attachment: fixed;
        min-height: 100vh;
    }}
    """
else:
    _bg_css = ""

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

/* ── 상단 브랜드 헤더 ───────────────────────────────── */
.brand {display:flex; align-items:center; gap:14px; margin:0 0 18px;}
.brand .logo {
    font-size:2.1rem; line-height:1;
    filter: drop-shadow(0 2px 10px rgba(0,255,136,.25));
}
.brand .tt {display:flex; flex-direction:column;}
.brand .name {
    font-size:1.55rem; font-weight:900; letter-spacing:-.03em; line-height:1.05;
    background:linear-gradient(120deg,#00ff88 0%,#00d4ff 60%,#a78bfa 100%);
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
}
.brand .slogan {color:#8b95a5; font-size:.82rem; margin-top:2px; letter-spacing:-.01em;}
.brand .spacer {flex:1;}
.brand .quote {
    color:#7c8696; font-size:.78rem; font-style:italic; text-align:right;
    max-width:280px; line-height:1.45; display:none;
}
@media (min-width:900px){ .brand .quote {display:block;} }

/* ── 한눈 요약 칩 (hero 안) ─────────────────────────── */
.mini-pills {display:flex; gap:8px; flex-wrap:wrap; margin-top:14px;}
.mini-pill {
    display:inline-flex; align-items:center; gap:6px;
    padding:5px 12px; border-radius:999px; font-size:.82rem; font-weight:700;
    border:1px solid rgba(255,255,255,.1);
}
.mini-pill.buy   {background:rgba(0,255,136,.12); color:#34f5a0; border-color:rgba(0,255,136,.35);}
.mini-pill.wait  {background:rgba(255,196,0,.10); color:#ffce4d; border-color:rgba(255,196,0,.32);}
.mini-pill.avoid {background:rgba(255,75,75,.10); color:#ff7a7a; border-color:rgba(255,75,75,.3);}
.mini-pill.er    {background:rgba(0,212,255,.10); color:#7cd6ff; border-color:rgba(0,212,255,.3);}
</style>
""", unsafe_allow_html=True)

if _bg_css:
    st.markdown(f"<style>{_bg_css}</style>", unsafe_allow_html=True)

# ── 상단 브랜드 헤더 ───────────────────────────────────────────────────────
st.markdown("""
<div class="brand">
  <div class="logo">🎩</div>
  <div class="tt">
    <div class="name">버핏 봇</div>
    <div class="slogan">워런 버핏식 장기 가치투자 스크리너 · 국장 + 미장</div>
  </div>
  <div class="spacer"></div>
  <div class="quote">“훌륭한 기업을 적당한 가격에 사는 것이<br>적당한 기업을 헐값에 사는 것보다 낫다.”</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────────────
def money(v, currency: str) -> str:
    if v is None:
        return "—"
    c = "₩" if currency == "KRW" else "$"
    return f"{c}{v:,.0f}" if currency == "KRW" else f"{c}{v:,.2f}"


def fmt_cap(v, currency: str) -> str:
    """시가총액을 사람이 읽기 쉬운 단위로 (국장: 조/억, 미장: B/M)."""
    if not v or v <= 0:
        return "—"
    if currency == "KRW":
        if v >= 1e12:   return f"{v/1e12:.1f}조"
        if v >= 1e8:    return f"{v/1e8:,.0f}억"
        return f"{v:,.0f}"
    # USD
    if v >= 1e12:   return f"${v/1e12:.2f}T"
    if v >= 1e9:    return f"${v/1e9:.1f}B"
    if v >= 1e6:    return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"


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


def pick_card_html(v, rank: int, sec_map: dict, stars: str, display_name: str = "") -> str:
    f, val = v.f, v.valuation
    cls, emoji, short = rating_meta(v.rating)
    cur = f.currency
    sec = sec_map.get(f.ticker, f.sector)
    mos = val.get("mos_pct")
    mos_cls = "pos" if (mos is not None and mos > 0) else "neg"
    mos_txt = f"{mos*100:+.0f}%" if mos is not None else "—"
    er = val.get("exp_return")
    er_txt = f"{er*100:.0f}%" if er is not None else "—"
    name_txt = (display_name or f.name)[:20]
    return f"""
<div class="pick-card {cls}">
  <div class="pick-head">
    <span class="pick-rank">#{rank}</span>
    <span class="badge {cls}">{emoji} {short}</span>
  </div>
  <div class="pick-name">{name_txt}</div>
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
    from advisor import _one_liner, _sector_context, _metric_narrative
    f, m, val = v.f, v.metrics, v.valuation
    cur = f.currency
    tech = getattr(m, "tech", None)
    fmt = lambda x: money(x, cur)

    with st.container(border=True):
        # ── 섹터 배경 설명 ──
        ctx = _sector_context(v)
        if ctx:
            st.markdown(f"#### 🌐 섹터 배경")
            st.info(ctx)

        # ── 왜 매수/주의인가 — 지표 해석 ──
        metric_lines = _metric_narrative(v)
        if metric_lines:
            st.markdown("#### 📊 주요 지표 해석")
            for ln in metric_lines:
                st.markdown(f"- {ln}")

        st.divider()

        # ── KPI 수치 ──
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("총점", f"{v.total:.0f} / 100")
        c1.metric("확신도", advisor.conviction_stars(v))
        per_val = m.norm_per if m.norm_per is not None else f.per
        c2.metric("PER", f"{per_val:.1f}배" if (per_val and per_val > 0) else "—")
        c2.metric("PBR", f"{f.pbr:.1f}배" if (f.pbr and f.pbr > 0) else "—")
        c3.metric("ROE", f"{f.roe*100:.1f}%" if f.roe else "—")
        c3.metric("ROIC", f"{m.roic*100:.1f}%" if m.roic else "—")
        c4.metric("현재가", fmt(f.price))
        c4.metric("적정가치", fmt(val.get("fair")))
        mos = val.get("mos_pct")
        er = val.get("exp_return")
        c5.metric("안전마진", f"{mos*100:+.0f}%" if mos is not None else "—",
                  delta=("싸다" if (mos or 0) > 0 else "비싸다"),
                  delta_color="normal" if (mos or 0) > 0 else "inverse")
        c5.metric("기대 연수익률", f"{er*100:.0f}%" if er is not None else "—")

        # ── 시나리오 DCF ──
        sc = val.get("scenarios", {})
        if sc:
            st.divider()
            d1, d2, d3 = st.columns(3)
            d1.metric("🐻 약세 시나리오", fmt(sc.get("bear")))
            d2.metric("📊 기본 시나리오", fmt(sc.get("base")))
            d3.metric("🐂 강세 시나리오", fmt(sc.get("bull")))
            st.caption(f"💰 매수 권장가 **{fmt(val.get('buy_below'))}** 이하 (안전마진 25%)")

        # ── 역DCF ──
        ig = val.get("implied_growth")
        real = f.earnings_cagr
        if ig is not None:
            if real is not None and ig <= real:
                st.success(f"📈 역DCF: 시장은 연 {ig*100:.0f}% 성장 가정 — 실제({real*100:.0f}%)보다 낮아 **저평가 신호**")
            elif real is not None:
                st.warning(f"📈 역DCF: 시장은 연 {ig*100:.0f}% 기대 — 실적({real*100:.0f}%)이 못 따라가면 하락 위험")
            else:
                st.info(f"📈 역DCF: 시장이 가정한 성장률 연 {ig*100:.0f}%")

        # ── 기술변곡점 ──
        if tech and tech.news_count > 0:
            st.divider()
            t1, t2 = st.columns([1, 2])
            lc = "🟢" if "긍정" in tech.label else ("🔴" if "부정" in tech.label else "⚪")
            t1.markdown(f"**📡 기술·사업 신호**  \n{lc} **{tech.label}**")
            t1.caption(f"뉴스 {tech.news_count}건 스캔")
            if tech.positive_hits:
                t2.markdown("**✅ 긍정 키워드:** " + " · ".join(tech.positive_hits))
            if tech.negative_hits:
                t2.markdown("**⚠️ 부정 키워드:** " + " · ".join(tech.negative_hits))

        # ── 주주환원·재무 고급 신호 ──
        extra_signals = []
        f_obj = v.f
        insider_pct = getattr(f_obj, 'insider_pct', None)
        if insider_pct is not None and insider_pct >= 0.05:
            extra_signals.append(f"👤 내부자 지분 {insider_pct*100:.1f}% — 경영진이 대주주")
        if getattr(m, 'buyback_signal', False):
            extra_signals.append("🔄 자사주 매입 감지 — 발행주식수 감소 중")
        div_streak = getattr(f_obj, 'div_growth_streak', 0)
        if div_streak >= 5:
            extra_signals.append(f"💰 배당 {div_streak}년 연속 성장")
        eps_streak = getattr(f_obj, 'eps_beat_streak', 0)
        if eps_streak >= 3:
            extra_signals.append(f"📈 분기 EPS {eps_streak}회 연속 성장")
        if getattr(f_obj, 'de_improving', False):
            extra_signals.append("📉 부채비율 개선 추세")
        interest_cov = getattr(m, 'interest_coverage', None)
        if interest_cov is not None:
            if interest_cov >= 10:
                extra_signals.append(f"🛡️ 이자보상비율 {interest_cov:.1f}배 — 재무 매우 안전")
            elif interest_cov < 3:
                extra_signals.append(f"⚠️ 이자보상비율 {interest_cov:.1f}배 — 이자 부담 주의")
        institution_pct = getattr(f_obj, 'institution_pct', None)
        if institution_pct is not None:
            extra_signals.append(f"🏦 기관 보유 {institution_pct*100:.1f}%")
        if extra_signals:
            st.info("  |  ".join(extra_signals))

        # ── 위험·F스코어 ──
        if v.flags:
            st.error("⚑ 위험 요인: " + "  /  ".join(v.flags))
        if m.fscore is not None:
            passed = [d[2:] for d in m.fscore_detail if d.startswith("✓")]
            st.caption(f"📋 F-Score {m.fscore}/9 통과: " + (", ".join(passed) if passed else "없음"))

        # ── 최종 한 줄 조언 ──
        st.divider()
        st.success(f"👉 {_one_liner(v)}")


@st.cache_data(show_spinner=False)
def ticker_sector_map() -> dict:
    from universe import KR_UNIVERSE, US_UNIVERSE
    m = {}
    for uni in (KR_UNIVERSE, US_UNIVERSE):
        for sector, items in uni.items():
            for tk, _ in items:
                m[tk] = sector
    return m


@st.cache_data(show_spinner=False)
def ticker_name_map() -> dict:
    """ticker → 한글(또는 표시용) 이름 맵. universe + search_db 통합."""
    m = {}
    # universe (한글명 우선)
    from universe import KR_UNIVERSE, US_UNIVERSE
    for uni in (KR_UNIVERSE, US_UNIVERSE):
        for sector, items in uni.items():
            for tk, name in items:
                m[tk] = name
    # search_db 보완
    try:
        from search_db import ALL_STOCKS
        for kor, eng, tk, _ in ALL_STOCKS:
            if tk not in m:
                m[tk] = kor if kor else eng
    except Exception:
        pass
    return m


# ─────────────────────────────────────────────────────────────────────────
# 메인 설정 패널 (사이드바 대신 — 접기/펼치기 가능)
# ─────────────────────────────────────────────────────────────────────────
import re

# 기본값 (아래 모드별로 덮어씀)
run_btn = watch_btn = check_btn = False
custom_tickers: list[str] = []
top_n = 8
use_cache = True
fetch_tech = True
auto_market = "kr"

view = st.radio(
    "보기 모드",
    ["📊 전체 종목 분석", "🔎 직접 종목 검색"],
    horizontal=True,
    label_visibility="collapsed",
    key="view_mode",
)

if view == "📊 전체 종목 분석":
    cc1, cc2 = st.columns([3, 1])
    with cc1:
        market_label = st.radio(
            "마켓",
            ["🇰🇷 국장 (KR)", "🇺🇸 미장 (US)"],
            horizontal=True,
            label_visibility="collapsed",
            key="auto_market_label",
        )
        auto_market = "kr" if "국장" in market_label else "us"
    with cc2:
        top_n = st.slider("상세 조언 상위", 3, 20, 8)
    st.caption("⚡ 매일 **오전 6시·오후 6시**에 자동 수집된 결과를 바로 보여줍니다. "
               "버튼을 누를 필요 없이, 마켓만 고르면 됩니다.")
else:
    with st.expander("⚙️ 검색 / 분석 설정", expanded=True):
        from search_db import search as stock_search

        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            search_q = st.text_input(
                "🔎 회사 이름으로 검색",
                placeholder="예: 삼성, 애플, 현대, Tesla...",
                key="search_q",
            )
        with col_s2:
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

        for d in (chosen or []):
            mm = re.search(r'\(([^)]+)\)$', d)
            if mm:
                custom_tickers.append(mm.group(1))
        if custom_tickers:
            st.caption(f"분석 목록: **{', '.join(custom_tickers)}**")

        col_opt1, col_opt2, col_opt3 = st.columns([2, 1, 1])
        with col_opt1:
            top_n = st.slider("상세 조언 상위 종목 수", 3, 20, 8)
        with col_opt2:
            use_cache = st.toggle("당일 캐시 사용", value=True)
            fetch_tech = st.toggle("기술변곡점 뉴스", value=True)
        with col_opt3:
            run_btn = st.button("🔍 분석 시작", type="primary", width="stretch")
            c1, c2 = st.columns(2)
            watch_btn = c1.button("💾 저장", width="stretch")
            check_btn = c2.button("🔔 점검", width="stretch")

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
    from concurrent.futures import ThreadPoolExecutor, as_completed

    total = len(tickers)
    bar = st.progress(0.0, text=f"병렬 데이터 수집 중… (0/{total})")
    status = st.empty()

    funds = []
    done_count = 0
    lock_funds = []

    # 캐시 없을 때 yfinance rate-limit 고려해 최대 20 스레드
    workers = min(20, total)

    def _fetch_one(tk):
        return fetch(tk, use_cache=use_cache)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_one, tk): tk for tk in tickers}
        for fut in as_completed(futures):
            done_count += 1
            tk = futures[fut]
            try:
                f = fut.result()
                if f:
                    lock_funds.append(f)
            except Exception:
                pass
            bar.progress(done_count / total,
                         text=f"수집 중… ({done_count}/{total})  ·  {tk}")

    bar.progress(1.0, text="버핏 점수 계산 중…")
    verdicts = sorted(
        (evaluate(f, fetch_tech=fetch_tech) for f in lock_funds),
        key=lambda v: v.total, reverse=True,
    )
    bar.empty()
    status.empty()
    return verdicts


# ─────────────────────────────────────────────────────────────────────────
# 결과 준비 — 전체 분석(사전수집 즉시 로드) / 직접 검색(버튼)
# ─────────────────────────────────────────────────────────────────────────
ready = False

if view == "📊 전체 종목 분석":
    import results_io

    ck = f"auto_loaded_{auto_market}"
    if ck not in st.session_state:
        st.session_state[ck] = results_io.load_market(auto_market)
    loaded_verdicts, loaded_ts = st.session_state[ck]

    if loaded_verdicts:
        st.session_state["verdicts"] = loaded_verdicts
        st.session_state["sec_map"] = ticker_sector_map()
        st.session_state["name_map"] = ticker_name_map()
        st.session_state["data_ts"] = loaded_ts or ""
        st.session_state["result_source"] = f"auto:{auto_market}"
        ready = True
    else:
        # 아직 자동 수집 전 — 안내 + 즉시 수집 폴백
        mk_name = "국장" if auto_market == "kr" else "미장"
        st.markdown(f"""
        <div class="hero">
          <h1>⏳ {mk_name} 자동 수집 대기 중</h1>
          <p>매일 <b>오전 6시·오후 6시</b>에 전체 종목이 자동 분석됩니다.<br>
          아직 첫 수집이 완료되지 않았어요. 지금 바로 분석하려면 아래 버튼을 누르세요 (1~2분 소요).</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"⚡ {mk_name} 지금 즉시 분석", type="primary"):
            from universe import get_universe
            tickers = [tk for tk, _, _ in get_universe(auto_market)]
            st.session_state["verdicts"] = run_analysis(tickers, True, False)
            st.session_state["sec_map"] = ticker_sector_map()
            st.session_state["name_map"] = ticker_name_map()
            st.session_state["data_ts"] = "방금 수집 (실시간)"
            st.session_state["result_source"] = f"auto:{auto_market}"
            st.rerun()
        st.stop()

elif run_btn:
    if not custom_tickers:
        st.warning("회사 이름으로 검색해 종목을 선택한 뒤 ‘분석 시작’을 누르세요.")
        st.stop()
    st.session_state["verdicts"] = run_analysis(custom_tickers, use_cache, fetch_tech)
    st.session_state["sec_map"] = ticker_sector_map()
    st.session_state["name_map"] = ticker_name_map()
    st.session_state["data_ts"] = "방금 수집 (실시간)"
    st.session_state["result_source"] = "custom"
    ready = True

elif st.session_state.get("result_source") == "custom" and st.session_state.get("verdicts"):
    # 직접 검색 결과를 이미 본 상태 — 재실행 시 유지
    ready = True


# ─────────────────────────────────────────────────────────────────────────
# 직접 검색 모드: 아직 분석 전이면 안내 후 정지
# ─────────────────────────────────────────────────────────────────────────
if not ready:
    st.markdown("""
    <div class="hero">
      <h1>🔎 직접 종목 검색</h1>
      <p>회사 이름을 검색해 종목을 고르고 <b>‘🔍 분석 시작’</b>을 누르면<br>
      버핏 잣대로 채점하고 적정 매수가·이유·위험을 조언합니다.</p>
      <span class="tag">전체 종목을 보려면 위에서 <b>📊 전체 종목 분석</b>을 선택하세요</span>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(3)
    cards = [
        ("🏆", "버핏 100점 채점", "수익성·해자 30 / 재무안정 25 / 성장 20 / 밸류 25 + 기술신호 ±3"),
        ("💰", "입체 적정가", "시나리오 DCF·역DCF·안전마진·기대 연수익률로 ‘살 가격’ 제시"),
        ("📡", "기술변곡점 탐지", "최신 뉴스에서 HBM·AI·수주 등 모멘텀 신호를 점수에 반영"),
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
name_map = st.session_state.get("name_map", {})


def disp_name(v) -> str:
    """티커에 맞는 한글(표시용) 이름 반환. 없으면 yfinance 이름 그대로."""
    return name_map.get(v.f.ticker) or v.f.name

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


def _fear_greed_label(score: int) -> tuple[str, str, str]:
    if score <= 24:   return "극도의 공포", "🥶", "역사적 저점 — 분할 매수 적기"
    elif score <= 44: return "공포", "😨", "저평가 종목 多 — 매수 우호"
    elif score <= 55: return "중립", "😐", "선별적 접근"
    elif score <= 75: return "탐욕", "😏", "고평가 구간 — 신중하게"
    else:             return "극도의 탐욕", "🤑", "과열 — 현금 비중 확대"


@st.cache_data(ttl=3600)
def _cnn_fear_greed() -> int | None:
    """CNN Fear & Greed Index (0~100). 미장 전용. 1시간 캐시. 실패 시 None."""
    try:
        import urllib.request, ssl, json as _json
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://edition.cnn.com/",
            "Origin": "https://edition.cnn.com",
        }
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        req = urllib.request.Request(url, headers=headers)
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            data = _json.loads(r.read())
        return int(round(float(data["fear_and_greed"]["score"])))
    except Exception:
        return None


def _fear_greed_kr(buy_ratio: float, avg_er) -> int:
    """국장 자체 공탐지수: 저평가 비율 + 기대수익률 기반."""
    a = 90 - 160 * buy_ratio
    if avg_er is not None:
        b = 70 - 2.5 * avg_er
        score = (a + b) / 2
    else:
        score = a
    return int(max(0, min(100, round(score))))


# 마켓 판별
_rs = st.session_state.get("result_source", "")
_is_us = _rs == "auto:us" or (
    _rs == "custom" and all(not v.f.ticker.endswith(".KS") and not v.f.ticker.endswith(".KQ")
                            for v in verdicts[:3])
)

if _is_us:
    _cnn = _cnn_fear_greed()
    fg_score = _cnn if _cnn is not None else _fear_greed_kr(buy_ratio, avg_er)
    _source_hint = "출처: CNN Fear & Greed Index" if _cnn is not None else "CNN 연결 실패 — 자체 추정"
else:
    fg_score = _fear_greed_kr(buy_ratio, avg_er)
    _source_hint = "출처: 버핏봇 자체 산출 (저평가 비율·기대수익률)"

fg_label, fg_emoji, fg_hint = _fear_greed_label(fg_score)
fg_color = "#ff7a7a" if fg_score >= 56 else ("#34f5a0" if fg_score <= 44 else "#ffce4d")
temp = (f"<span style='color:{fg_color};font-size:1.9rem;font-weight:800'>{fg_emoji} {fg_score}</span>"
        f"<br><span style='font-size:.82rem;color:#cbd5e1'>{fg_label}</span>"
        f"<br><span style='font-size:.7rem;color:#8b95a5'>{fg_hint}</span>"
        f"<br><span style='font-size:.65rem;color:#6b7280'>{_source_hint}</span>")

from pathlib import Path as _Path
from datafetch import CACHE_DIR as _CACHE_DIR, CACHE_VERSION as _CV

def _data_timestamp() -> str:
    import os
    files = list(_CACHE_DIR.glob(f"*_{_CV}_*.json"))
    if not files:
        from datetime import datetime
        return datetime.now().strftime("%Y년 %m월 %d일 %H:%M") + " 기준 (실시간 수집)"
    latest = max(files, key=lambda p: p.stat().st_mtime)
    from datetime import datetime, timezone, timedelta
    kst = timezone(timedelta(hours=9))
    dt = datetime.fromtimestamp(latest.stat().st_mtime, tz=kst)
    return dt.strftime("%Y년 %m월 %d일 %H:%M KST 기준")


def _market_indicators():
    """캐시 파일에서 환율·금리 로드. 없으면 실시간 수집."""
    import json as _json
    from pathlib import Path as _P
    _ind_path = _P(__file__).parent / "cache" / "market_indicators.json"
    if _ind_path.exists():
        try:
            d = _json.loads(_ind_path.read_text(encoding="utf-8"))
            return (d.get("usd_krw") or "—", d.get("jpy_krw_100") or "—",
                    d.get("us_rate") or "—", d.get("kr_rate") or "2.75%")
        except Exception:
            pass
    # 파일 없으면 실시간 fallback
    try:
        import yfinance as yf
        def _px(t):
            tk = yf.Ticker(t)
            v = tk.fast_info.get("lastPrice") or tk.info.get("regularMarketPrice")
            return float(v) if v else None
        usd = _px("USDKRW=X"); jpy = _px("JPYKRW=X"); irx = _px("^IRX")
        return (
            f"₩{usd:,.0f}" if usd else "—",
            f"₩{jpy*100:,.1f}" if jpy else "—",
            f"{irx:.2f}%" if irx else "—",
            "2.75%",
        )
    except Exception:
        return "—", "—", "—", "2.75%"


_usd_str, _jpy_str, _us_rate_str, _KR_RATE = _market_indicators()
_rate_card = (
    f"<span style='font-size:1.5rem;font-weight:800;color:#e2e8f0'>{_us_rate_str}</span>"
    f"<br><span style='font-size:.72rem;color:#8b95a5'>미국 기준금리 (IRX 근사)</span>"
) if _is_us else (
    f"<span style='font-size:1.5rem;font-weight:800;color:#e2e8f0'>{_KR_RATE}</span>"
    f"<br><span style='font-size:.72rem;color:#8b95a5'>한국 기준금리</span>"
)

_ts = st.session_state.get("data_ts") or _data_timestamp()

_er_pill = (f'<span class="mini-pill er">📈 평균 기대수익 {avg_er:.0f}%</span>'
            if avg_er is not None else "")
_mkt_badge = ""
_rs_now = st.session_state.get("result_source", "")
if _rs_now == "auto:kr":   _mkt_badge = "🇰🇷 국장 "
elif _rs_now == "auto:us": _mkt_badge = "🇺🇸 미장 "
st.markdown(f"""
<div class="hero">
  <h1>📊 {_mkt_badge}분석 결과</h1>
  <p>{n}개 종목을 버핏 잣대로 채점했습니다. {'강력 매수 ' + str(len(strong)) + '종목 발견!' if strong else '오늘은 강력 매수 등급이 없습니다 — 정상입니다.'}</p>
  <div class="mini-pills">
    <span class="mini-pill buy">✅ 지금 매수 {len(buys)}</span>
    <span class="mini-pill wait">⏳ 목표가 대기 {len(waits)}</span>
    <span class="mini-pill avoid">🚫 회피 {len(avoids)}</span>
    {_er_pill}
  </div>
  <span class="tag" style="margin-top:12px">🕗 {_ts}</span>
</div>
<div class="kpi-row">
  <div class="kpi-card temp"><div class="num">{temp}</div><div class="lbl">😱 공포·탐욕 지수</div></div>
  <div class="kpi-card">
    <div class="num"><span style='font-size:1.5rem;font-weight:800;color:#e2e8f0'>{_usd_str}</span><br><span style='font-size:.72rem;color:#8b95a5'>💵 달러 / 원</span></div>
    <div class="lbl" style="margin-top:8px"><span style='font-size:1.5rem;font-weight:800;color:#e2e8f0'>{_jpy_str}</span><br><span style='font-size:.72rem;color:#8b95a5'>💴 100엔 / 원</span></div>
  </div>
  <div class="kpi-card"><div class="num">🏦 {_rate_card}</div></div>
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
            st.markdown(pick_card_html(v, i, sec_map, advisor.conviction_stars(v),
                                       display_name=disp_name(v)),
                        unsafe_allow_html=True)
            key = f"spot_detail_{v.f.ticker}"
            is_open = st.session_state.get(key, False)
            btn_label = "▲ 상세 조언 닫기" if is_open else "📋 상세 조언 보기"
            if st.button(btn_label, key=f"btn_{v.f.ticker}", width="stretch"):
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
    st.markdown('<div class="section-sub">총점 100 = 품질 75 + 가격 25 (+ 기술신호 ±3) · 열 제목 클릭 시 정렬</div>',
                unsafe_allow_html=True)

    # ── 필터 ──
    fc1, fc2, fc3 = st.columns([2, 2, 3])
    with fc1:
        rating_opts = ["🚀 강력 매수", "✅ 매수 검토", "⏳ 우량주·대기", "👀 관망", "🚫 회피"]
        sel_ratings = st.multiselect("등급 필터", rating_opts, default=[],
                                     placeholder="전체 등급", key="rank_rating")
    with fc2:
        all_secs = sorted({sec_map.get(v.f.ticker, v.f.sector) for v in verdicts})
        sel_secs = st.multiselect("섹터 필터", all_secs, default=[],
                                  placeholder="전체 섹터", key="rank_sec")
    with fc3:
        name_q = st.text_input("이름 검색", placeholder="예: 삼성, Apple…",
                               key="rank_name", label_visibility="visible")

    rows = []
    shown_verdicts = []   # 표에 보이는 행과 1:1 대응 (행 클릭 → 상세 조언용)
    for i, v in enumerate(verdicts, 1):
        f, m = v.f, v.metrics
        tech = getattr(m, "tech", None)
        _, emoji, short = rating_meta(v.rating)
        sec = sec_map.get(f.ticker, f.sector)
        nm = disp_name(v)

        # 필터 적용
        if sel_ratings and f"{emoji} {short}" not in sel_ratings:
            continue
        if sel_secs and sec not in sel_secs:
            continue
        if name_q and name_q.lower() not in nm.lower() and name_q.lower() not in f.ticker.lower():
            continue

        shown_verdicts.append(v)
        mos = v.valuation.get("mos_pct")
        er = v.valuation.get("exp_return")
        per_val = m.norm_per if m.norm_per is not None else f.per
        dy = getattr(f, "dividend_yield", None)
        rows.append({
            "#": i,
            "종목": nm[:18],
            "섹터": sec[:10],
            "시총": fmt_cap(getattr(f, "market_cap", None), f.currency),
            "총점": round(v.total, 1),
            "품질": round(v.quality, 1),
            "등급": f"{emoji} {short}",
            "PER": round(per_val, 1) if (per_val and per_val > 0) else None,
            "PBR": round(f.pbr, 1) if (f.pbr and f.pbr > 0) else None,
            "ROE%": round(f.roe * 100, 0) if f.roe is not None else None,
            "배당%": round(dy * 100, 1) if dy else None,
            "안전마진": round(mos * 100, 0) if mos is not None else None,
            "기대수익": round(er * 100, 0) if er is not None else None,
            "ROIC": round(m.roic * 100, 0) if m.roic is not None else None,
            "F스코어": m.fscore if m.fscore is not None else None,
            "기술신호": tech.label if (tech and tech.news_count > 0) else "—",
        })

    st.caption(f"표시 {len(rows)}개 / 전체 {len(verdicts)}개")

    # ── 상세 조언 볼 종목 선택 (체크박스 없이 한 번에) ──
    name_to_v = {f"{disp_name(v)} ({v.f.ticker})": v for v in shown_verdicts}
    picked = st.selectbox(
        "📋 상세 조언 볼 종목 선택 (이름 입력으로 검색 가능)",
        options=["— 선택 안 함 —"] + list(name_to_v.keys()),
        index=0,
        key="rank_pick",
    )
    if picked and picked != "— 선택 안 함 —":
        vsel = name_to_v[picked]
        _, emoji, short = rating_meta(vsel.rating)
        st.markdown(f"### {emoji} {disp_name(vsel)} ({vsel.f.ticker}) · {short} · {vsel.total:.0f}점")
        _render_detail(vsel)
        st.divider()

    df = pd.DataFrame(rows)
    st.dataframe(
        df, width="stretch", hide_index=True, height=560,
        column_config={
            "총점": st.column_config.ProgressColumn("총점", min_value=0, max_value=100,
                                                   format="%.0f"),
            "품질": st.column_config.NumberColumn("품질/75", format="%.0f"),
            "PER": st.column_config.NumberColumn("PER(배)", format="%.1f"),
            "PBR": st.column_config.NumberColumn("PBR(배)", format="%.1f"),
            "ROE%": st.column_config.NumberColumn("ROE%", format="%.0f%%"),
            "배당%": st.column_config.NumberColumn("배당%", format="%.1f%%"),
            "안전마진": st.column_config.NumberColumn("안전마진%", format="%+.0f%%"),
            "기대수익": st.column_config.NumberColumn("기대수익%", format="%.0f%%"),
            "ROIC": st.column_config.NumberColumn("ROIC%", format="%.0f%%"),
        },
    )
    if not df.empty:
        st.download_button(
            "⬇️ 표 CSV로 내려받기",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"buffett_{auto_market if view=='📊 전체 종목 분석' else 'custom'}.csv",
            mime="text/csv",
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
            "대표 종목": disp_name(best)[:16],
            "투자 관점": SECTOR_PHILOSOPHY.get(sec, ""),
        })
    sec_rows.sort(key=lambda x: -x["평균 품질"])
    sec_df = pd.DataFrame(sec_rows)
    st.dataframe(
        sec_df, width="stretch", hide_index=True,
        column_config={
            "평균 품질": st.column_config.ProgressColumn("평균 품질", min_value=0,
                                                      max_value=75, format="%.0f"),
        },
    )
    st.bar_chart(sec_df.set_index("섹터")[["평균 품질", "평균 총점"]], width="stretch")

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
            cc[0].markdown(f"**{disp_name(v)[:16]}** {badge_html(v.rating)}", unsafe_allow_html=True)
            cc[1].markdown(f"`{sec}`")
            cc[2].markdown(f"{money(v.f.price, v.f.currency)} → {money(v.valuation.get('fair'), v.f.currency)}")
            cc[3].markdown(f"{advisor.conviction_stars(v)}{er_s}")

        # ── 확신도 가중 비중 배분 제안 ──
        top_buys = sorted(buys, key=lambda v: (advisor.conviction_stars(v).count("★"),
                                               v.valuation.get("exp_return") or -9),
                          reverse=True)[:6]
        weights = [advisor.conviction_stars(v).count("★") for v in top_buys]
        wsum = sum(weights) or 1
        # 한 종목 최대 30%로 제한 후 재정규화 (집중 + 분산 균형)
        raw = [w / wsum for w in weights]
        capped = [min(r, 0.30) for r in raw]
        csum = sum(capped) or 1
        alloc = [c / csum for c in capped]
        st.markdown("#### 📐 추천 비중 (확신도 가중 · 한 종목 30% 상한)")
        alloc_rows = [{
            "종목": disp_name(v)[:16],
            "확신도": advisor.conviction_stars(v),
            "비중": round(a * 100, 0),
            "현재가→적정가": f"{money(v.f.price, v.f.currency)} → {money(v.valuation.get('fair'), v.f.currency)}",
        } for v, a in zip(top_buys, alloc)]
        st.dataframe(
            pd.DataFrame(alloc_rows), width="stretch", hide_index=True,
            column_config={
                "비중": st.column_config.ProgressColumn("추천 비중%", min_value=0,
                                                       max_value=30, format="%.0f%%"),
            },
        )
        st.caption("⚠️ 동일 비중이 아닌 **확신도 기준** 예시입니다. 실제 비중은 본인 위험 성향에 맞게 조정하세요.")
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
            cc[0].markdown(f"**{disp_name(v)[:16]}**")
            cc[1].markdown(f"{money(v.f.price, v.f.currency)} · {txt}")
            cc[2].markdown(f"품질 {v.quality:.0f}/75")

    if avoids:
        st.markdown("#### 🚫 회피")
        for v in avoids[:6]:
            why = v.flags[0] if v.flags else "지표 기준 미달"
            st.markdown(f"- **{disp_name(v)[:16]}** — {why}")

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
    if watch_btn or st.button("💾 '대기' 종목 목표가 워치리스트 저장", width="stretch"):
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
        with st.expander(f"{emoji} {disp_name(v)} ({v.f.ticker})  ·  {short}  ·  {v.total:.0f}점",
                         expanded=(idx == 0)):
            _render_detail(v)

st.divider()

# ── 지표 용어 설명 ────────────────────────────────────────────────────────
with st.expander("📖 지표 용어 설명 — 각 숫자가 무엇을 뜻하는지"):
    st.markdown("""
| 지표 | 뜻 | 버핏 기준 |
|---|---|---|
| **PER (주가수익비율)** | 주가 ÷ 주당순이익. 이익 대비 얼마나 비싸게 거래되는지. | 업종 평균 이하 선호. 단, 이익의 질이 더 중요 |
| **PBR (주가순자산비율)** | 주가 ÷ 주당순자산. 장부가 대비 시장 프리미엄. | 1배 미만이면 자산 대비 저렴, 단 ROE와 함께 봐야 |
| **ROE% (자기자본이익률)** | 순이익 ÷ 자기자본. 주주 돈을 얼마나 효율적으로 버는지. | **15% 이상** 꾸준히 유지해야 해자 증거 |
| **안전마진%** | (적정가 − 현재가) ÷ 적정가. 얼마나 싸게 살 수 있는지. | **+25% 이상**이면 매수 권장 (버핏의 핵심 원칙) |
| **기대수익%** | 현재가로 매수 시 연평균 예상 수익률 (DCF 역산). | **10% 이상**이면 매력적 |
| **ROIC% (투하자본이익률)** | 영업이익 ÷ 투하자본. 사업에 투자한 돈 대비 실제 번 돈. | **10% 이상** = 자본 파괴 안 함, **15% 이상** = 해자 신호 |
| **F스코어 (피오트로스키)** | 수익성·부채·효율 9개 항목 체크 (0~9점). 재무건전성 종합점수. | **7점 이상** = 우량, 4점 이하 = 위험 신호 |
| **기술신호** | 최신 뉴스에서 포착한 모멘텀 (HBM·AI수주·실적 서프라이즈 등). | 강한 상승·약한 상승·중립·하락 신호 4단계 |
| **총점 (100점)** | 수익성·해자(30) + 재무안정(25) + 성장(20) + 밸류에이션(25). | **70점 이상** = 관심, **80점 이상** = 강력 매수 후보 |
""")

st.caption("⚠️ 교육·연구용 참고 도구입니다. 자동매매가 아니며, 실제 매수 전 사업보고서·해자의 지속성·"
           "경영진의 자본배분을 직접 검증하세요.  \"리스크는 자신이 무엇을 하는지 모르는 데서 온다.\" — 워런 버핏")
