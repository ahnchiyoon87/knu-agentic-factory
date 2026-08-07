"""8팀 동시 제어 테스트 — 교안 강사 노트가 요구하는 최종 점검.

    "제어 명령이 서로 부딪히지 않게 — 팀별 공간이 제대로 분리돼 있는지 최종 점검하고,
     리허설 때 여러 팀이 동시에 제어하는 시나리오를 반드시 테스트하세요."

Day 4 발표 때는 8팀이 동시에 자기 공장을 제어한다. 한 팀의 명령이 다른 팀 공장에
새거나, 동시 요청에 서버가 밀리면 그 자리에서 수업이 무너진다. 여기서 미리 확인한다.

    python tools/팀동시제어_테스트.py
    python tools/팀동시제어_테스트.py --base http://34.64.94.16:8000   # 클라우드 대상

서버가 떠 있어야 한다. 끝나면 상태를 원래대로 되돌린다.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
TARGET_RPM = 1200.0
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'통과' if ok else '실패'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def _env(base_override: str | None) -> tuple[str, str]:
    p = ROOT / ".env"
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    base = (base_override or os.environ.get("BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("INSTRUCTOR_TOKEN", "")
    if not token:
        sys.exit("INSTRUCTOR_TOKEN 을 못 찾았습니다 (.env 확인)")
    return base, token


def main() -> int:
    ap = argparse.ArgumentParser(description="8팀 동시 제어 테스트")
    ap.add_argument("--base", help="서버 주소 (기본: .env 또는 127.0.0.1:8000)")
    ap.add_argument("--equipment", default="EQ-02", help="각 팀이 제어할 설비")
    args = ap.parse_args()

    base, token = _env(args.base)
    ih = {"X-Instructor-Token": token}
    print("=" * 74)
    print(f"8팀 동시 제어 테스트   대상 {base}")
    print("=" * 74)

    c = httpx.Client(timeout=60.0)

    # 팀 목록과 키
    rows = c.get(f"{base}/api/instructor/tenants", headers=ih).json()["tenants"]
    teams = [t for t in rows if t["tenant_type"] == "team"]
    check("팀 네임스페이스가 8개 떠 있다", len(teams) == 8, f"{len(teams)}개")
    if not teams:
        return 1

    # 제어 개방 (테스트 후 되돌린다)
    was_open = c.get(f"{base}/api/instructor/status", headers=ih).json().get("control_api_open")
    c.post(f"{base}/api/instructor/control-lock", headers=ih,
           params={"unlocked": "true", "tenant_id": "*"})

    try:
        # 제어 전 상태 기록
        before = {}
        for t in teams:
            st = c.get(f"{base}/api/v1/{t['tenant_id']}/equipment/{args.equipment}").json()
            eq = st.get("equipment", st)
            before[t["tenant_id"]] = eq.get("rpm")

        # ---- 8팀 동시 제어 -------------------------------------------------
        print(f"\n1. 8팀이 같은 순간에 자기 {args.equipment} 를 {TARGET_RPM:g} rpm 으로")

        def control(t: dict) -> tuple[str, int, float]:
            t0 = time.time()
            r = httpx.post(
                f"{base}/api/v1/{t['tenant_id']}/control/set_equipment_speed/{args.equipment}",
                headers={"X-Access-Key": t["access_key"]},
                json={"rpm": TARGET_RPM, "issued_by": "concurrency-test"},
                timeout=60.0,
            )
            return t["tenant_id"], r.status_code, time.time() - t0

        t_start = time.time()
        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(control, teams))
        wall = time.time() - t_start

        okc = [r for r in results if r[1] < 300]
        slowest = max(r[2] for r in results)
        check("8팀 명령이 모두 성공했다", len(okc) == len(teams),
              f"{len(okc)}/{len(teams)} · 전체 {wall:.2f}초 · 가장 느린 응답 {slowest:.2f}초")
        check("동시 요청에도 응답이 느려지지 않는다 (10초 이내)", slowest < 10.0,
              f"가장 느린 {slowest:.2f}초")

        # ---- 반영 확인 ------------------------------------------------------
        print("\n2. 각 팀 공장에 실제로 반영됐는가")
        time.sleep(3)
        applied, wrong = 0, []
        for t in teams:
            st = c.get(f"{base}/api/v1/{t['tenant_id']}/equipment/{args.equipment}").json()
            rpm = (st.get("equipment", st)).get("rpm", 0)
            if abs(rpm - TARGET_RPM) <= 60:
                applied += 1
            else:
                wrong.append(f"{t['tenant_id']}={rpm:.0f}")
        check("8팀 전부 자기 공장에 반영됐다", applied == len(teams),
              f"{applied}/{len(teams)}" + (" · 어긋남: " + ", ".join(wrong) if wrong else ""))

        # ---- 교차 오염 ------------------------------------------------------
        print("\n3. 다른 팀 공장은 안 건드렸는가 (교차 오염)")
        other = "EQ-05" if args.equipment != "EQ-05" else "EQ-06"
        untouched = []
        for t in teams:
            st = c.get(f"{base}/api/v1/{t['tenant_id']}/equipment/{other}").json()
            untouched.append((st.get("equipment", st)).get("rpm", 0))
        check(f"제어하지 않은 {other} 는 어느 팀에서도 안 바뀌었다",
              all(abs(r - TARGET_RPM) > 60 for r in untouched),
              f"{min(untouched):.0f}~{max(untouched):.0f} rpm")

        # ---- 남의 키 차단 ---------------------------------------------------
        print("\n4. 남의 키로는 못 건드리는가")
        a, b = teams[0], teams[1]
        r = httpx.post(f"{base}/api/v1/{a['tenant_id']}/control/set_equipment_speed/{args.equipment}",
                       headers={"X-Access-Key": b["access_key"]},
                       json={"rpm": 900.0, "issued_by": "concurrency-test"}, timeout=30.0)
        check("B팀 키로 A팀 공장을 제어하면 거부된다", r.status_code in (401, 403),
              f"HTTP {r.status_code}")

        # ---- 감사 로그 ------------------------------------------------------
        print("\n5. 팀별 감사 로그가 섞이지 않는가")
        logged, detail = [], []
        for t in teams[:3]:
            cmds = c.get(f"{base}/api/v1/{t['tenant_id']}/control/commands",
                         headers={"X-Access-Key": t["access_key"]},
                         params={"limit": 20}).json()
            items = cmds.get("commands", cmds if isinstance(cmds, list) else [])
            mine = [x for x in items if x.get("tenant_id", t["tenant_id"]) == t["tenant_id"]]
            logged.append(len(mine) > 0 and len(mine) == len(items))
            detail.append(f"{t['tenant_id']}:{len(items)}건")
        check("조회한 팀의 로그에 남의 명령이 섞여 있지 않다", all(logged),
              " · ".join(detail))

    finally:
        # 원상복구
        for t in teams:
            try:
                httpx.post(f"{base}/api/v1/{t['tenant_id']}/control/set-speed",
                           headers={"X-Access-Key": t["access_key"]},
                           json={"equipment_id": args.equipment, "rpm": before.get(t["tenant_id"], 1800.0)},
                           timeout=30.0)
            except Exception:
                pass
        if not was_open:
            c.post(f"{base}/api/instructor/control-lock", headers=ih,
                   params={"unlocked": "false", "tenant_id": "*"})
        print("\n(원상복구 완료 — 회전수 되돌림 · 제어 잠금 원위치)")

    print("\n" + "=" * 74)
    if fails:
        print(f"실패 {len(fails)}건: " + ", ".join(fails))
        return 1
    print("전 항목 통과 — 8팀이 동시에 제어해도 서로 부딪히지 않습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
