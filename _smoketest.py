"""앱 전체 경로를 헤드리스로 실행해 런타임 에러를 잡는 스모크 테스트."""
from streamlit.testing.v1 import AppTest


def run(label, mutate=None):
    at = AppTest.from_file("app.py", default_timeout=60)
    if mutate:
        mutate(at)
    at.run()
    if at.exception:
        print(f"❌ [{label}] 예외 {len(at.exception)}건")
        for e in at.exception:
            print(f"    {e.type}: {e.message}")
            if e.stack_trace:
                print("    " + "\n    ".join(e.stack_trace[-6:]))
        return False
    print(f"✅ [{label}] 에러 없음 "
          f"(radio={len(at.radio)}, selectbox={len(at.selectbox)}, "
          f"dataframe={len(at.dataframe)}, tabs={len(at.tabs)})")
    return True


ok = True
# 1) 기본 진입 (국장 자동)
ok &= run("기본 진입(국장)")

# 2) 미장으로 전환
def to_us(at):
    at.run()
    for r in at.radio:
        if "미장" in str(r.options):
            r.set_value("🇺🇸 미장 (US)")
ok &= run("미장 전환", to_us)

# 3) 직접 종목 검색 모드
def to_search(at):
    at.run()
    for r in at.radio:
        if any("검색" in str(o) for o in r.options):
            r.set_value("🔎 직접 종목 검색")
ok &= run("직접 검색 모드", to_search)

# 4) 랭킹 표에서 종목 상세 선택
def pick_stock(at):
    at.run()
    for sb in at.selectbox:
        if "상세 조언" in str(sb.label):
            if len(sb.options) > 1:
                sb.set_value(sb.options[1])
ok &= run("종목 상세 선택", pick_stock)

print("\n" + ("🎉 전부 통과" if ok else "⚠️ 위 에러 수정 필요"))
