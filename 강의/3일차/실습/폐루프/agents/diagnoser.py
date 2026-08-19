"""진단 에이전트 — 폐루프의 두 번째 책임.

    "왜 그런가, 무엇을 해야 하는가"를 답한다. 직접 움직이지는 않는다.

감지가 넘긴 사실 + 그 설비의 정비 이력을 재료로 원인을 추정하고 조치를 제안합니다.
제안까지입니다. 실행은 조치 에이전트의 몫입니다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROLE = "진단"


class DiagnoseFailed(RuntimeError):
    """이번 회차의 AI 진단 호출이 실패했다 — 루프는 죽지 않고 다음 회차에 다시 건다.

    실패 안내(사람 말)는 이 예외를 던지기 전에 이미 화면에 냈다.
    loop.py 가 이 예외만 잡아서 회차를 넘긴다.
    """


def load_env_file() -> None:
    """`.env` 를 찾아 환경변수로 올린다 — 이미 설정된 값은 덮어쓰지 않는다.

    이 폴더부터 위로 올라가며 처음 만나는 `.env` 를 읽습니다.
    터미널마다 export 하지 않아도 되게 하는 것뿐이며, 다른 동작은 없습니다.

    주의 — `.env` 는 절대 저장소에 올리지 마십시오. 키가 평문으로 들어 있습니다.
    """
    here = Path(__file__).resolve()
    for folder in [here.parent, *here.parents]:
        path = folder / ".env"
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))
        return

# 진단 결과의 모양. 조치 에이전트가 이 모양을 기대합니다.
SCHEMA = {
    "type": "object",
    "properties": {
        "cause": {"type": "string", "description": "가장 그럴듯한 원인 한 문장"},
        "evidence": {"type": "array", "items": {"type": "string"},
                     "description": "그렇게 본 근거. 준 자료에서만 고를 것"},
        "severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string",
                             "enum": ["slow_down", "stop", "dispatch_robot", "ack_alarm", "none"]},
                    "equipment_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "rpm": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                    "robot_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "target": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "why": {"type": "string"},
                },
                # 구조화 출력은 모든 속성이 required 여야 한다. 없는 값은 null 로 낸다.
                "required": ["type", "equipment_id", "rpm", "robot_id", "target", "why"],
                "additionalProperties": False,
            },
        },
        "summary": {"type": "string", "description": "사람이 읽을 두세 문장"},
    },
    "required": ["cause", "evidence", "severity", "actions", "summary"],
    "additionalProperties": False,
}


# =============================================================================
# 재료 모으기 — 이미 되어 있습니다.
# =============================================================================
def gather(ctx, finding: dict) -> dict:
    """진단의 재료. 정비 이력의 note 와 미완 작업지시가 원인 추정의 실마리다."""
    eq = finding["equipment_id"]
    try:
        maint = ctx.api.maintenance(equipment_id=eq, limit=10)
    except Exception as exc:                                       # noqa: BLE001
        ctx.log(f"  정비 이력을 못 읽었습니다 — {type(exc).__name__}: {exc}")
        maint = []
    return {
        "finding": finding,
        "maintenance": maint,
        "open_work_orders": [m for m in maint if m.get("status") != "DONE"],
    }


# =============================================================================
# ★ 채우는 자리
# =============================================================================
def build_prompt(evidence: dict, cfg: dict) -> tuple[str, str]:
    """진단 에이전트에게 줄 지시문을 만든다.

    Args:
        evidence: gather() 가 모은 것 — finding, maintenance, open_work_orders
        cfg: config.json 의 act 블록 (감속 비율·최소 rpm·정비 로봇 이름)

    Returns:
        (system, user) 두 문자열

    ──────────────────────────────────────────────────────────────────
    호출·스키마·폴백은 이미 되어 있습니다. 지시문만 쓰면 됩니다.

    담아야 할 것은 네 가지입니다.
      1. 역할 — 공장 설비 진단자다. 조회한 사실만 쓰고 지어내지 않는다
      2. 재료 — evidence 를 사람이 읽을 수 있게 풀어 넣는다
               (정비 이력의 note 와 미완 작업지시를 빠뜨리지 말 것)
      3. 규칙 — 감속은 자동으로 실행되고, 정지와 로봇 파견은 사람 승인을 받는다.
               그러니 승인이 필요한 조치를 낼 때는 why 에 이유를 분명히 쓰게 한다
      4. 형태 — actions 에 쓸 수 있는 것: slow_down, stop, dispatch_robot,
               ack_alarm, none. slow_down 이면 rpm 을, dispatch_robot 이면
               robot_id 와 target 을 함께 낼 것

    ★ 여기서 대부분 한 번 막힙니다 — 「실행할 조치가 없습니다」

      감지는 드리프트를 **일찍** 잡으려고 상승폭이 작을 때 울립니다(+0.4℃).
      그 숫자만 던져 주면 모델은 "아직 별것 아니다"라며 severity 를 LOW 로 놓고
      조치를 하나도 안 냅니다. 실제로 그래서 폐루프가 안 닫힌 적이 있습니다.

      드리프트는 **지금 작아도 계속 오르는** 이상이라는 것을 지시문에 넣으십시오.
      2일차 에서 사람이 놓친 이유가 정확히 그것이었습니다.

    주의
      · 이 결과로 진짜 설비가 움직입니다. "추정"과 "확인된 사실"을 섞지 않게 하세요
      · 근거를 자료 밖에서 만들어 내면 진단이 아니라 창작입니다. 못 박아 두세요
      · 되돌릴 수 없는 조치(정지·파견)는 최소로. 라인을 다 세우는 진단은 좋지 않습니다
    ──────────────────────────────────────────────────────────────────
    """
    # ── 빈칸 3 ───────────────────────────────────────────────────────────────
    #   ★ AI 에게 주는 지시문. **세 문장**이 들어가야 오늘 볼 장면이 나온다.
    #
    #     ① 이 변화는 지금 작아도 계속 오른다 — 그렇게 보고 판단할 것
    #     ② 원인이 정비 보류·지연이면 감속과 **함께** 로봇 파견 요청까지 낼 것
    #     ③ 근거(evidence)에는 작업지시 번호를 그대로 인용할 것
    #
    #   ①이 빠지면 「아직 작으니 지켜보자」로 끝나고,
    #   ②가 빠지면 승인 화면이 안 뜨고, ③이 빠지면 근거에 번호가 안 붙는다.
    #   여러 줄로 쓰려면 따옴표 세 개(\"\"\" … \"\"\")로 감싼다.
    system = ...

    # 아래는 자료를 사람이 읽게 풀어 놓는 부분이다. 이미 다 돼 있다.
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
    return system, "\n".join(lines)


# =============================================================================
# 호출 — 이미 되어 있습니다. 고치지 않아도 됩니다.
# =============================================================================
def credentials(dcfg: dict) -> tuple[str, str] | None:
    """내 키로 직접 부를 수 있는지 본다 — 이번 특강에서는 쓰지 않는 예비 경로다.

    진단은 **공장 중계**로 확정돼 있습니다(`config.json` 의 `diagnose.backend`
    기본값이 `"server"`). 학생 코드에는 LLM 키를 두지 않습니다.
    이 함수는 강사가 공장 없이 확인할 때만 쓰입니다.
    키 이름은 config.json 의 openai_key_env 로 바꿀 수 있습니다.
    """
    load_env_file()
    name = dcfg.get("openai_key_env", "OPENAI_API_KEY")
    value = os.environ.get(name, "").strip()
    if value:
        return "openai", value
    return None


def _ask_openai(key: str, system: str, user: str, dcfg: dict) -> dict:
    """진단 모델 호출. 응답은 SCHEMA 대로만 옵니다(구조화 출력).

    추론(reasoning)은 꺼 둡니다. 실측으로 껐을 때가 더 좋았습니다 —
    실행 가능한 조치를 내는 비율 5/5 (켜면 4/5), 응답 2.9초 (켜면 4.1초).
    진단은 준 자료를 읽고 정리하는 일이라 긴 추론이 도움이 되지 않습니다.
    """
    from openai import OpenAI

    extra = {}
    effort = (dcfg.get("openai_reasoning_effort") or "").strip()
    if effort:
        extra["reasoning_effort"] = effort

    res = OpenAI(api_key=key).chat.completions.create(
        model=dcfg["openai_model"],
        max_completion_tokens=int(dcfg["max_tokens"]),
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "diagnosis", "strict": True,
                                         "schema": SCHEMA}},
        **extra,
    )
    choice = res.choices[0]
    if getattr(choice.message, "refusal", None):
        raise RuntimeError(f"모델이 응답을 거부했습니다: {choice.message.refusal}")
    return json.loads(choice.message.content)


def _ask_server(ctx, system: str, user: str, dcfg: dict) -> dict:
    """공장을 거쳐 진단한다 — 학생 코드에 LLM 키를 두지 않기 위한 것.

    공장에 붙으면 공장이 자기 열쇠로 모델을 부른다.
    프롬프트는 **내가 만든 것이 그대로** 올라간다. 공장은 중계만 한다.
    """
    import httpx

    api = ctx.api
    r = httpx.post(
        f"{api.base}/api/v1/{api.tenant}/diagnose",
        headers={"X-Access-Key": api.key},
        json={"system": system, "user": user, "schema": SCHEMA,
              "max_tokens": int(dcfg.get("max_tokens", 2000))},
        timeout=90,
    )
    if r.status_code == 429:
        raise RuntimeError("진단 호출이 1분 한도를 넘었습니다 — 잠시 뒤 다시 돕니다")
    r.raise_for_status()
    return r.json()


def _by_rules(evidence: dict, acfg: dict) -> dict:
    """규칙 기반 진단 — API 키가 없거나 호출이 실패했을 때의 안전망.

    시연·리허설이 키 하나 때문에 멈추지 않게 하는 장치입니다.
    폐루프가 도는 것 자체는 이쪽으로도 확인됩니다.
    """
    f = evidence["finding"]
    eq = f["equipment_id"]
    opens = evidence["open_work_orders"]
    rpm = f.get("current_rpm")

    cause = f"{eq} 온도가 기준 대비 {f.get('delta', 0):.1f}℃ 상승했습니다."
    ev = [f.get("detail", "")]
    if opens:
        o = opens[0]
        cause += f" 미완 정비 작업지시({o.get('work_order_no')})가 남아 있습니다."
        ev.append(f"{o.get('work_order_no')} {o.get('status')} — "
                  f"{o.get('action')} / {o.get('note') or '비고 없음'}")

    actions: list[dict] = []
    if rpm:
        target = max(float(acfg["min_rpm"]), round(float(rpm) * float(acfg["slow_down_ratio"])))
        actions.append({"type": "slow_down", "equipment_id": eq, "rpm": target,
                        "robot_id": None, "target": None,
                        "why": "온도는 회전수의 함수이므로 감속으로 상승을 먼저 꺾습니다."})
    if opens:
        actions.append({"type": "dispatch_robot", "equipment_id": eq,
                        "rpm": None, "robot_id": acfg["maintenance_robot"], "target": eq,
                        "why": "미완 정비 작업지시가 원인일 수 있어 현장 확인이 필요합니다."})

    return {
        "cause": cause,
        "evidence": [e for e in ev if e],
        "severity": "HIGH" if opens else "MEDIUM",
        "actions": actions,
        "summary": cause + " 감속으로 상승을 억제하고, 필요하면 정비 로봇을 보냅니다.",
        "backend": "rules",
    }


def run(ctx, finding: dict) -> dict:
    """감지 하나를 받아 진단 하나를 돌려준다."""
    from agents import 확인
    확인("build_prompt")   # 안 채웠으면 여기서 멈춘다 — 빈 지시문을 AI 에게 보내지 않는다

    evidence = gather(ctx, finding)
    dcfg = ctx.cfg["diagnose"]
    acfg = ctx.cfg["act"]

    # 지시문은 항상 만듭니다. 규칙으로 떨어져도 내가 쓴 지시문이 기록에 남습니다.
    system, user = build_prompt(evidence, acfg)

    backend = dcfg.get("backend", "server")

    # 기본 경로 — 공장 중계. 학생 코드에 키가 없어도 된다.
    if backend == "server":
        try:
            out = _ask_server(ctx, system, user, dcfg)
            out["backend"] = "server"
            out["prompt"] = user
            return out
        except Exception as exc:                                   # noqa: BLE001
            # 조용히 규칙으로 떨어지지 않는다. 그러면 학생은 자기가
            # **AI 진단을 못 봤다는 사실 자체를 모르고** 지나간다.
            # 그렇다고 루프를 죽이지도 않는다 — 다시 켜면 감지까지 또 몇 분을 기다린다.
            # 그래서 **감지 상태는 유지한 채 다음 회차에 자동으로 다시 건다.**
            ctx.진단실패 = getattr(ctx, "진단실패", 0) + 1
            ctx.log("")
            ctx.log(f"  AI 진단 실패 ({ctx.진단실패}회) — {type(exc).__name__}: {exc}")
            if ctx.진단실패 < 3:
                ctx.log("  다음 회차에 자동으로 다시 겁니다. 그대로 두세요.")
                ctx.log("  (감지는 그대로 살아 있어 처음부터 기다릴 필요가 없습니다)")
            else:
                ctx.log("  " + "=" * 56)
                ctx.log("  세 번 연속 실패했습니다 — 일시적인 문제가 아닙니다.")
                ctx.log("  손을 드세요. 오늘 봐야 할 장면이 여기입니다.")
                ctx.log("  (강사 안내가 있을 때만) 규칙으로 계속하려면 Ctrl+C 후:")
                ctx.log("      uv run loop.py --규칙으로")
                ctx.log("  " + "=" * 56)
            # 이 회차의 진단만 건너뛴다 — loop.py 가 이 예외를 잡아 다음 회차로 간다.
            raise DiagnoseFailed(f"{type(exc).__name__}: {exc}") from exc

    # 예비 경로 — 내 키로 직접. 이번 특강에서는 쓰지 않습니다(강사 확인용).
    if backend in ("openai", "auto"):
        provider, key = credentials(dcfg) or (None, None)
    else:                                     # "rules"
        provider, key = None, None

    if provider and key:
        try:
            out = _ask_openai(key, system, user, dcfg)
            out["backend"] = provider
            out["model"] = dcfg["openai_model"]
            out["prompt"] = user
            return out
        except Exception as exc:                                   # noqa: BLE001
            ctx.log(f"  진단 호출 실패({provider}) — {type(exc).__name__}: {exc} "
                    f"→ 규칙으로 대체합니다")

    out = _by_rules(evidence, acfg)
    out["prompt"] = user
    return out
