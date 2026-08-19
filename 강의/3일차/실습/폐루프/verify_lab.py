"""3일차 오후 폐루프 템플릿 검증 — 코드 쪽 품질 게이트.

교안 3일차 가 요구하는 것이 이 템플릿 위에서 실제로 성립하는지 확인한다.

    4~7장   감지 / 진단 / 조치 + 오케스트레이터 (Orchestrator-Worker 회수)
    10~11장 감속은 자동, 정지와 로봇 파견은 사람 승인
    12~14장 드리프트 주입 → 감지 → 진단 → 감속 실행 + 파견 승인 요청 → 승인 → AMR 이동
    기본 미션 — 학생 39명이 60분 안에 자기 공장에서 폐루프를 돌린다

라이브 검증은 실제로 시뮬레이터에 붙어 드리프트를 주입하고, 폐루프가 그것을
잡아 설비를 움직이는지까지 본다. "함수가 있다"와 "공장이 움직였다"는 다르다.

    uv run verify_lab.py                          템플릿·감지만 (서버 불필요)
    uv run verify_lab.py --live --token <토큰>    전 항목 (시뮬레이터 필요)
"""

from __future__ import annotations

# ── 한글 윈도우(cp949)에서 출력이 깨져 죽는 것을 막는다 ──────────────────
#    학생 PC 기본 콘솔은 cp949 라 `—` `→` 같은 글자에서 UnicodeEncodeError 가 난다.
#    리허설은 PYTHONUTF8=1 로 돌아가 이 문제가 안 보인다. 학생은 그냥 실행한다.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────────────────

import argparse
import builtins
import json
import random
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "정답"))

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'통과' if ok else '실패'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def set_cfg(**kw) -> dict:
    p = ROOT / "config.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    for k, v in kw.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


# =============================================================================
# 합성 시계열 — 7일치 CSV 와 같은 기울기로 만든다
# =============================================================================
def series(minutes: int, drift_c_per_hour: float = 0.0, base: float = 62.0,
           sigma: float = 0.35, seed: int = 7) -> list[float]:
    rnd = random.Random(seed)
    return [base + drift_c_per_hour * (i / 60) + rnd.gauss(0, sigma) for i in range(minutes)]


