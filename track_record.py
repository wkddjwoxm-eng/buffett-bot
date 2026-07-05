"""
추천 성과 자기검증(트랙레코드) — 과거 스냅샷의 '강력 매수' 추천이
실제로 어떤 수익률을 냈는지 git 이력으로 계산한다.

git에 하루 2회 커밋되는 results_{kr,us}.json 스냅샷에 당시 가격이
들어있으므로, 외부 API 없이 순수 이력만으로 성과를 측정할 수 있다.

GitHub Actions(daily_prefetch)가 수집 후 실행 → cache/track_record.json 저장
→ app.py가 읽어 '추천 성과' 배너로 표시.
"""
import json
import subprocess
import time
from pathlib import Path

REPO_DIR = Path(__file__).parent
CACHE_DIR = REPO_DIR / "cache"

WINDOWS_DAYS = (7, 14, 30)
TOLERANCE_SEC = 2.5 * 86400   # 목표 시점 ±2.5일 내 스냅샷만 인정


def _git(args: list[str]) -> str:
    out = subprocess.run(["git"] + args, capture_output=True, text=True,
                         cwd=str(REPO_DIR), timeout=60)
    return out.stdout


def _snapshot_days_ago(market: str, days: int):
    """days일 전에 가장 가까운 커밋의 results 스냅샷. (payload, 커밋시각) 또는 (None, None)."""
    target = time.time() - days * 86400
    best = None
    for line in _git(["log", "--format=%H %ct", "--",
                      f"cache/results_{market}.json"]).splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        h, ts = parts[0], int(parts[1])
        if best is None or abs(ts - target) < abs(best[1] - target):
            best = (h, ts)
    if not best or abs(best[1] - target) > TOLERANCE_SEC:
        return None, None
    try:
        payload = json.loads(_git(["show", f"{best[0]}:cache/results_{market}.json"]))
        return payload, best[1]
    except Exception:
        return None, None


def _fresh_prices(payload: dict) -> dict:
    """티커 → 가격 (이월된 낡은 레코드는 제외 — 수익률 왜곡 방지)."""
    px = {}
    for v in payload.get("verdicts", []):
        f = v.get("f", {})
        tk, p = f.get("ticker"), f.get("price")
        if tk and p and p > 0 and not v.get("_stale_epoch"):
            px[tk] = float(p)
    return px


def build_track_record() -> dict:
    result = {"generated_epoch": time.time(), "markets": {}}
    for mk in ("kr", "us"):
        cur_path = CACHE_DIR / f"results_{mk}.json"
        if not cur_path.exists():
            continue
        try:
            cur = json.loads(cur_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        cur_px = _fresh_prices(cur)
        windows = {}
        for days in WINDOWS_DAYS:
            snap, ts = _snapshot_days_ago(mk, days)
            if not snap:
                continue
            snap_px = _fresh_prices(snap)
            # 당시 '강력 매수' 추천 종목들
            picks = []
            for v in snap.get("verdicts", []):
                if "강력" not in (v.get("rating") or ""):
                    continue
                f = v.get("f", {})
                tk = f.get("ticker")
                p0 = snap_px.get(tk)
                p1 = cur_px.get(tk)
                if p0 and p1:
                    picks.append({"ticker": tk, "name": f.get("name", tk),
                                  "ret": (p1 / p0 - 1) * 100})
            if len(picks) < 3:      # 표본 너무 적으면 통계 무의미
                continue
            # 벤치마크: 당시 스냅샷 전체 종목의 같은 기간 평균 수익률
            mkt_rets = [(cur_px[tk] / p0 - 1) * 100
                        for tk, p0 in snap_px.items() if tk in cur_px]
            picks.sort(key=lambda x: -x["ret"])
            windows[str(days)] = {
                "n": len(picks),
                "avg": round(sum(p["ret"] for p in picks) / len(picks), 2),
                "mkt_avg": round(sum(mkt_rets) / len(mkt_rets), 2) if mkt_rets else None,
                "win_rate": round(sum(1 for p in picks if p["ret"] > 0) / len(picks) * 100, 0),
                "best": {"name": picks[0]["name"][:18], "ret": round(picks[0]["ret"], 1)},
                "worst": {"name": picks[-1]["name"][:18], "ret": round(picks[-1]["ret"], 1)},
                "asof_epoch": ts,
            }
        if windows:
            result["markets"][mk] = windows

    CACHE_DIR.mkdir(exist_ok=True)
    (CACHE_DIR / "track_record.json").write_text(
        json.dumps(result, ensure_ascii=False), encoding="utf-8")
    for mk, ws in result["markets"].items():
        for d, w in ws.items():
            print(f"  [track] {mk} {d}일: 강력매수 {w['n']}종목 평균 {w['avg']:+.1f}% "
                  f"(시장 {w['mkt_avg']:+.1f}%) 승률 {w['win_rate']:.0f}%")
    return result


if __name__ == "__main__":
    build_track_record()
