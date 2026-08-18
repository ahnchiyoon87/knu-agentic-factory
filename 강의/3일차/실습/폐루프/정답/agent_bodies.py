"""3일차 오후 참고 답안 — `--정답` 가 읽는 완성본.

★ 세 자리에 들어갈 **본문만** 담았습니다. 템플릿 전체를 복사해 두면
원본과 어긋나므로 본문만 둡니다.

시간이 다 된 학생의 `loop.py --정답` 가 막힌 자리 하나만 이 본문으로 채웁니다.
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


import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.actuator import COMMAND_OF  # noqa: E402


# =============================================================================
# ★1 감지 — agents/detector.py 의 judge()
# =============================================================================
def judge(values: list[float | None], cfg: dict) -> dict | None:
    vals = [v for v in values if v is not None]

    # 최근 것만 본다. 안 자르면 신호가 +1.2℃ 에서 +0.5℃ 로 흐려지고(임계 0.4 를 겨우 넘는다),
    # **이상이 끝나 온도가 내려간 뒤에도 그 구간이 창에 남아 계속 울린다**(실측: 300분 뒤 +0.52℃).
    # 그러면 감속이 먹혔는지를 화면에서 확인할 수 없다.
    cap = int(cfg.get("window_samples", 300)) * 2
    vals = vals[-cap:]

    if len(vals) < int(cfg["min_samples"]):
        return None

    # 창 안이 아니라 창 밖과 비교한다.
    # 드리프트는 창까지 같이 올라가므로 z-score 로는 잡히지 않는다(2일차의 결론).
    half = len(vals) // 2
    baseline = sum(vals[:half]) / half
    recent = sum(vals[half:]) / (len(vals) - half)
    delta = recent - baseline

    if delta < float(cfg["drift_delta_c"]):
        return None                      # 내려가는 것은 이상이 아니다. 조치가 먹힌 것이다

    return {
        "kind": "DRIFT",
        "delta": round(delta, 2),
        "recent": round(recent, 2),
        "baseline": round(baseline, 2),
        "detail": f"최근 {recent:.1f}℃ (기준 {baseline:.1f}℃, +{delta:.1f}℃ 상승)",
    }


# =============================================================================
# ★2 진단 — agents/diagnoser.py 의 build_prompt()
# =============================================================================
SYSTEM = """당신은 CNC 공장의 설비 진단자입니다.

주어진 자료만 근거로 씁니다. 자료에 없는 수치·부품명·이력을 만들어 내지 마십시오.
확인된 사실과 추정을 섞지 말고, 추정이면 추정이라고 쓰십시오.

■ 드리프트(DRIFT)를 다룰 때 반드시 알아 둘 것

  드리프트는 **지금 값이 작아 보여도 계속 오르는** 이상입니다.
  감지된 시점의 상승폭은 초기값일 뿐이고, 방치하면 몇 시간에 걸쳐 계속 올라갑니다.
  "아직 작으니 지켜보자"는 이 이상에서 가장 나쁜 판단입니다 —
  사람이 그렇게 놓쳐 온 것을 잡으려고 당신이 있는 것입니다.

  그러므로 **DRIFT 가 감지되면 상승폭이 작더라도 최소 한 가지 실제 조치를 내십시오.**
  가장 안전한 첫 조치는 감속(slow_down)입니다 — 온도는 회전수의 함수라 즉시 효과가 있고,
  되돌리기도 쉽습니다. 조치 없이 none 만 내지 마십시오.

■ 정비 로봇 파견(dispatch_robot)을 함께 요청해야 하는 경우

  추정 원인이 설비의 정비 문제일 때 — 예: 점검이 보류·지연 중이거나, 미완 작업지시가
  물려 있을 때 — 감속만으로는 원인이 해소되지 않습니다. 이때는 감속과 **함께**
  dispatch_robot 파견 요청까지 내십시오. 파견은 사람이 승인해야 실행되므로 요청을
  망설일 이유가 없습니다 — 요청하지 않으면 사람은 판단할 기회조차 얻지 못합니다.

■ 근거를 적는 법

  근거(evidence)에는 **작업지시 번호를 그대로 인용**할 것.
  원인을 맞게 짚어도 번호를 안 적으면 사람이 어느 작업지시를 말하는지 찾아야 합니다.
  (이 한 줄이 없으면 인용률이 약 95% 로 떨어진다는 것을 39명 실측에서 확인했습니다)

