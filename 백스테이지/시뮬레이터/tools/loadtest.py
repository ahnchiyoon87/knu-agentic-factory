"""39명 동시 접속 부하 테스트 — 완료기준 ④.

각 가상 수강생이 자기 네임스페이스의 읽기 API 를 폴링한다.
교안 5절이 요구하는 것은 "강의장에서 39명이 동시에 붙었을 때 견디는가"이다.

    python tools/loadtest.py                          기본 39명 · 2초 폴링 · 120초
    python tools/loadtest.py --users 39 --interval 1 --duration 300
    python tools/loadtest.py --base-url http://192.168.0.10:8000   강의장 실제 주소

판정 기준(리서치): 지연·에러가 없으면 유지, 병목이면 폴링 주기 3~5초 또는
데이터 생성 주기 5초로 완화한다.

주의 — 무료 티어에서 통과했다고 39명 동시 조건이 검증된 것이 아니다.
      D-14 부하 검증은 Pro 전환 후 강의장 네트워크에서 다시 돌려야 한다.
"""

from __future__ import annotations

# ── 한글 윈도우(cp949)에서 출력이 깨져 죽는 것을 막는다 ──────────────────
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────────────────

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


class Result:
    def __init__(self) -> None:
        self.latencies: list[float] = []
        self.errors: list[str] = []
        self.status: dict[int, int] = {}
        self.stale: list[float] = []      # 서버시각 - 응답의 server_time (적재 지연 아님)


async def student(client: httpx.AsyncClient, base: str, tenant: str,
                  interval: float, until: float, res: Result) -> None:
    while time.monotonic() < until:
        t0 = time.perf_counter()
        try:
            r = await client.get(f"{base}/api/v1/{tenant}/state")
            dt = (time.perf_counter() - t0) * 1000
            res.status[r.status_code] = res.status.get(r.status_code, 0) + 1
            if r.status_code == 200:
                res.latencies.append(dt)
                body = r.json()
                st = datetime.fromisoformat(body["server_time"])
                res.stale.append(abs((datetime.now(UTC) - st).total_seconds()))
            else:
                res.errors.append(f"HTTP {r.status_code}")
        except Exception as exc:                       # noqa: BLE001
            res.errors.append(type(exc).__name__ + ": " + str(exc)[:80])
        sleep = interval - (time.perf_counter() - t0)
        await asyncio.sleep(max(0.0, sleep))


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = min(len(s) - 1, int(round((p / 100) * (len(s) - 1))))
    return s[k]


