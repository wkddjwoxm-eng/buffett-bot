"""
버핏 봇 — 웹 UI (Streamlit)

실행: streamlit run app.py
브라우저에서 http://localhost:8501 자동 오픈
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="버핏 봇 — 장기 가치투자 스크리너",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────
# 사이드바 — 입력
# ─────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 버핏 봇")
    st.caption("워런 버핏식 장기 가치투자 스크리너")
    st.divider()

    mode = st.radio("분석 모드", ["유니버스 스크리닝", "직접 종목 입력"])

    if mode == "유니버스 스크리닝":
        market = st.selectbox("마켓", ["국장 (KR)", "미장 (US)", "전체 (All)"])
        market_code = {"국장 (KR)": "kr", "미장 (US)": "us", "전체 (All)": "all"}[market]
        custom_tickers = []
    else:
        ticker_input = st.text_area(
            "티커 입력 (쉼표 또는 줄바꿈으로 구분)",
            placeholder="예: AAPL, MSFT\n005930.KS, 000270.KS",
            height=120,
        )
        custom_tickers = [t.strip().upper() for t in ticker_input.replace("\n", ",").split(",") if t.strip()]
        market_code = "custom"

    st.divider()
    top_n = st.slider("상세 조언 상위 종목 수", 3, 20, 8)
    use_cache = st.toggle("당일 캐시 사용 (빠름)", value=True)
    fetch_tech = st.toggle("기술변곡점 뉴스 분석 포함", value=True)

    st.divider()
    run_btn = st.button("🔍 분석 시작", type="primary", use_container_width=True)

    st.divider()
    st.caption("📌 워치리스트")
    watch_btn = st.button("💾 대기 종목 목표가 저장", use_container_width=True)
    check_btn = st.button("🔔 목표가 도달 점검", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────
# 워치리스트 점검 (분석 없이)
# ─────────────────────────────────────────────────────────────────────────
if check_btn:
    import watchlist as wl
    from datafetch import fetch

    st.header("🔔 워치리스트 목표가 점검")
    data = wl.load()
    if not data:
        st.info("워치리스트가 비어 있습니다. 먼저 분석 후 '대기 종목 목표가 저장'을 눌러주세요.")
    else:
        with st.spinner("현재가 조회 중..."):
            lines = wl.check(lambda tk: fetch(tk, use_cache=False))
        for ln in lines:
            if "🔔" in ln:
                st.success(ln.strip())
            else:
                st.info(ln.strip())
    st.stop()

# ─────────────────────────────────────────────────────────────────────────
# 메인 분석
# ─────────────────────────────────────────────────────────────────────────
if not run_btn:
    # 초기 화면
    st.title("📈 버핏 봇 — 장기 가치투자 스크리너")
    st.markdown("""
    **왼쪽 사이드바에서 마켓을 고르고 '분석 시작'을 누르세요.**

    | 기능 | 설명 |
    |---|---|
    | 🏆 점수 랭킹 | 버핏 체크리스트 100점 채점 (수익성·해자·재무·밸류에이션) |
    | 🏭 섹터 분석 | 어느 산업이 괜찮은지 |
    | 💰 적정 매수가 | 시나리오 DCF·역DCF·안전마진·기대수익률 |
    | 📡 기술변곡점 | 최신 뉴스에서 HBM·AI·수주 등 모멘텀 신호 감지 |
    | 💼 포트폴리오 | 지금 살 종목 / 목표가 대기 / 회피 버킷 분류 |
    | 📌 워치리스트 | 목표가 저장 → 도달 시 알림 |

    > *"훌륭한 기업을 적당한 가격에 사라." — 워런 버핏*
    """)
    st.info("⚠️ 교육·연구용 참고 도구입니다. 실제 매수 전 사업보고서와 해자를 직접 검증하세요.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────
# 종목 목록 결정
# ─────────────────────────────────────────────────────────────────────────
from universe import get_universe, KR_UNIVERSE, US_UNIVERSE
from datafetch import fetch_many
from buffett import evaluate
import advisor
import watchlist as wl

def ticker_sector_map() -> dict[str, str]:
    m = {}
    for uni in (KR_UNIVERSE, US_UNIVERSE):
        for sector, items in uni.items():
            for tk, _ in items:
                m[tk] = sector
    return m

if market_code == "custom":
    if not custom_tickers:
        st.error("티커를 입력해주세요.")
        st.stop()
    tickers = custom_tickers
else:
    tickers = [tk for tk, _, _ in get_universe(market_code)]

sec_map = ticker_sector_map()

# ─────────────────────────────────────────────────────────────────────────
# 데이터 수집 & 평가
# ─────────────────────────────────────────────────────────────────────────
st.title("📊 분석 결과")
progress_bar = st.progress(0, text="데이터 수집 준비 중...")

# 개별 수집 with progress
from datafetch import fetch

funds = []
for i, tk in enumerate(tickers):
    progress_bar.progress((i + 1) / len(tickers), text=f"수집 중: {tk} ({i+1}/{len(tickers)})")
    f = fetch(tk, use_cache=use_cache)
    if f:
        funds.append(f)

progress_bar.progress(1.0, text="평가 중...")

# 기술신호 포함 여부를 metrics.compute에 전달하기 위해 패치
import metrics as _M_mod
_orig_compute = _M_mod.compute

def _patched_compute(f, fetch_tech_=fetch_tech):
    return _orig_compute(f, fetch_tech=fetch_tech_)

_M_mod.compute = lambda f: _patched_compute(f)

verdicts = sorted((evaluate(f) for f in funds), key=lambda v: v.total, reverse=True)
_M_mod.compute = _orig_compute   # 복원

progress_bar.empty()

if not verdicts:
    st.error("수집된 종목이 없습니다. 네트워크 연결을 확인하세요.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────
# 탭 레이아웃
# ─────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🏆 랭킹", "🏭 섹터", "💼 포트폴리오", "📋 상세 조언"])

# ── Tab1: 랭킹 ────────────────────────────────────────────────────────────
with tab1:
    st.subheader("버핏 점수 랭킹  (총점 100 = 품질 75 + 가격 25 + 기술신호 ±3)")

    rows = []
    for i, v in enumerate(verdicts, 1):
        f, m = v.f, v.metrics
        tech = getattr(m, "tech", None)
        rows.append({
            "#": i,
            "종목": f.name[:18],
            "티커": f.ticker,
            "섹터": sec_map.get(f.ticker, f.sector)[:12],
            "총점": round(v.total, 1),
            "품질": round(v.quality, 1),
            "가격": round(v.value, 1),
            "등급": v.rating,
            "PER": f"{f.per:.0f}" if f.per and f.per > 0 else "-",
            "ROIC": f"{m.roic*100:.0f}%" if m.roic is not None else "-",
            "F점수": m.fscore if m.fscore is not None else "-",
            "기술신호": tech.label if (tech and tech.news_count > 0) else "-",
        })

    df = pd.DataFrame(rows)

    def color_rating(val):
        if "강력" in str(val): return "background-color: #1a6e1a; color: white"
        if "매수 검토" in str(val): return "background-color: #2d6e2d; color: white"
        if "대기" in str(val): return "background-color: #6e5c1a; color: white"
        if "관망" in str(val): return "background-color: #3a3a3a"
        if "회피" in str(val): return "background-color: #6e1a1a; color: white"
        return ""

    def color_tech(val):
        if "강한 긍정" in str(val): return "color: #00ff88; font-weight: bold"
        if "긍정" in str(val): return "color: #88ff88"
        if "강한 부정" in str(val): return "color: #ff4444; font-weight: bold"
        if "부정" in str(val): return "color: #ff8888"
        return ""

    styled = df.style.applymap(color_rating, subset=["등급"]) \
                     .applymap(color_tech, subset=["기술신호"]) \
                     .background_gradient(subset=["총점"], cmap="RdYlGn", vmin=30, vmax=80)

    st.dataframe(styled, use_container_width=True, hide_index=True, height=600)

# ── Tab2: 섹터 ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("섹터별 평균 품질 점수  —  '어느 산업이 괜찮은지'")

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
        avg_q = sum(x.quality for x in vs) / len(vs)
        avg_t = sum(x.total for x in vs) / len(vs)
        best = max(vs, key=lambda x: x.total)
        sec_rows.append({
            "섹터": sec,
            "평균 품질": round(avg_q, 1),
            "평균 총점": round(avg_t, 1),
            "종목수": len(vs),
            "대표 종목": best.f.name[:16],
            "투자 관점": SECTOR_PHILOSOPHY.get(sec, ""),
        })
    sec_rows.sort(key=lambda x: -x["평균 품질"])

    sec_df = pd.DataFrame(sec_rows)
    st.dataframe(
        sec_df.style.background_gradient(subset=["평균 품질"], cmap="RdYlGn", vmin=30, vmax=60),
        use_container_width=True, hide_index=True
    )

    # 막대그래프
    st.bar_chart(
        sec_df.set_index("섹터")[["평균 품질", "평균 총점"]],
        use_container_width=True,
    )

# ── Tab3: 포트폴리오 ─────────────────────────────────────────────────────
with tab3:
    st.subheader("포트폴리오 조언  —  '지금 무엇을, 얼마에, 왜'")

    lines = advisor.portfolio(verdicts, sec_map)
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("="):
            continue
        if ln.startswith("💼") or ln.startswith("🌡"):
            st.markdown(f"### {ln}")
        elif ln.startswith("✅"):
            st.markdown(f"#### {ln}")
        elif ln.startswith("⏳"):
            st.markdown(f"#### {ln}")
        elif ln.startswith("🚫"):
            st.markdown(f"#### {ln}")
        elif ln.startswith("🧩"):
            st.markdown(f"#### {ln}")
        elif ln.startswith("🧭"):
            st.info(ln)
        elif ln.startswith("•"):
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{ln}")
        elif ln.startswith("→"):
            st.success(ln) if ("우호적" in ln or "적극" in ln) else st.warning(ln)
        else:
            st.text(ln)

    # 워치리스트 저장 버튼 (탭 내부에서도)
    if watch_btn or st.button("💾 대기 종목 목표가 저장 (워치리스트)", key="watch_tab3"):
        n = wl.add_from_verdicts(verdicts)
        st.success(f"✅ '대기' 종목 {n}개를 워치리스트에 저장했습니다. "
                   f"나중에 '목표가 도달 점검'으로 알림을 받으세요.")

# ── Tab4: 상세 조언 ──────────────────────────────────────────────────────
with tab4:
    st.subheader(f"종목별 상세 조언  —  상위 {min(top_n, len(verdicts))}개")

    show = verdicts[:top_n]
    for v in show:
        f, m, val = v.f, v.metrics, v.valuation
        cur = f.currency
        tech = getattr(m, "tech", None)

        # 등급별 색상
        color_map = {
            "★ 강력 매수 후보": "🟢",
            "매수 검토": "🔵",
            "우량주 · 가격 비쌈(대기)": "🟡",
            "관망": "⚪",
            "회피": "🔴",
        }
        icon = color_map.get(v.rating, "⚪")

        with st.expander(f"{icon} {f.name} ({f.ticker})  |  {v.rating}  |  {v.total:.0f}점", expanded=(v == show[0])):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총점", f"{v.total:.0f} / 100")
                st.metric("등급", v.rating)
            with col2:
                st.metric("ROE", f"{f.roe*100:.1f}%" if f.roe else "-")
                st.metric("ROIC", f"{m.roic*100:.1f}%" if m.roic else "-")
            with col3:
                fair = val.get("fair")
                c = "₩" if cur == "KRW" else "$"
                dec = 0 if cur == "KRW" else 2
                fmt = lambda x: f"{c}{x:,.{dec}f}" if x else "-"
                st.metric("현재가", fmt(f.price))
                st.metric("적정가치", fmt(fair))
            with col4:
                mos = val.get("mos_pct")
                er = val.get("exp_return")
                st.metric("안전마진", f"{mos*100:+.0f}%" if mos is not None else "-",
                          delta_color="normal" if (mos or 0) > 0 else "inverse")
                st.metric("기대 연수익률", f"{er*100:.0f}%" if er is not None else "-")

            st.divider()

            # 시나리오 DCF
            sc = val.get("scenarios", {})
            if sc:
                dcf_col1, dcf_col2, dcf_col3 = st.columns(3)
                with dcf_col1:
                    st.metric("약세 시나리오", fmt(sc.get("bear")))
                with dcf_col2:
                    st.metric("기본 시나리오", fmt(sc.get("base")))
                with dcf_col3:
                    st.metric("강세 시나리오", fmt(sc.get("bull")))
                st.caption(f"매수 권장가: **{fmt(val.get('buy_below'))}** 이하 (안전마진 25% 적용)")

            # 역DCF
            ig = val.get("implied_growth")
            real = f.earnings_cagr
            if ig is not None:
                if real is not None:
                    if ig <= real:
                        st.success(f"📈 역DCF: 시장은 연 {ig*100:.0f}% 성장 가정 — 실제 성장({real*100:.0f}%)보다 낮아 **저평가 신호**")
                    else:
                        st.warning(f"📈 역DCF: 시장은 연 {ig*100:.0f}% 성장 기대 — 실적({real*100:.0f}%)이 못 따라가면 하락 위험")
                else:
                    st.info(f"📈 역DCF: 시장이 가정한 성장률 연 {ig*100:.0f}%")

            # 기술변곡점 신호
            if tech and tech.news_count > 0:
                st.divider()
                tech_col1, tech_col2 = st.columns([1, 2])
                with tech_col1:
                    label_color = "🟢" if "긍정" in tech.label else ("🔴" if "부정" in tech.label else "⚪")
                    st.markdown(f"**📡 기술·사업 신호**  \n{label_color} {tech.label}")
                    st.caption(f"뉴스 {tech.news_count}건 스캔")
                with tech_col2:
                    if tech.positive_hits:
                        st.markdown("**✅ 긍정 키워드:** " + " · ".join(tech.positive_hits))
                    if tech.negative_hits:
                        st.markdown("**⚠️ 부정 키워드:** " + " · ".join(tech.negative_hits))

            # 레드플래그
            if v.flags:
                st.error("⚑ 위험 플래그: " + "  /  ".join(v.flags))

            # F-Score
            if m.fscore is not None:
                st.caption(f"F-Score {m.fscore}/9:  " + "  |  ".join(
                    d for d in m.fscore_detail if d.startswith("✓")
                ) or "통과 항목 없음")

            # 한 줄 조언
            from advisor import _one_liner
            st.info(f"👉 {_one_liner(v)}")

# ─────────────────────────────────────────────────────────────────────────
# 하단 면책
# ─────────────────────────────────────────────────────────────────────────
st.divider()
st.caption("⚠️ 교육·연구용 참고 도구입니다. 자동매매가 아니며 실제 매수 전 사업보고서·해자의 지속성·경영진의 자본배분을 직접 검증하세요. "
           "\"리스크는 자신이 무엇을 하는지 모르는 데서 온다.\" — 워런 버핏")