# =============================================================================
# 1. 템플릿
# =============================================================================
def part_template() -> None:
    print("\n1. 템플릿 — 학생이 처음 열었을 때")

    import agents
    import hitl

    # 채울 자리는 `raise` 가 아니라 **주석 블록**이다. 빈 함수는 조용히 None 을 돌려주므로
    # 「막혀 있는가」를 예외로는 못 본다 — 등록표가 소스를 읽어 판정한다.
    빈것 = [이름 for 이름, _파일, _역할 in agents.안채운자리()]
    check("채울 자리 3곳이 빈 채로 나간다 (학생이 처음 여는 상태)",
          sorted(빈것) == sorted(["judge", "build_prompt", "to_commands"]),
          f"{len(빈것)}/3 — {' · '.join(빈것) or '없음'}")
    for 이름, 파일, 역할 in [(n, *agents.BLANKS[n]) for n in agents.BLANKS]:
        src = (ROOT / 파일).read_text(encoding="utf-8")
        빈칸 = sum(1 for l in src.splitlines() if l.strip().endswith("..."))
        check(f"{역할} — 채울 빈칸(`...`)이 있고 `raise` 가 없다 ({파일})",
              "빈칸 " in src and 빈칸 >= 1 and "NotImplementedError" not in src,
              f"빈칸 {빈칸}개")
    # 안 채운 자리를 만나면 **멈춰서 어디인지 알려 줘야** 한다.
    # 조용히 「이상 없음」·「실행할 조치가 없습니다」로 넘어가면 학생은 자기 코드를 의심한다.
    for 역할, 파일 in (("감지", "agents/detector.py"), ("진단", "agents/diagnoser.py"),
                      ("조치", "agents/actuator.py")):
        src = (ROOT / 파일).read_text(encoding="utf-8")
        check(f"{역할} 에이전트가 자기 차례에 안 채움을 잡아 세운다", "확인(" in src)

    loop_src = (ROOT / "loop.py").read_text(encoding="utf-8")
    check("오케스트레이터는 완성되어 있다 — 학생은 에이전트만 채운다",
          "agents.SENSE.run" in loop_src and "agents.DIAGNOSE.run" in loop_src
          and "agents.ACT.run" in loop_src)
    # 오케스트레이터가 특정 에이전트를 import 하거나 직접 부르면 갈아 끼울 수 없다.
    # 잡으려는 것은 **에이전트 이름**이다. `from agents import ...` 자체는 등록표를 거치는
    # 정상 경로라 결합이 아니다 — 통째로 막으면 등록표가 내놓는 것도 못 쓰게 된다.
    # (`from agents import detector` 는 아래 "import detector" 에 걸린다)
    coupled = [p for p in ("agents.detector", "agents.diagnoser", "agents.actuator",
                           "import detector", "import diagnoser",
                           "import actuator") if p in loop_src]
    check("오케스트레이터가 에이전트를 이름으로 알지 않는다 (등록표만 본다)",
          "import agents" in loop_src and not coupled, ", ".join(coupled) or "결합 없음")
    check("확장 지점이 오케스트레이터 안에 있다 — 새 에이전트는 loop.py 를 안 고친다",
          "agents.EXTRA" in loop_src)

    # 교안 10~11장이 못 박은 규칙. 학생이 우회할 수 없어야 한다.
    check("감속은 자동 — 승인을 묻지 않는다", not hitl.needs_approval("set_equipment_speed"))
    check("정지는 사람 승인", hitl.needs_approval("stop_equipment"))
    check("로봇 파견은 사람 승인", hitl.needs_approval("dispatch_robot"))
    check("모르는 명령은 안전한 쪽으로 — 물어본다", hitl.needs_approval("무언가_새_명령"))
    act_src = (ROOT / "agents" / "actuator.py").read_text(encoding="utf-8")
    check("승인 관문이 조치 에이전트 안에서 강제된다 (학생이 건너뛸 수 없다)",
          "hitl.ask(" in act_src)


