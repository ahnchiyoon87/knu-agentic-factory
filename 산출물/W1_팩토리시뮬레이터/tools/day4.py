"""Day 4 준비 — 강사가 누르는 것을 한 번으로.

교안에 없는 조작(제어 개방·배속·주입)은 교안이 알려주지 않는다.
그래서 사람 기억에 맡기지 않고 여기 한 곳에 모았다.

    python tools/day4.py                 준비 (제어 개방 + 배속 + 팀 키 출력)
    python tools/day4.py --inject T3     그 팀 공장에 시연용 드리프트 주입
    python tools/day4.py --status        지금 상태와 경고 확인
    python tools/day4.py --end           Day 1~3 상태로 되돌림

접속 정보는 .env 에서 읽는다. 서버가 떠 있어야 한다.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def _env() -> tuple[str, str]:
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    base = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("INSTRUCTOR_TOKEN", "")
    if not token:
        sys.exit("INSTRUCTOR_TOKEN 을 못 찾았습니다 (.env 확인)")
    return base, token


def call(base: str, token: str, method: str, path: str, **kw) -> dict:
    r = httpx.request(method, f"{base}/api/instructor{path}",
                      headers={"X-Instructor-Token": token}, timeout=60, **kw)
    r.raise_for_status()
    return r.json()


def show_status(base: str, token: str) -> None:
    st = call(base, token, "GET", "/status")
    c = st["clock"]
    print(f"  배속 x{c['time_scale']:g} · 실제 tick {c['real_tick_seconds']}초 "
          f"· 공장 시각 {c['virtual_time'][11:19]}")
    print(f"  네임스페이스 {st['tenants']}개 · 진행 중 주입 {len(st['active_injections'])}건")
    for w in st["warnings"]:
        print(f"  ⚠ {w['message']}")
        print(f"     → {w['fix']}")
    if not st["warnings"]:
        print("  경고 없음")


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 4 준비")
    ap.add_argument("--inject", metavar="팀", help="그 팀 공장에 온도 드리프트 주입 (예: T3)")
    ap.add_argument("--equipment", default="EQ-03")
    ap.add_argument("--scale", type=float, default=120.0, help="시연 배속 (기본 120)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--end", action="store_true", help="Day 1~3 상태로 되돌림")
    args = ap.parse_args()

    base, token = _env()

    if args.status:
        print("현재 상태")
        show_status(base, token)
        return 0

    if args.end:
        call(base, token, "DELETE", "/inject")
        call(base, token, "POST", "/control-lock", params={"unlocked": "false", "tenant_id": "*"})
        call(base, token, "POST", "/time-scale", params={"scale": 60})
        print("Day 1~3 상태로 되돌렸습니다 (제어 잠금 · 주입 중단 · 배속 60)")
        return 0

    if args.inject:
        out = httpx.post(f"{base}/api/instructor/inject",
                         json={"tenant_id": args.inject, "equipment_id": args.equipment,
                               "kind": "temp_drift"},
                         headers={"X-Instructor-Token": token}, timeout=30).json()
        print(f"주입  {args.inject} · {out['equipment_id']} · {out['params']}")
        print("  감지까지 배속 x120 기준 약 100초, x60 기준 약 190초 걸립니다.")
        print("  팀이 발표석에 서기 **전에** 주입해 두십시오.")
        return 0

    # ---- 기본: Day 4 준비 ----------------------------------------------------
    print("Day 4 준비")
    call(base, token, "POST", "/time-scale", params={"scale": args.scale})
    call(base, token, "POST", "/control-lock", params={"unlocked": "true", "tenant_id": "*"})
    print(f"  제어 API 개방 · 배속 x{args.scale:g}")

    teams = [t for t in call(base, token, "GET", "/tenants")["tenants"]
             if t["tenant_type"] == "team"]
    if not teams:
        print("\n  ⚠ 팀 네임스페이스가 안 떠 있습니다. TENANT_MODE 를 both 로 두고 재시작하세요.")
        return 2

    print(f"\n팀에 나눠 줄 값 ({len(teams)}팀)")
    print(f"  {'팀':<6}{'이름':<10}{'access_key'}")
    for t in teams:
        print(f"  {t['tenant_id']:<6}{t['display_name']:<10}{t['access_key']}")
    print(f"\n  base_url : {base}")
    print("  학생 config.json 의 tenant · access_key · base_url 세 줄만 채우면 됩니다.")

    print("\n확인")
    show_status(base, token)
    print("\n발표 때 — python tools/day4.py --inject T3   (팀이 서기 전에)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