async def main() -> int:
    ap = argparse.ArgumentParser(description="39명 동시 접속 부하 테스트")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--users", type=int, default=39)
    ap.add_argument("--interval", type=float, default=2.0, help="폴링 주기(초)")
    ap.add_argument("--duration", type=float, default=120.0, help="지속(초)")
    ap.add_argument("--out", default=None, help="결과 JSON 파일")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")

    async with httpx.AsyncClient(timeout=15.0) as c:
        try:
            health = (await c.get(f"{base}/api/v1/health")).json()
            tenants = (await c.get(f"{base}/api/v1/tenants")).json()["tenants"]
        except Exception as exc:                       # noqa: BLE001
            print(f"서버에 붙지 못했습니다: {exc}")
            print(f"  {base} 에서 시뮬레이터가 돌고 있는지 확인하세요.")
            return 2

        ids = [t["tenant_id"] for t in tenants]
        if not ids:
            print("네임스페이스가 없습니다.")
            return 2
        if len(ids) < args.users:
            print(f"경고 — 네임스페이스 {len(ids)}개 < 가상 수강생 {args.users}명. "
                  f"일부가 같은 네임스페이스를 공유합니다.")
        assign = [ids[i % len(ids)] for i in range(args.users)]

        print("=" * 70)
        print(f"부하 테스트  대상 {base}")
        print(f"  가상 수강생 {args.users}명 · 폴링 {args.interval}초 · {args.duration:.0f}초 동안")
        print(f"  서버 tick {health['tick_seconds']}s / flush {health['flush_seconds']}s "
              f"/ 네임스페이스 {health['tenants']}개")
        print("=" * 70)

        before = health["stats"]
        res = Result()
        until = time.monotonic() + args.duration
        t_start = time.time()

        await asyncio.gather(*[
            student(c, base, assign[i], args.interval, until, res)
            for i in range(args.users)
        ])

        elapsed = time.time() - t_start
        after = (await c.get(f"{base}/api/v1/health")).json()["stats"]

    total = len(res.latencies) + len(res.errors)
    err_rate = (len(res.errors) / total * 100) if total else 0.0
    lat = res.latencies

    report = {
        "실행시각": datetime.now(UTC).isoformat(),
        "대상": base,
        "조건": {
            "가상수강생": args.users,
            "폴링주기_초": args.interval,
            "지속_초": round(elapsed, 1),
        },
        "요청": {
            "총건수": total,
            "성공": len(lat),
            "실패": len(res.errors),
            "에러율_퍼센트": round(err_rate, 3),
            "초당요청": round(total / elapsed, 1) if elapsed else 0,
            "상태코드": res.status,
        },
        "응답지연_ms": {
            "평균": round(statistics.fmean(lat), 1) if lat else None,
            "p50": round(pct(lat, 50), 1),
            "p95": round(pct(lat, 95), 1),
            "p99": round(pct(lat, 99), 1),
            "최대": round(max(lat), 1) if lat else None,
        },
        "서버": {
            "tick_증가": after["ticks"] - before["ticks"],
            "예상_tick": int(elapsed),
            "적재행_증가": after["rows_written"] - before["rows_written"],
            "tick_지연_증가": after["tick_overruns"] - before["tick_overruns"],
            "DB오류_증가": after["db_errors"] - before["db_errors"],
            "마지막_적재_ms": after["last_flush_ms"],
            "마지막_tick_ms": after["last_tick_ms"],
            "마지막_오류": after["last_error"],
        },
        "에러샘플": res.errors[:10],
    }

    print(f"\n요청     {total:,}건 ({report['요청']['초당요청']}/s) · "
          f"실패 {len(res.errors)}건 ({err_rate:.2f}%)")
    print(f"응답지연 p50 {report['응답지연_ms']['p50']}ms · "
          f"p95 {report['응답지연_ms']['p95']}ms · "
          f"p99 {report['응답지연_ms']['p99']}ms · "
          f"최대 {report['응답지연_ms']['최대']}ms")
    print(f"서버     tick {report['서버']['tick_증가']}/{report['서버']['예상_tick']} 예상 · "
          f"적재 {report['서버']['적재행_증가']:,}행 · "
          f"tick지연 +{report['서버']['tick_지연_증가']} · "
          f"DB오류 +{report['서버']['DB오류_증가']}")

    # ---- 판정 -------------------------------------------------------------
    print("\n" + "-" * 70)
    checks = [
        ("에러율 1% 미만", err_rate < 1.0, f"{err_rate:.2f}%"),
        ("p95 응답지연 500ms 이하", pct(lat, 95) <= 500, f"{pct(lat,95):.0f}ms"),
        ("p99 응답지연 1000ms 이하", pct(lat, 99) <= 1000, f"{pct(lat,99):.0f}ms"),
        ("1초 주기 유지(tick 누락 5% 이내)",
         report["서버"]["tick_증가"] >= int(elapsed) * 0.95,
         f"{report['서버']['tick_증가']}/{int(elapsed)}"),
        ("tick 지연 없음", report["서버"]["tick_지연_증가"] == 0,
         f"+{report['서버']['tick_지연_증가']}"),
        ("DB 오류 없음", report["서버"]["DB오류_증가"] == 0,
         f"+{report['서버']['DB오류_증가']}"),
    ]
    ok = True
    for name, passed, detail in checks:
        print(f"  [{'통과' if passed else '실패'}] {name} — {detail}")
        ok = ok and passed
    report["판정"] = {name: passed for name, passed, _ in checks}
    report["종합"] = "통과" if ok else "실패"

    print("-" * 70)
    if ok:
        print("종합: 통과 — 현재 폴링 주기를 유지한다.")
    else:
        print("종합: 실패 — 리서치 판단기준대로 완화한다.")
        print("  1) 클라이언트 폴링 주기를 3~5초로 (2D 뷰·학생 가이드 동시 수정)")
        print("  2) 그래도 안 되면 SIM_FLUSH_SECONDS 를 5초로")
        print("  3) SIM_TICK_SECONDS 는 교안 명시 사양이므로 마지막에 건드린다")

    out = Path(args.out) if args.out else ROOT / f"loadtest_result_{int(time.time())}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
