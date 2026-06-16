"""
매일 오전 8시 KST 자동 실행 — 유니버스 전체 종목 캐시 사전 수집.
GitHub Actions에서 호출. 캐시 파일을 repo에 커밋해두면
Streamlit Cloud가 배포 시 즉시 사용해 첫 분석 대기시간을 없앤다.
"""
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from universe import get_universe
from datafetch import fetch, _cache_path

def prefetch_all(market: str = "all", workers: int = 20) -> None:
    tickers = [tk for tk, _, _ in get_universe(market)]
    total = len(tickers)
    print(f"[prefetch] {date.today()} — 총 {total}개 종목 수집 시작 (workers={workers})")

    done = 0
    skipped = 0
    failed = 0

    def _fetch(tk):
        cp = _cache_path(tk)
        if cp.exists():
            return tk, "skip"
        f = fetch(tk, use_cache=True)
        return tk, ("ok" if f else "fail")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch, tk): tk for tk in tickers}
        for fut in as_completed(futures):
            tk = futures[fut]
            try:
                _, status = fut.result()
            except Exception as e:
                status = "fail"
                print(f"  ✗ {tk}: {e}")
            if status == "skip":
                skipped += 1
            elif status == "fail":
                failed += 1
            else:
                done += 1
            if (done + skipped + failed) % 50 == 0:
                print(f"  진행: {done+skipped+failed}/{total} (신규={done}, 스킵={skipped}, 실패={failed})")

    print(f"[prefetch] 완료 — 신규수집={done}, 캐시스킵={skipped}, 실패={failed}")


if __name__ == "__main__":
    prefetch_all()
