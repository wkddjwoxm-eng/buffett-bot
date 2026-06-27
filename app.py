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
import advisor   # 상세 렌더가 어느 경로에서든 쓰므로 최상단에서 임포트

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

/* ── 점수 breakdown 막대 ─────────────────────────────── */
.sbreak {margin:6px 0 2px;}
.srow {display:flex; align-items:center; gap:10px; margin:7px 0;}
.srow .slabel {flex:0 0 92px; font-size:.8rem; color:#cbd5e1;}
.srow .strack {flex:1; height:11px; border-radius:6px; background:rgba(255,255,255,.07); overflow:hidden;}
.srow .sfill {height:100%; border-radius:6px;}
.srow .sval {flex:0 0 56px; text-align:right; font-size:.8rem; font-weight:700; color:#e2e8f0;}

/* ── 밸류에이션 범위 바 ─────────────────────────────── */
.vrange {margin:10px 0 4px;}
.vtrack {position:relative; height:16px; border-radius:8px; overflow:hidden;
    background:linear-gradient(to right,
        rgba(0,255,136,.45) 0%, rgba(0,255,136,.30) var(--buy),
        rgba(255,196,0,.30) var(--buy), rgba(255,196,0,.25) var(--fair),
        rgba(255,75,75,.30) var(--fair), rgba(255,75,75,.35) 100%);}
.vmark {position:absolute; top:-4px; width:2px; height:24px;}
.vmark.price {background:#ffffff; box-shadow:0 0 6px rgba(255,255,255,.8);}
.vmark.fair  {background:#9aa4b2;}
.vmark.buy   {background:#34f5a0;}
.vlabels {display:flex; justify-content:space-between; font-size:.68rem; color:#7c8696; margin-top:6px;}
.vlegend {display:flex; gap:14px; font-size:.72rem; color:#9aa4b2; margin-top:8px; flex-wrap:wrap;}
.vlegend b {color:#e2e8f0;}

/* ── 섹터 히트맵 ─────────────────────────────────────── */
.heatgrid {display:flex; flex-wrap:wrap; gap:10px; margin:6px 0 4px;}
.heattile {
    flex:1 1 130px; min-width:120px; border-radius:13px; padding:12px 14px;
    border:1px solid rgba(255,255,255,.10);
}
.heattile .hs {font-size:.92rem; font-weight:800; color:#f1f5f9; letter-spacing:-.01em;}
.heattile .hm {font-size:1.35rem; font-weight:800; margin-top:4px; letter-spacing:-.02em;}
.heattile .hq {font-size:.72rem; color:#cbd5e1; margin-top:3px;}

/* ── 모바일 최적화 ───────────────────────────────────── */
@media (max-width:640px){
    .hero {padding:20px 18px; border-radius:16px;}
    .hero h1 {font-size:1.6rem;}
    .hero p {font-size:.92rem;}
    .brand .name {font-size:1.25rem;}
    .brand .logo {font-size:1.7rem;}
    .kpi-card {min-width:120px; padding:12px 13px;}
    .kpi-card .num {font-size:1.5rem;}
    .mini-pill {font-size:.75rem; padding:4px 9px;}
    .srow .slabel {flex:0 0 72px; font-size:.72rem;}
    .vlegend {gap:8px; font-size:.66rem;}
    /* 좁은 화면에선 배경 인물을 더 은은하게(가독성 우선) */
    [data-testid="stAppViewContainer"] > div:first-child {
        background-size: 130% auto !important;
        background-position: right -30px top !important;
    }
}
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
@st.cache_resource(ttl=1800, show_spinner="📊 분석 결과 불러오는 중…")
def _load_market_shared(market: str):
    """전 사용자 공유 1벌만 메모리에 올림(세션별 복제 방지 → Cloud OOM 예방).
    읽기 전용 렌더라 공유 안전. 30분 TTL로 새 수집 데이터 자동 반영."""
    import results_io
    return results_io.load_market(market)


def _resolve_one(ticker: str):
    """티커 1개 → (Verdict, 같은시장 peers). 사전수집 우선, 없으면 실시간.
    Cloud rate-limit 시에도 유니버스 종목은 사전수집으로 즉시 해결."""
    for mk in ("kr", "us"):
        try:
            vs, _ = _load_market_shared(mk)
        except Exception:
            vs = None
        for v in (vs or []):
            if v.f.ticker == ticker:
                return v, list(vs)
    # 유니버스 밖 — 실시간 조회
    try:
        from datafetch import fetch
        from buffett import evaluate
        f = fetch(ticker, use_cache=True)
        if f:
            return evaluate(f, fetch_tech=True), []
    except Exception:
        pass
    return None, []


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


# ── 워치리스트: 웹은 세션 기반(사용자별·재부팅 무관). CLI는 watchlist.py 파일. ──
def _wl_store() -> dict:
    return st.session_state.setdefault("watchlist", {})


def _wl_add_from_verdicts(verdicts) -> int:
    """대기(우량주 비쌈) 종목을 세션 워치리스트에 등록. 등록 수 반환."""
    store = _wl_store()
    n = 0
    for v in verdicts:
        buy = v.valuation.get("buy_below")
        if "대기" in v.rating and buy and v.f.price:
            if (1 - buy / v.f.price) > 0.55:   # 과도한 고평가는 제외
                continue
            store[v.f.ticker] = {
                "name": v.f.name, "currency": v.f.currency,
                "target": buy, "fair": v.valuation.get("fair"),
            }
            n += 1
    return n


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


def _score_breakdown_html(f, m) -> str:
    """버핏 100점이 4기둥 어디서 왔는지 막대로 시각화 (보존된 f로 즉석 재계산)."""
    import buffett as _bf
    try:
        p, _ = _bf.score_profitability(f, m.roic)
        s, _ = _bf.score_strength(f)
        g, _ = _bf.score_growth(f)
        va, _ = _bf.score_valuation(f, m.norm_per, m.cyclical)
    except Exception:
        return ""
    pillars = [
        ("수익성·해자", p, 30, "#00ff88"),
        ("재무안정",   s, 25, "#00d4ff"),
        ("성장성",     g, 20, "#a78bfa"),
        ("밸류에이션", va, 25, "#ffce4d"),
    ]
    rows = ""
    for label, sc, mx, col in pillars:
        pct = max(0, min(100, sc / mx * 100))
        rows += (f'<div class="srow"><span class="slabel">{label}</span>'
                 f'<div class="strack"><div class="sfill" style="width:{pct:.0f}%;'
                 f'background:{col}"></div></div>'
                 f'<span class="sval">{sc:.0f}/{mx}</span></div>')
    return f'<div class="sbreak">{rows}</div>'


def _valuation_range_html(f, val) -> str:
    """약세~강세 내재가치 범위에서 현재가·적정가·매수가 위치를 한눈에."""
    sc = val.get("scenarios") or {}
    bear, bull = sc.get("bear"), sc.get("bull")
    price, fair, buy = f.price, val.get("fair"), val.get("buy_below")
    if not all(isinstance(x, (int, float)) and x > 0 for x in (bear, bull, price)):
        return ""
    fair = fair or (bear + bull) / 2
    buy = buy or fair * 0.75
    lo = min(bear, buy, price) * 0.97
    hi = max(bull, price, fair) * 1.03
    span = (hi - lo) or 1
    def pos(x):
        return max(0, min(100, (x - lo) / span * 100))
    p_price, p_fair, p_buy = pos(price), pos(fair), pos(buy)
    cur = f.currency
    fmt = lambda x: money(x, cur)
    cheap = price <= (buy or 0)
    verdict = ("🟢 안전마진 구간 (싸다)" if cheap else
               ("🟡 적정~약간 비쌈" if price <= (fair or 0) else "🔴 적정가치 위 (비싸다)"))
    return (
        f'<div class="vrange">'
        f'<div class="vtrack" style="--buy:{p_buy:.0f}%; --fair:{p_fair:.0f}%">'
        f'<div class="vmark buy" style="left:{p_buy:.0f}%"></div>'
        f'<div class="vmark fair" style="left:{p_fair:.0f}%"></div>'
        f'<div class="vmark price" style="left:{p_price:.0f}%"></div>'
        f'</div>'
        f'<div class="vlabels"><span>🐻 {fmt(bear)}</span><span>🐂 {fmt(bull)}</span></div>'
        f'<div class="vlegend">'
        f'<span>🟢 매수권장 <b>{fmt(buy)}</b></span>'
        f'<span>⚪ 적정가 <b>{fmt(fair)}</b></span>'
        f'<span>⬜ 현재가 <b>{fmt(price)}</b></span>'
        f'<span>→ {verdict}</span>'
        f'</div></div>'
    )


def _valuation_reliability_note(v) -> str | None:
    """적정가 추정이 극단 구간이면 정밀도 한계를 정직하게 안내(데이터/버블 무관)."""
    val, f = v.valuation, v.f
    mos = val.get("mos_pct")
    fair, price = val.get("fair"), f.price
    if not (fair and price and price > 0):
        return None
    if mos is not None and mos < -2.0:        # 현재가 ≥ 적정가 3배
        mult = price / fair
        return (f"현재가가 추정 적정가의 약 **{mult:.0f}배**입니다. 극단적 고평가 구간에서는 "
                f"DCF 적정가 *수치*의 정밀도가 낮으니, 정확한 적정가보다 **등급(회피/관망)**과 "
                f"방향성만 참고하세요. (고PER 성장·사이클주에서 흔함)")
    if mos is not None and mos > 0.85:        # 적정가 ≥ 현재가 6.7배
        return (f"추정 적정가가 현재가의 **{fair/price:.0f}배**로 비정상적으로 높습니다 — "
                f"일회성 이익·주식수/통화 데이터 오류 가능. 원문(국장 DART·미장 SEC) 확인을 권합니다.")
    return None


def _peer_context_lines(v) -> list[str]:
    """동종업계(같은 섹터) 중앙값 대비 PER·ROE·ROIC 위치를 한 줄씩."""
    import statistics
    verdicts = st.session_state.get("verdicts", [])
    sec_map = st.session_state.get("sec_map", {})
    sec = sec_map.get(v.f.ticker, v.f.sector)
    peers = [p for p in verdicts if sec_map.get(p.f.ticker, p.f.sector) == sec]
    if len(peers) < 4:
        return []

    def med(getter):
        xs = [g for g in (getter(p) for p in peers) if g is not None and g > 0]
        return statistics.median(xs) if len(xs) >= 4 else None

    def cmp_word(x, m, lower_better):
        if x is None or m is None:
            return None
        ratio = x / m
        if 0.9 <= ratio <= 1.1:
            return "비슷"
        if lower_better:
            return "저렴" if x < m else "비쌈"
        return "우수" if x > m else "열위"

    lines = []
    per_v = v.metrics.norm_per if v.metrics.norm_per is not None else v.f.per
    per_m = med(lambda p: (p.metrics.norm_per if p.metrics.norm_per is not None else p.f.per))
    w = cmp_word(per_v, per_m, lower_better=True)
    if w:
        lines.append(f"**PER** {per_v:.1f}배 vs 섹터 중앙값 {per_m:.1f}배 → **{w}**")
    roe_m = med(lambda p: (p.f.roe * 100 if p.f.roe is not None else None))
    if v.f.roe is not None:
        w = cmp_word(v.f.roe * 100, roe_m, lower_better=False)
        if w:
            lines.append(f"**ROE** {v.f.roe*100:.0f}% vs 섹터 중앙값 {roe_m:.0f}% → **{w}**")
    roic_m = med(lambda p: (p.metrics.roic * 100 if p.metrics.roic is not None else None))
    if v.metrics.roic is not None:
        w = cmp_word(v.metrics.roic * 100, roic_m, lower_better=False)
        if w:
            lines.append(f"**ROIC** {v.metrics.roic*100:.0f}% vs 섹터 중앙값 {roic_m:.0f}% → **{w}**")
    return lines


def _render_detail(v, show_memo: bool = False):
    """종목 상세 조언 블록 (스포트라이트 카드 클릭 + Tab4에서 공용).

    show_memo=True 는 '종목 선택' 경로(한 번에 1개만 렌더)에서만 켠다.
    여러 곳에서 동시 렌더되면 text_area key가 충돌하므로 기본은 False.
    """
    from advisor import _one_liner, _sector_context, _metric_narrative
    f, m, val = v.f, v.metrics, v.valuation
    cur = f.currency
    tech = getattr(m, "tech", None)
    fmt = lambda x: money(x, cur)

    with st.container(border=True):
        # ── 섹터 배경 설명 ──
        ctx = _sector_context(v)
        if ctx:
            st.markdown("#### 🌐 섹터 배경")
            st.info(ctx)

        # ── 왜 매수/주의인가 — 지표 해석 ──
        metric_lines = _metric_narrative(v)
        if metric_lines:
            st.markdown("#### 📊 주요 지표 해석")
            for ln in metric_lines:
                st.markdown(f"- {ln}")

        st.divider()

        # ── 동종업계 대비 위치 ──
        peer_lines = _peer_context_lines(v)
        if peer_lines:
            sec_nm = st.session_state.get("sec_map", {}).get(f.ticker, f.sector)
            st.markdown(f"#### 🏷️ 동종업계({sec_nm}) 대비")
            for ln in peer_lines:
                st.markdown(f"- {ln}")

        # ── 버핏 점수 breakdown (100점이 어디서 왔나) ──
        sb = _score_breakdown_html(f, m)
        if sb:
            st.markdown(f"#### 🏆 버핏 점수 구성 — 품질 {v.quality:.0f}/75 + 가격 {v.value:.0f}/25 = **{v.total:.0f}/100**")
            st.markdown(sb, unsafe_allow_html=True)

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

        # ── 적정가 신뢰도 경고 (극단 구간) ──
        rel_note = _valuation_reliability_note(v)
        if rel_note:
            st.warning(f"⚠️ **적정가 추정 주의** — {rel_note}")

        # ── 시나리오 DCF + 밸류에이션 범위 시각화 ──
        sc = val.get("scenarios", {})
        if sc:
            st.divider()
            d1, d2, d3 = st.columns(3)
            d1.metric("🐻 약세 시나리오", fmt(sc.get("bear")))
            d2.metric("📊 기본 시나리오", fmt(sc.get("base")))
            d3.metric("🐂 강세 시나리오", fmt(sc.get("bull")))
            vr = _valuation_range_html(f, val)
            if vr:
                st.markdown("##### 📍 지금 가격은 어디쯤? (내재가치 범위 內 현재가 위치)")
                st.markdown(vr, unsafe_allow_html=True)
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

        # ── 내 투자 메모 (이 브라우저 세션에 저장) ──
        if show_memo:
            memos = st.session_state.setdefault("memos", {})
            tk = f.ticker
            note = st.text_area(
                "📝 내 투자 메모 (이 종목에 대한 생각·매수 조건 등 — 세션 저장)",
                value=memos.get(tk, ""),
                key=f"memo_input_{tk}",
                placeholder="예: 105달러 아래로 오면 1차 매수, 클라우드 성장률 둔화 주시…",
                height=90,
            )
            if note != memos.get(tk, ""):
                memos[tk] = note
            if note.strip():
                st.caption("✅ 메모가 이 세션에 저장됐습니다.")


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
check_btn = False
search_pick_ticker = None
top_n = 8
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
    from search_db import search as stock_search

    sc1, sc2 = st.columns([3, 1])
    with sc1:
        search_q = st.text_input(
            "🔎 회사 이름·티커로 검색 — 고르면 바로 상세분석이 열립니다",
            placeholder="예: 삼성, 기아, 애플, Tesla, AAPL, 005930…",
            key="search_q",
        )
    with sc2:
        check_btn = st.button("🔔 워치리스트 점검", width="stretch")

    if search_q:
        hits = stock_search(search_q, max_results=20)
        if hits:
            picked = st.selectbox(
                "종목 선택 (선택 즉시 상세분석)",
                options=[h["display"] for h in hits],
                index=0,
                key="search_pick_box",
            )
            mm = re.search(r'\(([^)]+)\)$', picked or "")
            if mm:
                search_pick_ticker = mm.group(1)
        else:
            st.caption("검색 결과 없음 — 다른 이름이나 티커로 시도해보세요.")

st.caption("⚠️ 교육·연구용 참고 도구. 투자 책임은 본인에게 있습니다.")


# ─────────────────────────────────────────────────────────────────────────
# 워치리스트 점검 (분석 없이 즉시)
# ─────────────────────────────────────────────────────────────────────────
if check_btn:
    from datafetch import fetch

    st.markdown('<div class="hero"><h1>🔔 워치리스트 점검</h1>'
                '<p>저장한 목표가에 현재가가 도달했는지 확인합니다. (이 브라우저 세션 기준)</p></div>',
                unsafe_allow_html=True)
    data = _wl_store()
    if not data:
        st.info("워치리스트가 비어 있습니다. 먼저 분석 후 포트폴리오 탭에서 '대기' 종목을 저장하세요.")
    else:
        with st.spinner("현재가 조회 중..."):
            for tk, w in data.items():
                f = fetch(tk, use_cache=False)
                c = "₩" if w["currency"] == "KRW" else "$"
                dec = 0 if w["currency"] == "KRW" else 2
                if not f or not f.price:
                    st.info(f"  {w['name']} ({tk}): 가격 조회 실패"); continue
                price = f"{c}{f.price:,.{dec}f}"
                target = f"{c}{w['target']:,.{dec}f}"
                if f.price <= w["target"]:
                    st.success(f"🔔 {w['name']} ({tk}): 현재 {price} ≤ 목표 {target} — 매수 검토 구간 도달!")
                else:
                    drop = (1 - w["target"] / f.price) * 100
                    st.info(f"· {w['name']} ({tk}): 현재 {price} (목표 {target}까지 −{drop:.0f}% 더 하락 필요)")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────
# 직접 종목 검색: 고른 종목을 즉시 상세분석 (대시보드 대신 상세 바로 표시)
# ─────────────────────────────────────────────────────────────────────────
if view == "🔎 직접 종목 검색":
    if not search_pick_ticker:
        st.markdown("""
        <div class="hero">
          <h1>🔎 개별 종목 검색</h1>
          <p>위에서 회사 이름이나 티커를 검색하고 종목을 고르면<br>
          <b>바로 그 종목의 상세분석</b>(점수·적정가·매수가·이유·위험·동종업계 비교)이 열립니다.</p>
          <span class="tag">국장·미장 어떤 종목이든 검색 가능</span>
        </div>
        """, unsafe_allow_html=True)
        st.info('💡 *"훌륭한 기업을 적당한 가격에 사라. 그저 그런 기업을 헐값에 사는 것보다 낫다."* — 워런 버핏')
        st.stop()

    with st.spinner("분석 중…"):
        _v, _peers = _resolve_one(search_pick_ticker)
    if not _v:
        st.error("종목 데이터를 가져오지 못했습니다. 잠시 후 다시 시도하거나 다른 종목으로 검색해보세요. "
                 "(실시간 데이터 제공처가 일시적으로 응답하지 않을 수 있습니다)")
        st.stop()

    _nmap = ticker_name_map()
    _nm = _nmap.get(_v.f.ticker) or _v.f.name
    _cls, _emoji, _short = rating_meta(_v.rating)
    st.session_state["verdicts"] = _peers or [_v]   # 동종업계 비교용
    st.session_state["sec_map"] = ticker_sector_map()
    st.session_state["name_map"] = _nmap
    st.session_state["result_source"] = "custom"
    st.markdown(f"## {_emoji} {_nm} ({_v.f.ticker}) · {_short} · {_v.total:.0f}점")
    st.markdown(badge_html(_v.rating), unsafe_allow_html=True)
    _render_detail(_v, show_memo=True)
    st.stop()


# ─────────────────────────────────────────────────────────────────────────
# 분석 실행 → session_state 보관 (재실행 시 재수집 방지)
# ─────────────────────────────────────────────────────────────────────────
def run_analysis(tickers: list[str], use_cache: bool, fetch_tech: bool):
    from buffett import evaluate
    from datafetch import fetch
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # 중복 제거 + 빈 입력 방어 (0 division·빈 화면 예방)
    tickers = list(dict.fromkeys(t for t in tickers if t))
    total = len(tickers)
    if total == 0:
        return []
    bar = st.progress(0.0, text=f"병렬 데이터 수집 중… (0/{total})")
    status = st.empty()

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
    try:
        loaded_verdicts, loaded_ts = _load_market_shared(auto_market)
    except Exception:
        loaded_verdicts, loaded_ts = None, None

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

# (직접 종목 검색 모드는 위에서 이미 처리·정지함 — 여기는 전체 분석 모드 전용)
if not ready:
    st.stop()


# ─────────────────────────────────────────────────────────────────────────
# 결과 렌더링
# ─────────────────────────────────────────────────────────────────────────

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

from datafetch import CACHE_DIR as _CACHE_DIR, CACHE_VERSION as _CV

def _data_timestamp() -> str:
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

# ── 데이터 신선도 점검 (자동 수집 모드만) ──────────────────────────────────
if _rs_now in ("auto:kr", "auto:us"):
    try:
        import results_io as _rio
        _age = _rio.market_age_hours(_rs_now.split(":")[1])
        if _age is not None and _age > 30:   # 하루 2회(12h) 기준 2회 이상 누락
            _days = _age / 24
            st.warning(f"⚠️ 데이터가 약 **{_days:.1f}일 전** 기준입니다 — 최근 자동 수집이 지연됐을 수 있어요. "
                       f"수치는 마지막 정상 수집 시점 기준이며, 곧 자동 갱신됩니다.")
    except Exception:
        pass
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

# ── 오늘의 결론 한 줄 (가장 중요한 액션 메시지) ────────────────────────────
_mkt_kor = "국장" if _is_us is False else "미장"
if strong:
    best = max(strong, key=lambda v: (v.valuation.get("exp_return") or -9, v.total))
    _be = best.valuation.get("exp_return")
    _bm = best.valuation.get("mos_pct")
    _extra = []
    if _bm is not None: _extra.append(f"안전마진 {_bm*100:+.0f}%")
    if _be is not None: _extra.append(f"기대수익 {_be*100:.0f}%")
    _ex = f" ({' · '.join(_extra)})" if _extra else ""
    st.success(f"##### 🟢 오늘의 결론 — 지금 사도 좋은 종목 **{len(buys)}개**, "
               f"그중 1순위는 **{disp_name(best)}**{_ex}. 아래 카드에서 근거 확인.")
elif buys:
    st.success(f"##### 🟢 오늘의 결론 — 안전마진을 주는 매수 후보 **{len(buys)}개** 발견. "
               f"강력 등급은 없지만 선별 매수 가능 구간.")
elif waits:
    st.warning(f"##### 🟡 오늘의 결론 — 지금 {_mkt_kor}은 **살 만한 가격이 아님**. "
               f"우량주 **{len(waits)}개**가 '목표가 대기' 중 — 더 빠지면 기회. (버핏: 기다림도 전략)")
else:
    st.error("##### 🔴 오늘의 결론 — 기준을 통과하는 매수·대기 후보가 없음. 현금 보유 우위.")

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
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏆 전체 랭킹", "🏭 섹터 진단", "💼 포트폴리오", "📋 상세 조언", "⚖️ 종목 비교"])

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
        _render_detail(vsel, show_memo=True)
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
        moss = [x.valuation.get("mos_pct") for x in vs if x.valuation.get("mos_pct") is not None]
        avg_mos = (sum(moss) / len(moss) * 100) if moss else None
        n_buy = sum(1 for x in vs if advisor._bucket(x) == "buy")
        sec_rows.append({
            "섹터": sec,
            "평균 품질": round(sum(x.quality for x in vs) / len(vs), 1),
            "평균 총점": round(sum(x.total for x in vs) / len(vs), 1),
            "평균 안전마진": round(avg_mos, 0) if avg_mos is not None else None,
            "매수후보": n_buy,
            "종목수": len(vs),
            "대표 종목": disp_name(best)[:16],
            "투자 관점": SECTOR_PHILOSOPHY.get(sec, ""),
        })

    cs1, cs2 = st.columns([1, 3])
    with cs1:
        sort_key = st.radio("정렬 기준", ["평균 품질", "저평가도(안전마진)", "매수후보 수"],
                            key="sec_sort", label_visibility="collapsed")
    _key = {"평균 품질": ("평균 품질", -1), "저평가도(안전마진)": ("평균 안전마진", -1),
            "매수후보 수": ("매수후보", -1)}[sort_key]
    sec_rows.sort(key=lambda x: ((x[_key[0]] if x[_key[0]] is not None else -999) * _key[1]))

    # 저평가 매력 섹터 한 줄 요약
    cheapest = max((r for r in sec_rows if r["평균 안전마진"] is not None),
                   key=lambda r: r["평균 안전마진"], default=None)
    if cheapest and cheapest["평균 안전마진"] > 0:
        st.success(f"💡 지금 가장 **저평가된 섹터는 ‘{cheapest['섹터']}’** "
                   f"(평균 안전마진 {cheapest['평균 안전마진']:+.0f}%, 매수후보 {cheapest['매수후보']}개)")

    # ── 저평가 히트맵 (초록=쌈 / 빨강=비쌈) ──
    def _heat_color(mos):
        if mos is None:
            return "rgba(255,255,255,.04)"
        t = max(-60.0, min(40.0, mos))          # -60%~+40% 클램프
        if t >= 0:
            a = 0.18 + 0.32 * (t / 40)           # 초록 강도
            return f"rgba(0,255,136,{a:.2f})"
        a = 0.15 + 0.30 * (-t / 60)              # 빨강 강도
        return f"rgba(255,75,75,{a:.2f})"
    tiles = ""
    for r in sorted(sec_rows, key=lambda x: (x["평균 안전마진"] if x["평균 안전마진"] is not None else -999), reverse=True):
        mos = r["평균 안전마진"]
        mos_txt = f"{mos:+.0f}%" if mos is not None else "—"
        col = "#34f5a0" if (mos or -1) >= 0 else "#ff9a9a"
        tiles += (f'<div class="heattile" style="background:{_heat_color(mos)}">'
                  f'<div class="hs">{r["섹터"]}</div>'
                  f'<div class="hm" style="color:{col}">{mos_txt}</div>'
                  f'<div class="hq">품질 {r["평균 품질"]:.0f}/75 · 매수 {r["매수후보"]}개 · {r["종목수"]}종목</div>'
                  f'</div>')
    st.markdown("##### 🗺️ 섹터 저평가 히트맵 — 평균 안전마진 (🟢 쌈 · 🔴 비쌈)")
    st.markdown(f'<div class="heatgrid">{tiles}</div>', unsafe_allow_html=True)
    st.caption("")

    sec_df = pd.DataFrame(sec_rows)
    st.dataframe(
        sec_df, width="stretch", hide_index=True,
        column_config={
            "평균 품질": st.column_config.ProgressColumn("평균 품질", min_value=0,
                                                      max_value=75, format="%.0f"),
            "평균 안전마진": st.column_config.NumberColumn("평균 안전마진%", format="%+.0f%%"),
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
    if st.button("💾 '대기' 종목 목표가 워치리스트 저장", width="stretch"):
        cnt = _wl_add_from_verdicts(verdicts)
        st.success(f"✅ '대기' 종목 {cnt}개를 워치리스트에 저장했습니다 (이 브라우저 세션 기준). "
                   f"직접 검색 모드의 '🔔 점검'으로 목표가 도달을 확인하세요.")

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

# Tab5: 종목 비교
with tab5:
    st.markdown('<div class="section-sub">2~4개 종목을 나란히 비교 — 각 지표의 우승자에 ⭐</div>',
                unsafe_allow_html=True)
    _name_to_v = {f"{disp_name(v)} ({v.f.ticker})": v for v in verdicts}
    _default = list(_name_to_v.keys())[:2]
    picks = st.multiselect("비교할 종목 (2~4개)", options=list(_name_to_v.keys()),
                           default=_default, max_selections=4, key="cmp_pick")
    cmp_vs = [_name_to_v[p] for p in picks]

    if len(cmp_vs) < 2:
        st.info("종목을 **2개 이상** 선택하면 나란히 비교합니다.")
    else:
        import buffett as _bf

        def _pillars(v):
            f, m = v.f, v.metrics
            try:
                return (_bf.score_profitability(f, m.roic)[0], _bf.score_strength(f)[0],
                        _bf.score_growth(f)[0], _bf.score_valuation(f, m.norm_per, m.cyclical)[0])
            except Exception:
                return (None, None, None, None)

        # (라벨, 값추출, 높을수록좋음, 포맷)
        def _per(v):
            pv = v.metrics.norm_per if v.metrics.norm_per is not None else v.f.per
            return pv if (pv and pv > 0) else None
        specs = [
            ("총점 /100",   lambda v: round(v.total, 1),                         True,  lambda x: f"{x:.0f}"),
            ("품질 /75",    lambda v: round(v.quality, 1),                       True,  lambda x: f"{x:.0f}"),
            ("가격점수 /25", lambda v: round(v.value, 1),                         True,  lambda x: f"{x:.0f}"),
            ("PER",        _per,                                                False, lambda x: f"{x:.1f}배"),
            ("PBR",        lambda v: v.f.pbr if (v.f.pbr and v.f.pbr > 0) else None, False, lambda x: f"{x:.1f}배"),
            ("ROE%",       lambda v: v.f.roe * 100 if v.f.roe is not None else None, True, lambda x: f"{x:.0f}%"),
            ("ROIC%",      lambda v: v.metrics.roic * 100 if v.metrics.roic is not None else None, True, lambda x: f"{x:.0f}%"),
            ("배당%",       lambda v: getattr(v.f, "dividend_yield", None) and v.f.dividend_yield * 100, True, lambda x: f"{x:.1f}%"),
            ("안전마진%",   lambda v: v.valuation.get("mos_pct") and v.valuation["mos_pct"] * 100, True, lambda x: f"{x:+.0f}%"),
            ("기대수익%",   lambda v: v.valuation.get("exp_return") and v.valuation["exp_return"] * 100, True, lambda x: f"{x:.0f}%"),
            ("F스코어 /9",  lambda v: v.metrics.fscore,                          True,  lambda x: f"{x:.0f}"),
        ]
        cols = ["지표"] + [disp_name(v)[:14] for v in cmp_vs]
        table = []
        for label, getter, higher, fmt in specs:
            vals = [getter(v) for v in cmp_vs]
            nums = [x for x in vals if isinstance(x, (int, float))]
            best = (max(nums) if higher else min(nums)) if nums else None
            row = {"지표": label}
            for v, x in zip(cmp_vs, vals):
                cell = fmt(x) if isinstance(x, (int, float)) else "—"
                if best is not None and isinstance(x, (int, float)) and x == best and len(nums) > 1:
                    cell = f"⭐ {cell}"
                row[disp_name(v)[:14]] = cell
            table.append(row)
        # 현재가·적정가·등급 행
        for label, getter in [("현재가", lambda v: money(v.f.price, v.f.currency)),
                              ("적정가", lambda v: money(v.valuation.get("fair"), v.f.currency)),
                              ("등급", lambda v: rating_meta(v.rating)[1] + " " + rating_meta(v.rating)[2])]:
            row = {"지표": label}
            for v in cmp_vs:
                row[disp_name(v)[:14]] = getter(v)
            table.append(row)

        st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")

        # 4기둥 점수 막대 나란히
        st.markdown("##### 🏆 버핏 점수 구성 비교")
        bcols = st.columns(len(cmp_vs))
        for col, v in zip(bcols, cmp_vs):
            with col:
                st.markdown(f"**{disp_name(v)[:14]}** · {v.total:.0f}점")
                sb = _score_breakdown_html(v.f, v.metrics)
                if sb:
                    st.markdown(sb, unsafe_allow_html=True)

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