# =============================================================================
# 2. 감지 — 어제 것으로는 안 잡히고, 오늘 것으로는 잡히는가
# =============================================================================
def part_detect() -> None:
    print("\n2. 감지 — 2일차의 한계를 3일차에서 넘는가 (같은 0.5℃/h 기울기)")

    import agent_bodies
    agent_bodies.install()
    from agents import detector

    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["detect"]

    flat = series(240, 0.0)
    drift = series(240, 0.5)

    v_flat = detector.judge(flat, cfg)
    v_drift = detector.judge(drift, cfg)
    check("평탄 구간은 이상이 아니다 (오탐 없음)", v_flat is None)
    check("4시간 0.5℃/h 드리프트를 잡는다", v_drift is not None,
          v_drift["detail"] if v_drift else "미탐")

    cooling = series(240, -0.5, base=64.0)
    check("내려가는 것은 이상이 아니다 — 조치가 먹힌 것이다",
          detector.judge(cooling, cfg) is None)

    short = series(20, 0.5)
    check("표본이 모자라면 판정하지 않는다", detector.judge(short, cfg) is None)

    # ── 실습 정상 상태 — 여기서 한 번 놓쳤다. 반드시 남겨 둘 것 ─────────────
    # 학생은 loop.py 를 실습 내내 돌린다. 드리프트는 12분치 안의 짧은 구간일 뿐이라
    # 최근 구간만 보지 않으면 신호가 +1.2℃ 에서 +0.5℃ 로 흐려지고,
    # **이상이 끝난 뒤에도 그 구간이 남아 계속 울린다**(실측 — 가상 300분 뒤 +0.52℃).
    RAMP, HOLD, RISE = 240, 60, 2.0        # 가상 4h 램프 + 1h 유지, 62→64℃

    def steady(total: int, elapsed: int, seed: int = 7) -> list[float]:
        rnd = random.Random(seed)
        out = []
        for i in range(total):
            age = elapsed - (total - 1 - i)
            off = (0.0 if age <= 0 else
                   RISE * age / RAMP if age <= RAMP else
                   RISE if age <= RAMP + HOLD else 0.0)
            out.append(62.0 + off + rnd.gauss(0, 0.35))
        return out

    long_run = steady(3000, 260)           # 25분 돌린 상태에서 드리프트가 진행 중
    v_long = detector.judge(long_run, cfg)
    check("한참 돌린 뒤에도 진행 중인 드리프트를 잡는다 (최근 구간만 본다)",
          v_long is not None,
          v_long["detail"] if v_long else "★ 미탐 — 최근 구간만 보게 안 자르면 흐려진다")

    fresh = steady(400, 200)               # 갓 켠 학생 — 데이터가 얼마 없다
    check("갓 켠 학생도 잡는다 (있는 만큼으로 판정)", detector.judge(fresh, cfg) is not None)

    quiet = [62.0 + random.Random(s).gauss(0, 0.35) for s in range(3000)]
    check("오래 돌려도 평온할 때는 안 울린다", detector.judge(quiet, cfg) is None)

    # 새 기준은 드리프트와 평탄을 갈라야 한다 — 어제의 z-score 는 그러지 못했다
    check("드리프트와 평탄을 실제로 갈라낸다",
          v_drift is not None and v_flat is None,
          f"드리프트 +{v_drift['delta']}℃ vs 평탄 미검출" if v_drift else "미탐")

    try:
        sys.path.insert(0, str(ROOT.parents[2] / "2일차" / "실습" / "정답"))
        from detect_answer import detect as zscore
        n_drift = sum(1 for f in zscore(list(drift), window=cfg["spike_window"],
                                        k=cfg["spike_k"]) if f)
        n_flat = sum(1 for f in zscore(list(flat), window=cfg["spike_window"],
                                       k=cfg["spike_k"]) if f)
        # 드리프트가 있으나 없으나 검출 수가 같다 = 구분하지 못한다는 뜻
        check("어제의 z-score 는 드리프트와 평탄을 구분하지 못한다 (그래서 기준을 바꿨다)",
              abs(n_drift - n_flat) <= 2,
              f"드리프트 {n_drift}건 vs 평탄 {n_flat}건 — 차이 없음(둘 다 노이즈 꼬리)")
    except Exception as exc:                                       # noqa: BLE001
        print(f"  [건너뜀] 2일차 정답을 못 읽어 대조 생략 — {type(exc).__name__}")


# =============================================================================
# 2-b. 진단 지시문 — 재료가 빠짐없이 들어가는가
# =============================================================================
def part_prompt() -> None:
    print("\n2-b. 진단 지시문 — 원인 추정의 재료가 다 들어가는가")

    import agent_bodies
    agent_bodies.install()
    from agents import actuator, diagnoser

    evidence = {
        "finding": {"equipment_id": "EQ-03", "metric": "temperature", "kind": "DRIFT",
                    "detail": "최근 63.9℃ (기준 62.0℃, +1.9℃ 상승)",
                    "current_rpm": 1800.0, "run_state": "RUN", "sample_count": 600},
        "maintenance": [
            {"work_order_no": "WO-2026-0801", "status": "IN_PROGRESS",
             "issued_at": "2026-08-01", "action": "냉각 계통 정기점검",
             "note": "부품 입고 지연으로 보류. 재개 일자 미정"},
            {"work_order_no": "WO-2026-0712", "status": "DONE",
             "issued_at": "2026-07-12", "action": "냉각수 필터 교체", "note": "필터 오염 심함"},
        ],
        "open_work_orders": [
            {"work_order_no": "WO-2026-0801", "status": "IN_PROGRESS",
             "action": "냉각 계통 정기점검", "note": "부품 입고 지연으로 보류. 재개 일자 미정"},
        ],
    }
    acfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["act"]
    system, user = diagnoser.build_prompt(evidence, acfg)

    check("system·user 두 문장을 만든다", isinstance(system, str) and isinstance(user, str)
          and len(system) > 50 and len(user) > 100, f"system {len(system)}자 · user {len(user)}자")
    check("감지 사실이 들어간다", "EQ-03" in user and "63.9" in user)
    check("정비 이력의 note 가 들어간다 — 원인 추정이 여기서 나온다",
          "부품 입고 지연" in user)
    check("미완 작업지시가 따로 드러난다", user.count("WO-2026-0801") >= 2)
    check("승인 규칙을 지시문이 알려 준다 (교안 10~11장)",
          ("승인" in system or "승인" in user) and "감속" in system + user)
    check("자료 밖을 지어내지 말라고 못 박는다",
          any(w in system for w in ("만들어 내지", "지어내", "자료만")))

    enum = diagnoser.SCHEMA["properties"]["actions"]["items"]["properties"]["type"]["enum"]
    check("진단이 낼 수 있는 조치 = 조치 에이전트가 아는 조치",
          set(enum) - {"none"} == set(actuator.COMMAND_OF), ", ".join(enum))
    check("스키마가 자유 서술을 막는다 (구조화 출력)",
          diagnoser.SCHEMA.get("additionalProperties") is False
          and "actions" in diagnoser.SCHEMA["required"])


