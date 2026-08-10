"""네임스페이스 분리 검증 — 견적서 W1 완료기준 ⑤.

교안 p.9 강사 노트:
    "제어 명령이 서로 부딪히지 않게 — 팀별 공간이 제대로 분리돼 있는지 최종 점검하고,
     리허설 때 여러 팀이 동시에 제어하는 시나리오를 반드시 테스트하세요."

여러 네임스페이스가 동시에 서로 다른 제어 명령을 쏘고, 각자 자기 공장만
바뀌었는지 확인한다. 남의 키로 남의 공장을 건드릴 수 없다는 것도 함께 본다.

    python tools/isolation_test.py
    python tools/isolation_test.py --base-url http://192.168.0.10:8000 --tenants 8
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
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'통과' if ok else '실패'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


async def main() -> int:
    ap = argparse.ArgumentParser(description="네임스페이스 분리 검증")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--token", default=None, help="INSTRUCTOR_TOKEN (기본: .env 에서)")
    ap.add_argument("--tenants", type=int, default=8, help="동시 제어할 네임스페이스 수")
    args = ap.parse_args()

    token = args.token
    if not token:
        from server.app.config import get_settings
        token = get_settings().instructor_token

    base = args.base_url.rstrip("/")
    ih = {"X-Instructor-Token": token}

    async with httpx.AsyncClient(timeout=20.0) as c:
        # --- 준비 ---------------------------------------------------------
        r = await c.get(f"{base}/api/instructor/tenants", headers=ih)
        if r.status_code != 200:
            print(f"강사 토큰 인증 실패: {r.status_code} {r.text[:200]}")
            return 2
        all_t = [t for t in r.json()["tenants"] if t["active"]]
        running = (await c.get(f"{base}/api/v1/tenants")).json()["tenants"]
        running_ids = {t["tenant_id"] for t in running}
        pool = [t for t in all_t if t["tenant_id"] in running_ids][: args.tenants]
        if len(pool) < 2:
            print("네임스페이스가 2개 이상 돌고 있어야 합니다.")
            return 2

        print("=" * 70)
        print(f"네임스페이스 분리 검증 — 동시 제어 {len(pool)}개")
        print("  " + ", ".join(t["tenant_id"] for t in pool))
        print("=" * 70)

        print("\n0. 제어 API 개방 (Day 4 조건 재현)")
        r = await c.post(f"{base}/api/instructor/control-lock?unlocked=true&tenant_id=*",
                         headers=ih)
        opened = await c.get(f"{base}/api/v1/{pool[0]['tenant_id']}/state")
        check("전 네임스페이스 개방",
              r.status_code == 200 and opened.json()["control"]["unlocked"] is True,
              f"HTTP {r.status_code} · {pool[0]['tenant_id']} 개방 확인")

        # --- 1. 잠금 상태 확인 --------------------------------------------
        print("\n1. 잠금 동작 — Day 1~3 에는 제어가 막혀야 한다")
        victim = pool[0]
        await c.post(f"{base}/api/instructor/control-lock?unlocked=false"
                     f"&tenant_id={victim['tenant_id']}", headers=ih)
        r = await c.post(
            f"{base}/api/v1/{victim['tenant_id']}/control/stop_equipment/EQ-01",
            headers={"X-Access-Key": victim["access_key"]}, json={},
        )
        check("잠긴 네임스페이스는 403", r.status_code == 403, f"HTTP {r.status_code}")
        await c.post(f"{base}/api/instructor/control-lock?unlocked=true"
                     f"&tenant_id={victim['tenant_id']}", headers=ih)

        # --- 2. 키 검증 ----------------------------------------------------
        print("\n2. 키 검증 — 남의 공장은 못 건드린다")
        a, b = pool[0], pool[1]
        r = await c.post(
            f"{base}/api/v1/{a['tenant_id']}/control/stop_equipment/EQ-01",
            headers={"X-Access-Key": b["access_key"]}, json={},
        )
        check(f"{b['tenant_id']} 키로 {a['tenant_id']} 제어 시도 → 401",
              r.status_code == 401, f"HTTP {r.status_code}")
        r = await c.post(
            f"{base}/api/v1/{a['tenant_id']}/control/stop_equipment/EQ-01",
            json={},
        )
        check("키 없이 제어 시도 → 401", r.status_code == 401, f"HTTP {r.status_code}")

        # --- 3. 동시 제어 --------------------------------------------------
        print(f"\n3. {len(pool)}개 네임스페이스가 동시에 서로 다른 제어를 실행")
        # 각 테넌트마다 서로 다른 설비를 정지하고 서로 다른 rpm 을 지정한다
        plan = []
        for i, t in enumerate(pool):
            eq_stop = f"EQ-0{(i % 6) + 1}"
            eq_speed = f"EQ-0{((i + 3) % 6) + 1}"
            rpm = 600 + i * 100
            robot_target = ["EQ-01", "EQ-02", "EQ-03", "WH", "EQ-04", "EQ-05", "EQ-06", "DOCK"][i % 8]
            plan.append((t, eq_stop, eq_speed, rpm, robot_target))

        async def fire(t, eq_stop, eq_speed, rpm, robot_target):
            h = {"X-Access-Key": t["access_key"]}
            tid = t["tenant_id"]
            return await asyncio.gather(
                c.post(f"{base}/api/v1/{tid}/control/stop_equipment/{eq_stop}",
                       headers=h, json={"issued_by": f"iso-{tid}"}),
                c.post(f"{base}/api/v1/{tid}/control/set_equipment_speed/{eq_speed}",
                       headers=h, json={"rpm": rpm, "issued_by": f"iso-{tid}"}),
                c.post(f"{base}/api/v1/{tid}/control/dispatch_robot/AMR-01",
                       headers=h, json={"target": robot_target, "issued_by": f"iso-{tid}"}),
            )

        results = await asyncio.gather(*[fire(*p) for p in plan])
        codes = [r.status_code for group in results for r in group]
        check("동시 제어 명령 전부 성공", all(x == 200 for x in codes),
              f"{len([x for x in codes if x == 200])}/{len(codes)}건 200")

        await asyncio.sleep(4)   # 다음 tick 과 적재를 기다린다

        # --- 4. 결과 대조 --------------------------------------------------
        print("\n4. 각 네임스페이스가 자기 명령대로만 바뀌었는가")
        states = {}
        for t, *_ in plan:
            states[t["tenant_id"]] = (
                await c.get(f"{base}/api/v1/{t['tenant_id']}/state")
            ).json()

        ok_stop = ok_speed = ok_robot = True
        for t, eq_stop, eq_speed, rpm, robot_target in plan:
            snap = states[t["tenant_id"]]
            eqs = {e["equipment_id"]: e for e in snap["equipment"]}
            if eqs[eq_stop]["run_state"] != "STOP":
                ok_stop = False
            if abs(eqs[eq_speed]["target_rpm"] - rpm) > 0.5:
                ok_speed = False
            amr = next(r for r in snap["robots"] if r["robot_id"] == "AMR-01")
            if amr["target_node"] != robot_target:
                ok_robot = False

        check("각자 지정한 설비만 정지됨", ok_stop)
        check("각자 지정한 rpm 만 반영됨", ok_speed)
        check("각자 지정한 목적지로만 로봇 파견됨", ok_robot)

        # 교차 오염 — 남의 명령이 내 공장에 들어왔는가
        cross = []
        for t, eq_stop, eq_speed, rpm, _ in plan:
            for other, o_stop, o_speed, o_rpm, _ in plan:
                if other["tenant_id"] == t["tenant_id"]:
                    continue
                eqs = {e["equipment_id"]: e for e in states[t["tenant_id"]]["equipment"]}
                if o_stop != eq_stop and eqs[o_stop]["run_state"] == "STOP":
                    cross.append(f"{t['tenant_id']}.{o_stop} 가 {other['tenant_id']} 명령으로 정지")
                if o_speed != eq_speed and abs(eqs[o_speed]["target_rpm"] - o_rpm) < 0.5:
                    cross.append(f"{t['tenant_id']}.{o_speed} rpm 이 {other['tenant_id']} 값과 일치")
        check("교차 오염 없음", not cross, "; ".join(cross[:3]) if cross else "0건")

        # --- 5. 감사 로그 --------------------------------------------------
        print("\n5. 감사 로그도 네임스페이스별로 분리되는가")
        bad = []
        for t, *_ in plan:
            cmds = (await c.get(
                f"{base}/api/v1/{t['tenant_id']}/control/commands?limit=20")).json()["commands"]
            foreign = [x for x in cmds
                       if x["issued_by"] and x["issued_by"] != f"iso-{t['tenant_id']}"]
            if foreign:
                bad.append(f"{t['tenant_id']} 에 남의 명령 {len(foreign)}건")
        check("각 네임스페이스 로그에 자기 명령만", not bad, "; ".join(bad[:3]) if bad else "0건")

        # --- 6. 이상 주입 격리 ---------------------------------------------
        print("\n6. 이상 주입도 지정 네임스페이스에만 적용되는가")
        target = pool[0]["tenant_id"]
        # 주입 지속시간은 **가상 시간** 기준이다. 배속이 걸려 있으면 그만큼 빨리 끝난다.
        # 실제로 30초는 버티게 배속을 곱해 준다(x60 이면 1800 가상초).
        scale = max(1.0, float((await c.get(f"{base}/api/v1/health")).json()
                               ["clock"]["time_scale"]))
        r = await c.post(f"{base}/api/instructor/inject", headers=ih, json={
            "tenant_id": target, "kind": "sensor_dropout",
            "equipment_id": "EQ-02", "params": {"duration_seconds": 30 * scale},
        })
        inj_id = r.json().get("id")
        await asyncio.sleep(3)
        on_target = next(
            e for e in (await c.get(f"{base}/api/v1/{target}/state")).json()["equipment"]
            if e["equipment_id"] == "EQ-02")
        others_ok = True
        for t, *_ in plan[1:]:
            e = next(x for x in (await c.get(
                f"{base}/api/v1/{t['tenant_id']}/state")).json()["equipment"]
                if x["equipment_id"] == "EQ-02")
            if not e["sensor_online"]:
                others_ok = False
        check(f"{target} 의 EQ-02 만 결측", on_target["sensor_online"] is False and others_ok,
              f"대상 sensor_online={on_target['sensor_online']}, 나머지 정상={others_ok}")
        if inj_id:
            await c.delete(f"{base}/api/instructor/inject/{inj_id}", headers=ih)

        # --- 정리 -----------------------------------------------------------
        print("\n7. 정리 — 검증에 쓴 네임스페이스 초기화")
        resets = []
        for t, *_ in plan:
            rr = await c.post(f"{base}/api/instructor/reset?tenant_id={t['tenant_id']}",
                              headers=ih)
            resets.append(rr.status_code)
        rl = await c.post(f"{base}/api/instructor/control-lock?unlocked=false&tenant_id=*",
                          headers=ih)
        relocked = await c.get(f"{base}/api/v1/{plan[0][0]['tenant_id']}/state")
        check("초기화 및 제어 재잠금 완료",
              all(s == 200 for s in resets) and rl.status_code == 200
              and relocked.json()["control"]["unlocked"] is False,
              f"초기화 {sum(1 for s in resets if s == 200)}/{len(resets)} · 재잠금 확인")

    print("\n" + "=" * 70)
    if failures:
        print(f"실패 {len(failures)}건: " + ", ".join(failures))
        return 1
    print("전 항목 통과 — 네임스페이스 분리가 검증됐습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
