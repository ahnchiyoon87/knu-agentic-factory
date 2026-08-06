"""4일치 무인 리허설 — 수업을 사람 없이 처음부터 끝까지 재생해 본다.

왜 만들었는가
  제작 중 두 번, "짧게 돌리면 통과 · 오래 돌리면 실패"하는 결함을 놓쳤다.
  검증이 매번 초기화 직후에 돌아서 가장 유리한 조건만 재고 있었기 때문이다.
    · 감지 창이 길어지면 드리프트가 희석돼 미탐 (실습 중반부터 죽음)
    · 주입 지속시간이 가상 시간이라 배속이 걸리면 순식간에 끝남

  그래서 이 하네스에는 규칙이 하나 있다.

      ★ 시작할 때 한 번 말고는 초기화하지 않는다.

  Day 1 부터 Day 4 까지 한 번도 안 끊고 돌리면서, 학생이 무언가를 하는
  시점마다 **학생이 보는 것**을 그대로 검사한다.

무엇을 검사하지 못하는가 (정직하게)
  · 학생이 Day 2 에 자기 Supabase 에 만드는 것 — 학생마다 다르므로 검사 불가
  · 강의장 무선 구간·브라우저 렌더링 — 사람이 있어야 한다
  · 사람이 터미널에 y 를 치는 승인 — 여기서는 자동 승인으로 대체한다

사용법
    python 리허설_4일치.py --token <강사토큰>
    python 리허설_4일치.py --token <토큰> --quick     누적 대기를 줄여 빠르게(결함 놓칠 수 있음)
    python 리허설_4일치.py --token <토큰> --base-url http://192.168.0.10:8000

W1 서버가 떠 있어야 한다. 서버 설정은 **건드리지 않는다** — 출하 기본값 그대로가 도는지 보는 것이 목적이다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent          # 산출물/0_공통
OUT = ROOT.parent                                # 산출물/
W1 = ROOT / "W1_팩토리시뮬레이터"
W5 = OUT / "3일차_알기" / "W5_센서데이터셋"
LAB32 = OUT / "3일차_알기" / "Lab3-2_이상감지뼈대"
LAB33 = OUT / "3일차_알기" / "Lab3-3_MCP도구템플릿"
W6 = OUT / "4일차_움직이기" / "W6_폐루프템플릿"

START = time.time()
results: list[tuple[str, str, bool, str]] = []   # (일자, 항목, 통과, 상세)
skipped: list[tuple[str, str, str]] = []        # (일자, 항목, 이유)
_phase = "준비"


def elapsed() -> str:
    s = time.time() - START
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((_phase, name, bool(ok), detail))
    mark = "통과" if ok else "실패"
    print(f"  [{elapsed()}] [{mark}] {name}" + (f" — {detail}" if detail else ""), flush=True)
    return bool(ok)


def skip(name: str, why: str) -> None:
    """검사하지 않은 것을 통과로 세지 않는다. 침묵이 성공처럼 보이면 안 된다."""
    skipped.append((_phase, name, why))
    print(f"  [{elapsed()}] [건너뜀] {name} — {why}", flush=True)


def phase(title: str) -> None:
    global _phase
    _phase = title
    print(f"\n{'=' * 78}\n{title}   (경과 {elapsed()})\n{'=' * 78}", flush=True)


def wait(seconds: float, why: str) -> None:
    """데이터가 쌓이기를 기다린다. 이 하네스의 핵심이다 — 짧게 돌면 결함을 놓친다."""
    if seconds <= 0:
        return
    print(f"  [{elapsed()}] … {why} — {seconds:.0f}초 대기", flush=True)
    time.sleep(seconds)


class Sim:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.h = {"X-Instructor-Token": token}
        self.c = httpx.Client(timeout=60.0)

    def get(self, path: str, **params) -> dict:
        r = self.c.get(f"{self.base}{path}", params=params or None)
        r.raise_for_status()
        return r.json()

    def inst(self, method: str, path: str, **kw) -> dict:
        r = self.c.request(method, f"{self.base}/api/instructor{path}", headers=self.h, **kw)
        r.raise_for_status()
        return r.json()

    def status_code(self, method: str, path: str, **kw) -> int:
        return self.c.request(method, f"{self.base}{path}", **kw).status_code


# =============================================================================
# Day 1 — 학생이 대시보드를 만든다
# =============================================================================
def day1(s: Sim, ns: str, quick: bool) -> None:
    phase("Day 1 — 보기 : 학생이 시뮬레이터를 읽어 대시보드를 만든다")

    h = s.get("/api/v1/health")
    c = h["clock"]
    check("서버가 떠 있다", h["status"] == "ok", f"네임스페이스 {h['tenants']}개")
    check("배속이 기본값으로 켜져 있다 (강사가 아무것도 안 눌렀다)", c["time_scale"] >= 2,
          f"x{c['time_scale']:g}")
    check("교안 3절 '1초에 한 번씩 바뀐다' 가 지켜진다", c["real_tick_seconds"] == 1.0,
          f"실제 tick {c['real_tick_seconds']}초")
    check("팀 공간도 처음부터 떠 있다 (Day 4 에 재시작할 일이 없다)", h["tenants"] >= 47,
          f"{h['tenants']}개")

    st = s.get(f"/api/v1/{ns}/state")
    check("설비 6대 · 로봇 2대가 한 번에 온다",
          len(st["equipment"]) == 6 and len(st["robots"]) == 2)
    cols = {"equipment_id", "display_name", "pos_x", "pos_y", "temperature",
            "vibration", "rpm", "run_state", "target_rpm", "sensor_online"}
    check("설비 응답 필드가 API 명세와 같다", cols <= set(st["equipment"][0]))
    check("제어 통로 4개가 잠긴 채로 보인다 (덱B 33장)",
          st["control"]["unlocked"] is False and len(st["control"]["channels"]) == 4)
    check("제어를 부르면 403 이 돌아온다 (Day 1~3)",
          s.status_code("POST", f"/api/v1/{ns}/control/stop_equipment/EQ-01") == 403)
    check("공장 배치도가 온다 (AMR 통로 좌표)",
          len(s.get("/api/v1/layout")["equipment"]) == 6)

    # 값이 실제로 변하는가 — 학생 대시보드가 살아 있는지의 본질
    a = s.get(f"/api/v1/{ns}/equipment/EQ-01")["temperature"]
    wait(6, "값이 변하는지 보려고")
    b = s.get(f"/api/v1/{ns}/equipment/EQ-01")["temperature"]
    check("값이 계속 바뀐다", a != b, f"{a:.2f}℃ → {b:.2f}℃")

    # null 처리 — 안 하면 학생 화면이 통째로 죽는다
    scale = max(1.0, s.get("/api/v1/health")["clock"]["time_scale"])
    inj = s.inst("POST", "/inject", json={"tenant_id": ns, "equipment_id": "EQ-02",
                                          "kind": "sensor_dropout",
                                          "params": {"duration_seconds": 40 * scale}})
    check("주입 응답이 실제 소요 시간을 알려준다", inj.get("lasts_real_seconds") is not None,
          inj.get("note", "")[:60])
    wait(6, "결측이 반영되기를")
    eq = s.get(f"/api/v1/{ns}/equipment/EQ-02")
    check("센서 결측이 null 로 온다 (시드에 null 처리가 필요한 이유)",
          eq["temperature"] is None and eq["sensor_online"] is False)
    others = [e for e in s.get(f"/api/v1/{ns}/state")["equipment"]
              if e["equipment_id"] != "EQ-02"]
    check("결측은 그 설비에만 (나머지는 정상)", all(e["sensor_online"] for e in others))
    s.inst("DELETE", f"/inject/{inj['id']}")

    # 폴링 — 39명이 하는 그것
    lat, errs = [], 0
    for _ in range(10 if quick else 20):
        t0 = time.perf_counter()
        try:
            s.get(f"/api/v1/{ns}/state")
        except Exception:                                          # noqa: BLE001
            errs += 1
        lat.append(time.perf_counter() - t0)
        time.sleep(2)
    lat.sort()
    check("2초 폴링이 안정적이다", errs == 0 and lat[int(len(lat) * 0.95)] < 0.5,
          f"에러 {errs} · p95 {lat[int(len(lat) * 0.95)] * 1000:.0f}ms")


# =============================================================================
# Day 2 — 스펙과 백엔드 (학생 Supabase 는 검사 못 함)
# =============================================================================
def day2(s: Sim, ns: str) -> None:
    phase("Day 2 — 시키기 : 스펙으로 백엔드를 만든다")
    print("  (학생이 자기 Supabase 에 만드는 것은 학생마다 달라 검사할 수 없다.")
    print("   여기서는 시뮬레이터가 Day 2·3 에 제공해야 하는 면만 본다)")

    r = s.get(f"/api/v1/{ns}/readings", minutes=5, limit=10)
    check("센서 이력이 교안 부록 A 6컬럼이다",
          r["columns"] == ["equipment_id", "timestamp", "temperature",
                           "vibration", "rpm", "run_state"])
    m = s.get(f"/api/v1/{ns}/maintenance", limit=5)
    check("정비 이력이 온다 (Day 3 진단의 재료)", m["count"] > 0, f"{m['count']}건")
    opens = [x for x in s.get(f"/api/v1/{ns}/maintenance", equipment_id="EQ-03")["maintenance"]
             if x["status"] != "DONE"]
    check("EQ-03 에 미완 작업지시가 있다 (원인 추정의 실마리)", bool(opens),
          opens[0]["work_order_no"] if opens else "없음")


# =============================================================================
# Day 3 — 알기 : 이상감지 · MCP 도구화
# =============================================================================
def run_script(path: Path, args: list[str], timeout: int) -> tuple[bool, str]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        p = subprocess.run([sys.executable, str(path.name), *args], cwd=str(path.parent),
                           capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, f"{timeout}초 안에 안 끝남"
    tail = [l for l in p.stdout.splitlines() if l.strip()]
    return p.returncode == 0, (tail[-1][:70] if tail else f"종료코드 {p.returncode}")


def day3(s: Sim, ns: str) -> None:
    phase("Day 3 — 알기 : 이상감지 알고리즘과 MCP 도구화")

    csv = W5 / "데이터" / "sensor_readings_7days.csv"
    info = W5 / "데이터" / "생성정보.json"
    if csv.is_file() and info.is_file():
        meta = json.loads(info.read_text(encoding="utf-8"))
        got = hashlib.sha256(csv.read_bytes()).hexdigest()
        check("W5 데이터셋 해시가 기록과 일치한다 (배포본 대조)",
              got == meta.get("sha256"), got[:16] + "…")
        rows = sum(1 for _ in csv.open(encoding="utf-8")) - 1
        check("행수가 기록과 같다 (교안 부록 A · 6대×7일×1분)",
              rows == meta.get("행수"), f"{rows:,}행")
        check("컬럼이 교안 부록 A 와 같다",
              meta.get("컬럼") == ["equipment_id", "timestamp", "temperature",
                                   "vibration", "rpm", "run_state"])
    else:
        check("W5 데이터셋이 있다", False, f"없음: {csv.name} / {info.name}")

    ok, msg = run_script(LAB32 / "verify_lab.py", [], 300)
    check("Lab 3-2 이상감지 뼈대 — 교안이 가르치려는 것이 재현된다", ok, msg)

    ok, msg = run_script(LAB33 / "verify_lab.py", [], 300)
    check("Lab 3-3 MCP 도구 템플릿 — 서버를 띄워 도구가 왕복한다", ok, msg)

    r = s.get(f"/api/v1/{ns}/readings", equipment_id="EQ-01", minutes=60, limit=20000)
    check("보존정책 안의 이력이 조회된다", r["count"] > 0, f"{r['count']}행")


# =============================================================================
# Day 4 — 움직이기 : 폐루프
# =============================================================================
def day4(s: Sim, base: str, token: str, teams: list[str], quick: bool) -> None:
    phase("Day 4 — 움직이기 : 제어 개방과 폐루프")

    # 강사가 누르는 것 — 명령 하나
    ok, msg = run_script(W1 / "tools" / "day4.py", [], 120)
    check("Day 4 준비가 명령 하나로 끝난다 (tools/day4.py)", ok, msg)

    st = s.get(f"/api/v1/{teams[0]}/state")
    check("제어 통로가 열렸다", st["control"]["unlocked"] is True)
    warn = s.inst("GET", "/status")["warnings"]
    check("콘솔이 '주입이 없다'를 스스로 경고한다",
          any(w["code"] == "DAY4_NO_INJECTION" for w in warn),
          ", ".join(w["code"] for w in warn) or "경고 없음")

    keys = {t["tenant_id"]: t["access_key"] for t in s.inst("GET", "/tenants")["tenants"]}

    # ---- 격리 : 두 팀이 동시에 다른 제어를 한다 ------------------------------
    a, b = teams[0], teams[1]
    ra = s.c.post(f"{base}/api/v1/{a}/control/set_equipment_speed/EQ-04",
                  json={"rpm": 900, "issued_by": "rehearsal"},
                  headers={"X-Access-Key": keys[a]})
    rb = s.c.post(f"{base}/api/v1/{b}/control/set_equipment_speed/EQ-05",
                  json={"rpm": 2400, "issued_by": "rehearsal"},
                  headers={"X-Access-Key": keys[b]})
    check("두 팀이 동시에 서로 다른 설비를 제어한다",
          ra.status_code == 200 and rb.status_code == 200)
    cross = s.c.post(f"{base}/api/v1/{a}/control/stop_equipment/EQ-01",
                     json={}, headers={"X-Access-Key": keys[b]})
    check("남의 키로는 못 건드린다", cross.status_code == 401)
    sa = {e["equipment_id"]: e for e in s.get(f"/api/v1/{a}/state")["equipment"]}
    sb = {e["equipment_id"]: e for e in s.get(f"/api/v1/{b}/state")["equipment"]}
    check("교차 오염이 없다",
          abs(sa["EQ-04"]["target_rpm"] - 900) < 1 and abs(sb["EQ-05"]["target_rpm"] - 2400) < 1
          and abs(sb["EQ-04"]["target_rpm"] - 900) > 1,
          f"{a}/EQ-04={sa['EQ-04']['target_rpm']:.0f} · {b}/EQ-04={sb['EQ-04']['target_rpm']:.0f}")

    # ---- 폐루프 : 학생이 실제로 돌리는 그 코드 ------------------------------
    team = teams[2]
    # 감지기가 보는 상한(window_samples×2)만큼 실제로 쌓일 때까지 기다린다.
    # 고정 대기로는 배속·장비 속도에 따라 모자랄 수 있어 조건으로 기다린다.
    need = int(json.loads((W6 / "config.json").read_text(encoding="utf-8"))
               ["detect"]["window_samples"]) * 2

    def acc() -> int:
        return s.get(f"/api/v1/{team}/readings", equipment_id="EQ-03",
                     minutes=30, limit=20000)["count"]

    n_before = acc()
    if quick:
        skip("창이 이미 꽉 차 있다 (초기화 직후가 아니다)",
             f"--quick 이라 {n_before}/{need}샘플. 창 희석 결함은 이 모드로 못 잡는다")
    else:
        t0 = time.time()
        while n_before < need and time.time() - t0 < 900:
            print(f"  [{elapsed()}] … 창이 차기를 기다린다 {n_before}/{need}샘플", flush=True)
            time.sleep(30)
            n_before = acc()
        check("창이 감지기 상한만큼 꽉 찼다 (초기화 직후가 아니다 — 이 하네스의 요점)",
              n_before >= need, f"{n_before}/{need}샘플 누적")

    sys.path.insert(0, str(W6))
    sys.path.insert(0, str(W6 / "정답"))
    os.environ.update({"W6_BASE_URL": base, "W6_TENANT": team,
                       "W6_ACCESS_KEY": keys[team]})
    import agent_bodies                                            # noqa: E402
    agent_bodies.install()
    import hitl                                                    # noqa: E402
    import loop as looper                                          # noqa: E402
    from agents import detector                                    # noqa: E402
    from control_client import CONTROL_TOOLS, MCPControl           # noqa: E402
    from factory_api import FactoryAPI                             # noqa: E402

    hitl.CFG["hitl"]["auto_approve"] = True      # 사람이 y 를 치는 대신
    api = FactoryAPI()
    mcp = MCPControl(api=api)
    check("제어 4종이 MCP 도구로 열린다 (교안 8~9장)",
          sorted(mcp.tools) == sorted(CONTROL_TOOLS), ", ".join(sorted(mcp.tools)))

    cfg = json.loads((W6 / "config.json").read_text(encoding="utf-8"))
    cfg["hitl"]["auto_approve"] = True
    ctx = looper.Context(api=api, cfg=cfg, control=mcp)

    inj = s.inst("POST", "/inject", json={"tenant_id": team, "equipment_id": "EQ-03",
                                          "kind": "temp_drift"})
    print(f"  [{elapsed()}] 주입 — {inj['note']}")
    before = {e["equipment_id"]: e for e in s.get(f"/api/v1/{team}/state")["equipment"]}

    t0, hit, budget = time.time(), None, (240 if quick else 420)
    while time.time() - t0 < budget:
        found = [f for f in detector.run(ctx) if f["equipment_id"] == "EQ-03"]
        if found:
            hit = found[0]
            break
        time.sleep(10)
    check("오래 돌린 상태에서도 드리프트를 잡는다", hit is not None,
          f"{time.time() - t0:.0f}초 만에 — {hit['detail']}" if hit
          else f"{budget}초 안에 미탐 ★ 창 희석 결함")

    if hit:
        rec = looper.one_round(ctx)
        case = rec["cases"][0] if rec["cases"] else {}
        diag = case.get("diagnosis", {})
        acts = case.get("actions", [])
        check("진단이 실제 모델로 돈다", diag.get("backend") in ("openai", "claude"),
              f"{diag.get('backend')} · {diag.get('model')}")
        check("정비 이력을 근거로 쓴다",
              any("WO-" in str(e) or "냉각" in str(e) for e in diag.get("evidence", [])))
        check("감속은 승인 없이 실행된다",
              any(x["command"] == "set_equipment_speed" and x["mode"] == "AUTO"
                  and x["status"] == "EXECUTED" for x in acts))
        wait(0 if quick else 25, "감속이 온도에 닿기를")
        after = {e["equipment_id"]: e for e in s.get(f"/api/v1/{team}/state")["equipment"]}
        check("공장이 실제로 바뀌었다 — 회전수가 내려갔다",
              after["EQ-03"]["target_rpm"] < before["EQ-03"]["target_rpm"],
              f"{before['EQ-03']['target_rpm']:.0f} → {after['EQ-03']['target_rpm']:.0f} rpm")
        if quick:
            skip("감속이 온도를 끌어내렸다 — 루프가 닫혔다", "--quick 이라 하강 대기를 생략")
        else:
            check("감속이 온도를 끌어내렸다 — 루프가 닫혔다",
                  after["EQ-03"]["temperature"] < hit["recent"],
                  f"{hit['recent']:.1f}℃ → {after['EQ-03']['temperature']:.1f}℃")
        cmds = s.get(f"/api/v1/{team}/control/commands", limit=20)["commands"]
        check("모든 조치가 감사 로그에 남는다",
              any(c["command"] == "set_equipment_speed" for c in cmds), f"{len(cmds)}건")

        # 확장 미션 지점
        import agents as reg                                       # noqa: E402
        sys.path.insert(0, str(W6 / "확장미션"))
        import importlib                                           # noqa: E402
        extra = importlib.import_module("예시_교대리포트")
        reg.EXTRA = [extra]
        try:
            r2 = looper.one_round(ctx)
            check("확장 에이전트를 붙이면 오케스트레이터가 부른다 (loop.py 무수정)",
                  "extra" in r2 and extra.ROLE in r2["extra"])
        finally:
            reg.EXTRA = []

    mcp.close()
    api.close()
    (W6 / "실행기록.jsonl").unlink(missing_ok=True)


# =============================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="4일치 무인 리허설")
    ap.add_argument("--token", required=True, help="X-Instructor-Token")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--ns", default="S01", help="Day 1~3 에 쓸 개인 네임스페이스")
    ap.add_argument("--quick", action="store_true", help="누적 대기를 줄인다(결함을 놓칠 수 있음)")
    ap.add_argument("--soak", type=float, default=None,
                    help="Day 3~4 사이 추가 누적 시간(초). 기본은 창이 찰 만큼")
    args = ap.parse_args()

    print("=" * 78)
    print("4일치 무인 리허설 — 수업을 사람 없이 처음부터 끝까지 재생한다")
    print(f"  대상 {args.base_url} · 시작 {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("  ★ 규칙 — 시작할 때 한 번 말고는 초기화하지 않는다")
    print("=" * 78)

    s = Sim(args.base_url, args.token)
    try:
        s.get("/api/v1/health")
    except Exception as exc:                                       # noqa: BLE001
        print(f"\n서버에 닿지 못했습니다 — {type(exc).__name__}: {exc}", file=sys.stderr)
        print("  W1 폴더에서 서버를 먼저 띄우세요.", file=sys.stderr)
        return 1

    teams = [t["tenant_id"] for t in s.get("/api/v1/tenants")["tenants"]
             if t["tenant_id"].startswith("T")][:3]
    if len(teams) < 3:
        print("\n팀 네임스페이스가 3개 미만입니다. TENANT_MODE 를 both 로 두세요.", file=sys.stderr)
        return 1

    # 처음 한 번만 초기화한다. 이후로는 절대 하지 않는다.
    print(f"\n초기화(처음 한 번) — {args.ns}, {', '.join(teams)}")
    for t in [args.ns, *teams]:
        s.inst("POST", "/reset", params={"tenant_id": t})

    try:
        day1(s, args.ns, args.quick)
        day2(s, args.ns)
        day3(s, args.ns)
        soak = args.soak if args.soak is not None else (0 if args.quick else 240)
        wait(soak, "실습이 진행되는 동안 데이터가 쌓이도록 (여기가 결함이 드러나는 자리)")
        day4(s, args.base_url, args.token, teams, args.quick)
    finally:
        phase("정리 — Day 1~3 상태로 되돌린다")
        run_script(W1 / "tools" / "day4.py", ["--end"], 120)
        for t in [args.ns, *teams]:
            try:
                s.inst("POST", "/reset", params={"tenant_id": t})
            except Exception:                                      # noqa: BLE001
                pass
        print(f"  [{elapsed()}] 되돌렸습니다")

    # ---- 요약 ---------------------------------------------------------------
    print("\n" + "=" * 78)
    print(f"요약   총 소요 {elapsed()}")
    print("=" * 78)
    by_day: dict[str, list] = {}
    for d, name, ok, detail in results:
        by_day.setdefault(d, []).append((name, ok, detail))
    for d, items in by_day.items():
        bad = [i for i in items if not i[1]]
        print(f"  {'✔' if not bad else '✗'} {d:<52} {len(items) - len(bad)}/{len(items)}")
        for name, _ok, detail in bad:
            print(f"      실패 — {name}" + (f" ({detail})" if detail else ""))

    if skipped:
        print(f"\n  건너뛴 검사 {len(skipped)}건 — 이 항목들은 **검증되지 않았습니다**")
        for _d, name, why in skipped:
            print(f"      · {name} ({why})")

    failed = [r for r in results if not r[2]]
    print("-" * 78)
    if failed:
        print(f"실패 {len(failed)}건 / 전체 {len(results)}건")
        return 1
    if skipped:
        print(f"통과 {len(results)}건 · **건너뜀 {len(skipped)}건** — 전체 검증이 아닙니다. "
              "--quick 없이 다시 돌리세요.")
        return 0
    print(f"전 항목 통과 — {len(results)}건. 4일치가 초기화 없이 연속으로 돌았습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
