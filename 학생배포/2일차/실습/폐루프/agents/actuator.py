"""조치 에이전트 — 폐루프의 세 번째 책임.

    "제안을 실제 명령으로 바꿔 실행한다." 원인은 다시 따지지 않는다.

어제까지 잠겨 있던 통로 네 개가 오늘 열립니다.

    set_equipment_speed(id, rpm)      감속 — 자동으로 실행됩니다
    stop_equipment(id)                정지 — 사람 승인을 받습니다
    dispatch_robot(robot_id, target)  파견 — 사람 승인을 받습니다
    ack_alarm(id)                     알람 확인 — 자동으로 실행됩니다

승인 관문은 hitl.py 가 강제합니다. 여기서 우회할 수 없습니다.
"""

from __future__ import annotations

import hitl

ROLE = "조치"

# 진단이 낸 조치 이름 → 실제 제어 명령
COMMAND_OF = {
    "slow_down": "set_equipment_speed",
    "stop": "stop_equipment",
    "dispatch_robot": "dispatch_robot",
    "ack_alarm": "ack_alarm",
}


# =============================================================================
# ★ 여기를 채우세요
# =============================================================================
def to_commands(diagnosis: dict, finding: dict, cfg: dict) -> list[dict]:
    """진단이 낸 조치 제안을 '실행 가능한 명령'으로 바꾼다.

    Args:
        diagnosis: 진단 결과. actions[] 안에 type / rpm / robot_id / target / why
        finding: 감지 결과. equipment_id, current_rpm 등
        cfg: config.json 의 act 블록
             slow_down_ratio   감속 비율 (0.8 = 20% 낮춘다)
             min_rpm           이 아래로는 내리지 않는다
             maintenance_robot 정비용 로봇 이름

    Returns:
        [{"command": "set_equipment_speed", "target": "EQ-03",
          "args": {"rpm": 1440}, "detail": "1800 → 1440 rpm", "why": "..."}]
        실행할 게 없으면 빈 리스트

    ──────────────────────────────────────────────────────────────────
    할 일은 세 가지입니다.

      1. diagnosis["actions"] 를 하나씩 본다. type 이 "none" 이면 건너뛴다
      2. COMMAND_OF 로 실제 명령 이름을 찾는다. 모르는 type 은 버린다
      3. 명령마다 필요한 값을 채운다
           set_equipment_speed  args={"rpm": ...}
                                진단이 rpm 을 안 줬으면 현재 rpm × slow_down_ratio,
                                단 min_rpm 아래로는 내리지 않는다
           stop_equipment       args={"reason": ...}
           dispatch_robot       target 은 로봇 이름, args={"target": 설비ID}
                                로봇을 안 줬으면 maintenance_robot 을 쓴다
           ack_alarm            target 은 알람 id

    주의
      · detail 은 사람이 승인 화면에서 읽습니다. "1800 → 1440 rpm" 처럼 구체적으로
      · 같은 설비에 감속과 정지를 동시에 내지 마세요. 정지가 있으면 정지만 남깁니다
      · 진단이 이상한 값을 줘도 여기서 걸러야 합니다. 실제 설비가 움직입니다
    ──────────────────────────────────────────────────────────────────
    """
    # TODO: 여기를 채우세요
    raise NotImplementedError("to_commands 를 완성하세요")


# =============================================================================
# 실행 — 이미 되어 있습니다. 승인 규칙은 여기서 강제됩니다.
# =============================================================================
def _call(control, cmd: dict) -> dict:
    """제어 통로로 실제 명령을 내보낸다.

    control 은 MCP 도구(control_mcp.py)이거나 직접 호출 경로다.
    어느 쪽이든 이름과 시그니처가 같아서 여기서는 구분하지 않는다.
    """
    name, target, args = cmd["command"], cmd["target"], cmd.get("args", {})
    if name == "set_equipment_speed":
        out = control.set_equipment_speed(target, float(args["rpm"]))
    elif name == "stop_equipment":
        out = control.stop_equipment(target, reason=args.get("reason"))
    elif name == "dispatch_robot":
        out = control.dispatch_robot(target, str(args["target"]))
    elif name == "ack_alarm":
        out = control.ack_alarm(int(target), note=args.get("note"))
    else:
        raise ValueError(f"모르는 명령입니다: {name}")

    if isinstance(out, dict) and out.get("ok") is False:
        raise RuntimeError(out.get("error", "제어 도구가 실패를 돌려줬습니다."))
    return out


def run(ctx, finding: dict, diagnosis: dict) -> list[dict]:
    """명령을 만들고, 승인 관문을 거쳐, 실제로 실행한다."""
    commands = to_commands(diagnosis, finding, ctx.cfg["act"])
    results: list[dict] = []

    for cmd in commands:
        decision = hitl.ask(cmd["command"], str(cmd["target"]),
                            cmd.get("detail", ""), cmd.get("why", ""))
        record = {**cmd, "mode": decision.mode, "decided_by": decision.by}

        if not decision.allowed:
            record["status"] = "DENIED"
            ctx.log(f"  거부됨  {cmd['command']}({cmd['target']}) — 사람이 승인하지 않았습니다")
            results.append(record)
            continue

        try:
            record["result"] = _call(ctx.control, cmd)
            record["status"] = "EXECUTED"
            mark = "자동" if decision.mode == "AUTO" else "승인됨"
            ctx.log(f"  실행({mark})  {cmd['command']}({cmd['target']}) — {cmd.get('detail', '')}")
        except Exception as exc:                                   # noqa: BLE001
            record["status"] = "FAILED"
            record["error"] = f"{type(exc).__name__}: {exc}"
            ctx.log(f"  실패  {cmd['command']}({cmd['target']}) — {record['error']}")

        results.append(record)

    if not commands:
        ctx.log("  실행할 조치가 없습니다 (진단이 조치를 내지 않았습니다)")
    return results