■ 당신이 낸 조치는 실제 설비에 실행됩니다

  · 감속(slow_down)은 사람 확인 없이 바로 실행됩니다.
  · 정지(stop)와 로봇 파견(dispatch_robot)은 사람이 승인해야 실행됩니다.
    승인하는 사람이 판단할 수 있도록 why 에 이유를 분명히 쓰십시오.

  되돌릴 수 없는 조치는 최소로 냅니다. 상승폭이 작은데 라인을 세우는 진단은 좋지 않습니다.
  근거가 부족하면 severity 를 낮추되, **조치를 비우지는 마십시오.**"""


def build_prompt(evidence: dict, cfg: dict) -> tuple[str, str]:
    f = evidence["finding"]
    lines = [
        "# 감지된 이상",
        f"설비: {f['equipment_id']}",
        f"지표: {f.get('metric')}  종류: {f.get('kind')}",
        f"내용: {f.get('detail')}",
        f"현재 회전수: {f.get('current_rpm')} rpm   운전 상태: {f.get('run_state')}",
        f"표본 수: {f.get('sample_count')}",
        "",
        "# 이 설비의 정비 이력",
    ]
    if evidence["maintenance"]:
        for m in evidence["maintenance"]:
            lines.append(
                f"- {m.get('work_order_no')} [{m.get('status')}] {m.get('issued_at')} "
                f"{m.get('action')} / 비고: {m.get('note') or '없음'}"
            )
    else:
        lines.append("- 없음")

    lines += ["", "# 아직 끝나지 않은 작업지시"]
    if evidence["open_work_orders"]:
        for m in evidence["open_work_orders"]:
            lines.append(
                f"- {m.get('work_order_no')} [{m.get('status')}] {m.get('action')} "
                f"/ 비고: {m.get('note') or '없음'}"
            )
    else:
        lines.append("- 없음")

    lines += [
        "",
        "# 쓸 수 있는 조치",
        f"- slow_down      감속. rpm 을 함께 낼 것 (권장: 현재의 {cfg['slow_down_ratio']}배, "
        f"{cfg['min_rpm']} rpm 미만은 불가)",
        "- stop           정지. 사람 승인 필요",
        f"- dispatch_robot 로봇 파견. robot_id 와 target(설비ID)을 함께 낼 것 "
        f"(정비 로봇: {cfg['maintenance_robot']}). 사람 승인 필요",
        "- ack_alarm      알람 확인 처리",
        "- none           할 조치 없음",
        "",
        "위 자료로 원인을 추정하고 조치를 제안하십시오.",
    ]
    return SYSTEM, "\n".join(lines)


# =============================================================================
# ★3 조치 — agents/actuator.py 의 to_commands()
# =============================================================================
def to_commands(diagnosis: dict, finding: dict, cfg: dict) -> list[dict]:
    eq = finding["equipment_id"]
    actions = diagnosis.get("actions") or []
    kinds = {a.get("type") for a in actions}
    cmds: list[dict] = []

    for a in actions:
        kind = a.get("type")
        if not kind or kind == "none":
            continue
        # 정지가 함께 나왔으면 감속은 의미가 없다. 정지만 남긴다.
        if kind == "slow_down" and "stop" in kinds:
            continue

        name = COMMAND_OF.get(kind)
        if name is None:
            continue                      # 진단이 모르는 조치를 냈다. 버린다
        why = a.get("why", "")

        if name == "set_equipment_speed":
            target_eq = a.get("equipment_id") or eq
            rpm = a.get("rpm")
            if rpm is None:
                current = finding.get("current_rpm")
                if not current:
                    continue              # 기준 삼을 rpm 이 없다
                rpm = float(current) * float(cfg["slow_down_ratio"])
            rpm = max(float(cfg["min_rpm"]), round(float(rpm)))
            current = finding.get("current_rpm")
            detail = (f"{float(current):.0f} → {rpm:.0f} rpm" if current
                      else f"{rpm:.0f} rpm 으로 조정")
            cmds.append({"command": name, "target": target_eq,
                         "args": {"rpm": rpm}, "detail": detail, "why": why})

        elif name == "stop_equipment":
            cmds.append({"command": name, "target": a.get("equipment_id") or eq,
                         "args": {"reason": why},
                         "detail": "라인 정지 — 되돌리려면 다시 기동해야 합니다",
                         "why": why})

        elif name == "dispatch_robot":
            robot = a.get("robot_id") or cfg["maintenance_robot"]
            target = a.get("target") or a.get("equipment_id") or eq
            cmds.append({"command": name, "target": robot,
                         "args": {"target": target},
                         "detail": f"{robot} → {target} 로 이동",
                         "why": why})

        elif name == "ack_alarm":
            alarm_id = a.get("target")
            if alarm_id is None:
                continue
            cmds.append({"command": name, "target": alarm_id,
                         "args": {"note": why},
                         "detail": f"알람 {alarm_id} 확인 처리", "why": why})

    return cmds


# =============================================================================
# 템플릿에 꽂아 넣기 — 검증·시연에서 씁니다
# =============================================================================
def install() -> None:
    """참고 답안을 템플릿 모듈에 주입한다 — 셋 다."""
    from agents import actuator, detector, diagnoser
    detector.judge = judge
    diagnoser.build_prompt = build_prompt
    actuator.to_commands = to_commands


# 학생이 막혔을 때 여는 것 — 막힌 자리 **하나만** 채운다.
# 나머지는 학생이 쓴 것 그대로 돈다. 2일차 `점검.py --정답` 와 같은 규칙이다.
ONE = {
    1: ("judge", "agents/detector.py", "감지"),
    2: ("build_prompt", "agents/diagnoser.py", "진단"),
    3: ("to_commands", "agents/actuator.py", "조치"),
}


def install_one(n: int) -> tuple[str, str, str]:
    """n 번 자리 하나만 참고 답안으로 채운다. (함수, 파일, 역할) 을 돌려준다."""
    from agents import actuator, detector, diagnoser
    이름, 파일, 역할 = ONE[n]
    {1: lambda: setattr(detector, "judge", judge),
     2: lambda: setattr(diagnoser, "build_prompt", build_prompt),
     3: lambda: setattr(actuator, "to_commands", to_commands)}[n]()
    return 이름, 파일, 역할


if __name__ == "__main__":
    install()
    print(json.dumps({"installed": ["judge", "build_prompt", "to_commands"]},
                     ensure_ascii=False))
