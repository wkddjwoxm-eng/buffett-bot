"""
Streamlit 앱 절전 방지 — 실제 페이지를 headless 브라우저로 열어 활동을 발생시킨다.
잠들어 있으면 'Yes, get this app back up!' 버튼을 눌러 깨운다.

GitHub Actions(keep_alive.yml)가 몇 시간마다 실행한다.
단순 HTTP 핑은 Streamlit이 활동으로 안 칠 때가 있어 websocket 세션이 붙는
브라우저 로드 방식을 쓴다.
"""
import sys
import time

APP_URL = "https://buffett-bot.streamlit.app/"

# 잠든 앱의 깨우기 버튼에 흔히 들어가는 문구들
WAKE_TEXTS = [
    "get this app back up",
    "Yes, get this app back up",
    "is back up",
    "app back up",
]


def main() -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36")
        )
        try:
            print(f"[keep-alive] 접속: {APP_URL}")
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=60_000)

            # 페이지 안정화 대기
            page.wait_for_timeout(8_000)

            # 잠들어 있으면 깨우기 버튼 클릭 (여러 문구 시도)
            woke = False
            for txt in WAKE_TEXTS:
                try:
                    btn = page.get_by_text(txt, exact=False)
                    if btn.count() > 0:
                        btn.first.click(timeout=5_000)
                        print(f"[keep-alive] 💤 절전 상태 감지 → '{txt}' 버튼 클릭, 깨우는 중…")
                        woke = True
                        break
                except Exception:
                    continue

            if woke:
                # 다시 살아날 때까지 넉넉히 대기
                page.wait_for_timeout(40_000)
                print("[keep-alive] ✅ 깨우기 완료")
            else:
                # 이미 깨어 있으면 잠깐 머물러 세션 활동 발생
                page.wait_for_timeout(5_000)
                print("[keep-alive] ✅ 앱 정상 가동 중 (절전 아님)")

            title = page.title()
            print(f"[keep-alive] 페이지 타이틀: {title!r}")
            return 0
        except Exception as e:  # noqa: BLE001
            print(f"[keep-alive] ⚠️ 오류(무시 가능): {type(e).__name__}: {e}")
            # keep-alive는 실패해도 워크플로우를 빨갛게 만들지 않는다
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
