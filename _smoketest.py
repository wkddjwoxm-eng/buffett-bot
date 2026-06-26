"""
앱 전체 경로 + 핵심 모듈을 헤드리스로 검증하는 스모크 테스트.

로컬:  python3 _smoketest.py
CI:    실패 시 exit code 1 → 배포 게이트 역할
"""
import sys
import compileall
import os

FAILS = []


def check(label, cond, detail=""):
    if cond:
        print(f"✅ {label}")
    else:
        print(f"❌ {label}  {detail}")
        FAILS.append(label)


# ── 1) 전 파이썬 파일 컴파일(문법) 검사 ──────────────────────────────────
here = os.path.dirname(os.path.abspath(__file__))
ok_compile = compileall.compile_dir(here, quiet=1, maxlevels=1)
check("전 모듈 문법 컴파일", ok_compile)

# ── 2) 핵심 모듈 import ──────────────────────────────────────────────────
try:
    import buffett, metrics, valuation, advisor, results_io, datafetch, universe  # noqa
    check("핵심 모듈 import", True)
except Exception as e:  # noqa: BLE001
    check("핵심 모듈 import", False, f"{type(e).__name__}: {e}")

# ── 3) 저장된 결과 무결성 ────────────────────────────────────────────────
try:
    import results_io
    for mk in ("kr", "us"):
        vs, ts = results_io.load_market(mk)
        n = len(vs) if vs else 0
        check(f"{mk} 결과 로드(≥50종목)", n >= 50, f"실제 {n}개")
        if vs:
            v = vs[0]
            sane = (v.total is not None and 0 <= v.total <= 110
                    and isinstance(v.valuation, dict))
            check(f"{mk} 1위 종목 데이터 정합성", sane)
except Exception as e:  # noqa: BLE001
    check("결과 무결성", False, f"{type(e).__name__}: {e}")

# ── 4) 앱 전 경로 렌더(AppTest) — 예외 0건 ────────────────────────────────
try:
    from streamlit.testing.v1 import AppTest

    def render(label, mutate=None):
        at = AppTest.from_file("app.py", default_timeout=90)
        if mutate:
            at.run(); mutate(at)
        at.run()
        if at.exception:
            msgs = "; ".join(f"{e.type}:{e.message}" for e in at.exception)
            check(f"렌더 [{label}]", False, msgs)
        else:
            check(f"렌더 [{label}]", True)

    def to_us(at):
        for r in at.radio:
            if "미장" in str(r.options):
                r.set_value("🇺🇸 미장 (US)")

    def to_search(at):
        # 직접 검색 모드 진입 + 종목 검색·선택 → 즉시 상세분석 렌더
        for r in at.radio:
            if any("검색" in str(o) for o in r.options):
                r.set_value("🔎 직접 종목 검색")
        at.run()
        for ti in at.text_input:
            if "검색" in str(ti.label):
                ti.set_value("삼성")
        at.run()
        for sb in at.selectbox:
            if "종목 선택" in str(sb.label) and sb.options:
                sb.set_value(sb.options[0])

    def pick(at):
        for sb in at.selectbox:
            if "상세 조언" in str(sb.label) and len(sb.options) > 1:
                sb.set_value(sb.options[1])

    def compare(at):
        for ms in at.multiselect:
            if "비교할 종목" in str(ms.label) and len(ms.options) >= 3:
                ms.set_value(list(ms.options[:3]))

    render("기본 진입(국장)")
    render("미장 전환", to_us)
    render("직접 검색 모드", to_search)
    render("종목 상세 선택", pick)
    render("종목 비교(3개)", compare)

    # 회귀: 검색→선택→다른 검색어 변경 시 크래시 방지
    def search_change(at):
        for r in at.radio:
            if any("검색" in str(o) for o in r.options):
                r.set_value("🔎 직접 종목 검색")
        at.run()
        for ti in at.text_input:
            if "검색" in str(ti.label):
                ti.set_value("기아")
        at.run()
        for sb in at.selectbox:
            if "종목 선택" in str(sb.label) and sb.options:
                sb.set_value(sb.options[0])
        at.run()
        for ti in at.text_input:
            if "검색" in str(ti.label):
                ti.set_value("삼성")   # 검색어 변경 시 안정성 확인

    render("검색어 변경(기아→삼성)", search_change)
except Exception as e:  # noqa: BLE001
    check("AppTest 렌더", False, f"{type(e).__name__}: {e}")


print("\n" + ("🎉 전부 통과" if not FAILS else f"⚠️ 실패 {len(FAILS)}건: {FAILS}"))
sys.exit(0 if not FAILS else 1)