# =============================================================================
# 3~7. 라이브 — 실제 공장에 붙는다
# =============================================================================
def actuator_module():
    from agents import actuator
    return actuator


def part_live(base: str, tenant: str, timeout_s: float) -> None:
    """공장이 3일차 상태(제어 개방)로 켜져 있어야 한다 —
    강사 저장소라면  강의/시뮬레이터  에서  uv run 3일차준비.py sk-열쇠  한 줄이다.
    깨끗한 상태에서 재려면 먼저  docker compose down -v && docker compose up -d.
    """
    print(f"\n3. 라이브 — {base} · {tenant}")

    import agent_bodies
    import hitl
    import loop as looper
    from factory_api import FactoryAPI

    agent_bodies.install()

    key = "local-lab-key"          # 003 시드의 고정값 — 비밀이 아니다

    api = FactoryAPI(base_url=base, tenant=tenant, access_key=key)
    info = api.preflight()
    if not info["제어_개방"]:
        check("제어 통로가 열렸다 (3일차 상태)", False,
              "잠겨 있다 — 저장소 루트에서  uv run 3일차준비.py sk-열쇠  뒤  uv run 제어열기.py")
        return
    check("제어 통로가 열렸다 (어제까지 잠겨 있던 그 네 개)", info["제어_개방"])

    # 교안 3절·8~9장 — 제어 4종은 MCP 도구 형태로 열린다
    from control_client import CONTROL_TOOLS, DirectControl, MCPControl, open_control
    mcp_ctl = MCPControl(api=api)
    check("제어가 MCP 도구로 열린다 (교안 8~9장)",
          sorted(mcp_ctl.tools) == sorted(CONTROL_TOOLS), ", ".join(sorted(mcp_ctl.tools)))
    probe = mcp_ctl.set_equipment_speed("EQ-06", 1500)
    after_probe = {e["equipment_id"]: e for e in api.state()["equipment"]}["EQ-06"]
    check("MCP 도구 호출이 실제로 공장을 움직인다",
          probe.get("ok") is True and abs(after_probe["target_rpm"] - 1500) < 1,
          f"EQ-06 target_rpm={after_probe['target_rpm']:.0f}")
    bad = mcp_ctl.stop_equipment("EQ-99")
    check("잘못된 인자는 예외가 아니라 결과로 돌아온다 (에이전트가 읽을 수 있게)",
          bad.get("ok") is False and "404" in str(bad.get("error")),
          str(bad.get("error"))[:70])
    fallback = open_control({"control_transport": "direct"}, api)
    check("우회 경로도 같은 이름·같은 시그니처다 (config 한 줄로 바꾼다)",
          isinstance(fallback, DirectControl)
          and all(hasattr(fallback, t) for t in CONTROL_TOOLS))

    before = {e["equipment_id"]: e for e in api.state()["equipment"]}

    time.sleep(12)   # 드리프트 전 평탄 구간을 확보한다
    # 학생 화면의 「이상 시작」 버튼과 같은 창구다 — 배속 x120 까지 스스로 건다
    inj = httpx.post(f"{base.rstrip('/')}/api/v1/{tenant}/drill", timeout=30).json()
    print(f"  이상 시작  {inj.get('안내', '')}")

    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    ctx = looper.Context(api=api, cfg=cfg, control=mcp_ctl)

    from agents import detector
    started = time.time()
    findings: list[dict] = []
    while time.time() - started < timeout_s:
        findings = detector.run(ctx)
        if any(f["equipment_id"] == "EQ-03" for f in findings):
            break
        time.sleep(5)
    waited = time.time() - started

    hit = next((f for f in findings if f["equipment_id"] == "EQ-03"), None)
    check("주입한 드리프트를 폐루프가 실제로 잡는다", hit is not None,
          f"{waited:.0f}초 만에 — {hit['detail']}" if hit else f"{timeout_s:.0f}초 안에 미탐")
    check("엉뚱한 설비를 잡지 않는다", all(f["equipment_id"] == "EQ-03" for f in findings),
          ", ".join(f["equipment_id"] for f in findings) or "없음")
    if hit is None:
        return

    # ---------------------------------------------------- 진단 (실제 LLM)
    from agents import diagnoser

    found = diagnoser.credentials(ctx.cfg["diagnose"])
    print(f"\n4. 진단 — 실제 LLM 호출 ({found[0] if found else '키 없음'})")
    if found:
        provider = found[0]
        ctx.cfg["diagnose"]["backend"] = provider
        llm = diagnoser.run(ctx, hit)
        check("실제 모델이 진단을 돌려준다 (규칙 대체가 아니다)",
              llm.get("backend") == provider, f"{llm.get('backend')} · {llm.get('model')}")
        check("스키마대로 온다 — 자유 서술이 아니다",
              all(k in llm for k in ("cause", "evidence", "severity", "actions", "summary")))
        check("근거를 자료 안에서만 가져온다 — 지어내지 않는다",
              any("WO-2026-0801" in str(e) or "냉각" in str(e) or "입고" in str(e)
                  for e in llm.get("evidence", [])) or "WO-2026-0801" in str(llm.get("cause")),
              "; ".join(str(e)[:60] for e in llm.get("evidence", []))[:150])
        kinds_llm = [a.get("type") for a in llm.get("actions", [])]
        check("실행 가능한 조치를 낸다", bool(set(kinds_llm) - {"none"}), ", ".join(kinds_llm))
        print(f"    원인 — {llm.get('cause')}")
        print(f"    요약 — {llm.get('summary')}")
        for a in llm.get("actions", []):
            print(f"    조치 — {a.get('type')} {a.get('equipment_id') or ''} "
                  f"rpm={a.get('rpm')} robot={a.get('robot_id')} : {a.get('why')}")
        cmds_llm = actuator_module().to_commands(llm, hit, ctx.cfg["act"])
        check("실제 모델의 조치가 조치 에이전트에 그대로 꽂힌다",
              all(c["command"] in actuator_module().COMMAND_OF.values() for c in cmds_llm),
              ", ".join(f"{c['command']}({c['target']})" for c in cmds_llm) or "명령 없음")
    else:
        print("  [건너뜀] OPENAI_API_KEY 가 없어 LLM 경로 미검증")
        failures.append("실제 LLM 진단 미검증(키 없음)")

    # ---------------------------------------------------- 진단 (규칙 · 결정적)
    print("\n4-b. 진단 → 조치 (규칙 기반 · 시연 시퀀스 재현)")
    ctx.cfg["diagnose"]["backend"] = "rules"
    diagnosis = diagnoser.run(ctx, hit)
    check(f"원인을 추정한다 (backend={diagnosis.get('backend')})",
          bool(diagnosis.get("cause")), (diagnosis.get("cause") or "")[:60])
    check("정비 이력을 근거로 쓴다 — 미완 작업지시가 실마리다",
          any("WO-2026-0801" in str(e) for e in diagnosis.get("evidence", []))
          or "WO-2026-0801" in str(diagnosis.get("cause", "")),
          "; ".join(str(e)[:50] for e in diagnosis.get("evidence", []))[:90])
    kinds = [a.get("type") for a in diagnosis.get("actions", [])]
    check("감속과 로봇 파견을 함께 낸다 (시연 시퀀스와 같다)",
          "slow_down" in kinds and "dispatch_robot" in kinds, ", ".join(kinds))

    # ---------------------------------------------------- 조치 · 승인 거부
    print("\n5. 승인 관문 — 교안 10~11장 규칙이 실제로 작동하는가")
    set_cfg(hitl={"auto_approve": False})
    ctx.cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    hitl.CFG = ctx.cfg
    orig_input = builtins.input
    builtins.input = lambda *_: "n"                     # 사람이 거부한다
    try:
        from agents import actuator
        denied_run = actuator.run(ctx, hit, diagnosis)
    finally:
        builtins.input = orig_input

    speed = [r for r in denied_run if r["command"] == "set_equipment_speed"]
    disp = [r for r in denied_run if r["command"] == "dispatch_robot"]
    check("감속은 승인을 묻지 않고 실행된다",
          bool(speed) and speed[0]["mode"] == "AUTO" and speed[0]["status"] == "EXECUTED",
          speed[0].get("detail") if speed else "명령 없음")
    check("거부하면 로봇 파견이 실행되지 않는다",
          bool(disp) and disp[0]["status"] == "DENIED", disp[0]["mode"] if disp else "명령 없음")

    mid = {r["robot_id"]: r for r in api.state()["robots"]}
    check("거부된 로봇은 실제로 움직이지 않았다",
          mid[cfg["act"]["maintenance_robot"]]["status"] != "MOVING",
          mid[cfg["act"]["maintenance_robot"]]["status"])

    # ---------------------------------------------------- 조치 · 승인
    print("\n6. 승인하면 실제로 움직이는가")
    builtins.input = lambda *_: "y"
    try:
        approved = actuator.run(ctx, hit, diagnosis)
    finally:
        builtins.input = orig_input

    disp2 = [r for r in approved if r["command"] == "dispatch_robot"]
    check("승인하면 파견이 실행된다",
          bool(disp2) and disp2[0]["status"] == "EXECUTED" and disp2[0]["mode"] == "APPROVED")

    time.sleep(3)
    after = {e["equipment_id"]: e for e in api.state()["equipment"]}
    robots = {r["robot_id"]: r for r in api.state()["robots"]}
    check("공장이 실제로 바뀌었다 — EQ-03 목표 회전수가 내려갔다",
          after["EQ-03"]["target_rpm"] < before["EQ-03"]["target_rpm"],
          f"{before['EQ-03']['target_rpm']:.0f} → {after['EQ-03']['target_rpm']:.0f} rpm")
    check("AMR 이 EQ-03 로 향한다",
          robots[cfg["act"]["maintenance_robot"]]["target_node"] == "EQ-03",
          f"{robots[cfg['act']['maintenance_robot']]['status']} → "
          f"{robots[cfg['act']['maintenance_robot']]['target_node']}")

    # ---------------------------------------------------- 감사 로그
    hist = httpx.get(f"{base.rstrip('/')}/api/v1/{tenant}/control/commands", timeout=30).json()
    cmds = [c["command"] for c in hist["commands"]]
    check("모든 조치가 감사 로그에 남는다", "set_equipment_speed" in cmds
          and "dispatch_robot" in cmds, f"{len(cmds)}건")

    # ---------------------------------------------------- 루프가 닫혔는가
    print("\n7. 폐루프 — 조치가 원인에 닿았는가")
    time.sleep(20)                       # 열은 바로 안 내려간다 (tau 60초)
    cooled = {e["equipment_id"]: e for e in api.state()["equipment"]}["EQ-03"]
    check("감속이 온도를 실제로 끌어내렸다 — 조치가 원인에 닿았다",
          cooled["temperature"] < hit["recent"],
          f"{hit['recent']:.1f}℃ → {cooled['temperature']:.1f}℃")
    again = detector.run(ctx)
    check("다시 돌리면 이상이 사라졌다 — 루프가 닫혔다",
          not any(f["equipment_id"] == "EQ-03" for f in again),
          ", ".join(f["equipment_id"] for f in again) or "이상 없음")

    # ---------------------------------------------------- 확장 지점
    #   확장미션/ 폴더는 개인 단위 전환 때 없앴다. 그래도 loop.py 의 EXTRA 기구는
    #   남아 있으므로(README 「끝낸 뒤 더 해 볼 것」이 여기에 기댄다),
    #   삭제된 파일을 불러오는 대신 최소 에이전트를 그 자리에서 만들어 기구를 검사한다.
    print("\n8. 확장 지점 — 에이전트를 하나 더 붙일 수 있는가 (loop.py 무수정)")
    import types

    import agents as reg

    def _확장_run(ctx, record: dict) -> dict:
        """그 회차 기록을 그대로 받는지 확인한다 — 확장이 성립하는 조건."""
        return {"이상_설비": {f["equipment_id"]: f.get("detail")
                              for f in record.get("findings", [])},
                "조치_건수": sum(len(c.get("actions", []))
                                 for c in record.get("cases", []))}

    # 학생이 하는 것과 같은 모양으로 만든다 — agents/my_agent.py 모듈 하나를 EXTRA 에 등록
    extra = types.ModuleType("확장_점검용")
    extra.ROLE = "확장_점검"
    extra.run = _확장_run
    reg.EXTRA = [extra]
    try:
        rec = looper.one_round(ctx)
        check("EXTRA 에 등록하면 오케스트레이터가 부른다 (loop.py 를 안 고쳤다)",
              "extra" in rec and extra.ROLE in rec["extra"],
              ", ".join(rec.get("extra", {}).keys()) or "안 불림")
        check("확장 에이전트가 그 회차의 감지·진단·조치를 다 본다",
              isinstance(rec.get("extra", {}).get(extra.ROLE, {}).get("이상_설비"), dict))
    finally:
        reg.EXTRA = []

    # ---------------------------------------------------- 정리
    # 「이상 시작」을 멈추면 배속도 기본(x60)으로 돌아온다. 상태를 완전히 비우려면
    # 공장 폴더에서  docker compose down -v  한 줄이다 — 여기서 대신 눌러 주지 않는다.
    httpx.post(f"{base.rstrip('/')}/api/v1/{tenant}/drill/stop", timeout=30)
    print("  (이상을 멈추고 배속을 기본으로 돌려놨습니다)")
    mcp_ctl.close()
    api.close()


# =============================================================================
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="공장에 실제로 붙어 검증한다 (3일차 상태로 켜 두고)")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--tenant", default="S01")
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    print("=" * 74)
    print("3일차 오후 폐루프 템플릿 검증")
    print("=" * 74)

    original = (ROOT / "config.json").read_text(encoding="utf-8")
    log = ROOT / "실행기록.jsonl"
    had_log = log.exists()
    try:
        part_template()
        part_detect()
        part_prompt()
        if args.live:
            set_cfg(tenant=args.tenant, base_url=args.base_url,
                    hitl={"auto_approve": False})
            part_live(args.base_url, args.tenant, args.timeout)
        else:
            print("\n(라이브 검증 생략 — --live 로 실행하면 실제 공장까지 확인합니다)")
    finally:
        (ROOT / "config.json").write_text(original, encoding="utf-8")
        if not had_log:
            log.unlink(missing_ok=True)

    print("\n" + "=" * 74)
    if failures:
        print(f"실패 {len(failures)}건: " + ", ".join(failures))
        return 1
    print("전 항목 통과 — 3일차 폐루프가 이 템플릿 위에서 성립합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
