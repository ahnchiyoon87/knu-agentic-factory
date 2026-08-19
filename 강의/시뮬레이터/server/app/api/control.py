"""제어 API 4종 — 교안 3절 명시. 3일차 에서 MCP 도구로 노출된다.

    set_equipment_speed(id, rpm)   설비 속도 조절
    stop_equipment(id)             설비 정지
    dispatch_robot(robot_id, target)  로봇 파견
    ack_alarm(id)                  알람 확인 처리

교안상 2일차 에는 잠겨 있고, 3일차 아침 3일차준비.py 가 연다.

격리: 경로의 tenant_id 와 X-Access-Key 헤더가 일치해야만 실행된다.
      키가 맞아도 다른 테넌트의 공장은 건드릴 수 없다(경로가 곧 대상).
      모든 호출은 control_command 에 감사 로그로 남아 격리 검증의 증거가 된다.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from .. import db
from ..config import get_settings
from ..sim.runner import runner

router = APIRouter(prefix="/api/v1", tags=["control (3일차)"])
UTC = timezone.utc

COMMANDS = ("set_equipment_speed", "stop_equipment", "dispatch_robot", "ack_alarm")


# ----------------------------------------------------------------- 요청 모델
class SpeedReq(BaseModel):
    rpm: float = Field(..., ge=0, le=3000, description="목표 회전수")
    issued_by: str | None = Field(None, description="호출 주체(에이전트명 등)")


class StopReq(BaseModel):
    issued_by: str | None = None
    reason: str | None = None


class DispatchReq(BaseModel):
    target: str | dict = Field(
        ..., description="노드명(EQ-01~EQ-06, WH, DOCK, J1~J4, W-END) 또는 {\"x\":.., \"y\":..}"
    )
    issued_by: str | None = None


class AckReq(BaseModel):
    issued_by: str | None = None
    note: str | None = None


# ----------------------------------------------------------------- 공통 검사
def _tenant(tenant_id: str) -> dict:
    t = runner.tenants.get(tenant_id)
    if t is None:
        raise HTTPException(status_code=404, detail=f"'{tenant_id}' 네임스페이스가 없습니다.")
    return t


def _authorize(tenant_id: str, access_key: str | None) -> dict:
    t = _tenant(tenant_id)
    s = get_settings()

    if not (s.control_api_enabled or t["control_unlocked"]):
        raise HTTPException(
            status_code=403,
            # 이 문장은 **학생 화면**에 그대로 뜬다.
            # 학생이 스스로 할 수 있는 일만 적는다 — 개방은 강사만 할 수 있다.
            detail=(
                "제어 통로가 아직 잠겨 있습니다. 3일차 오후에 강사가 엽니다. "
                "이미 열렸어야 하는 시간이면 손을 드세요."
            ),
        )
    if not access_key or access_key != t["access_key"]:
        raise HTTPException(
            status_code=401,
            detail="X-Access-Key 헤더가 없거나 이 네임스페이스의 키와 다릅니다.",
        )
    return t


async def _log(tenant_id: str, command: str, target: str | None, params: dict,
               status: str, result: dict | None, issued_by: str | None) -> int:
    async with db.pool().acquire() as con:
        return await con.fetchval(
            """
            insert into control_command (tenant_id, command, target, params,
                                         status, result, issued_by)
            values ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7)
            returning id
            """,
            tenant_id, command, target, json.dumps(params, ensure_ascii=False),
            status, json.dumps(result or {}, ensure_ascii=False), issued_by,
        )


def _needs_approval(command: str) -> bool:
    """HITL — 교안 3일차 10~11장.

    되돌릴 수 없는 행동(정지·로봇 파견)에 승인 관문을 둘 수 있다.
    기본은 비활성이며, 승인 관문은 학생이 만드는 오케스트레이터(폐루프)에 두는 것이 교안의 설계다.
    시뮬레이터 쪽에서 강제하고 싶을 때만 HITL_REQUIRED_COMMANDS 로 켠다.
    """
    return command in get_settings().hitl_commands


# ----------------------------------------------------------------- 1. 속도 조절
@router.post("/{tenant_id}/control/set_equipment_speed/{equipment_id}",
             summary="set_equipment_speed(id, rpm) — 설비 속도 조절")
async def set_equipment_speed(
    tenant_id: str, equipment_id: str, req: SpeedReq,
    x_access_key: str | None = Header(None, alias="X-Access-Key"),
) -> dict:
    _authorize(tenant_id, x_access_key)
    f = runner.engine.factories[tenant_id]
    if equipment_id not in f.equipment:
        raise HTTPException(status_code=404, detail=f"설비 '{equipment_id}' 없음 (EQ-01~EQ-06)")

    params = {"rpm": req.rpm}
    if _needs_approval("set_equipment_speed"):
        cid = await _log(tenant_id, "set_equipment_speed", equipment_id, params,
                         "PENDING", None, req.issued_by)
        return {"status": "PENDING", "command_id": cid,
                "message": "승인 대기 — /control/commands/{id}/approve 로 승인하세요."}

    result = f.set_speed(equipment_id, req.rpm)
    cid = await _log(tenant_id, "set_equipment_speed", equipment_id, params,
                     "EXECUTED", result, req.issued_by)
    return {"status": "EXECUTED", "command_id": cid, **result}


# ----------------------------------------------------------------- 2. 정지
@router.post("/{tenant_id}/control/stop_equipment/{equipment_id}",
             summary="stop_equipment(id) — 설비 정지")
async def stop_equipment(
    tenant_id: str, equipment_id: str, req: StopReq | None = None,
    x_access_key: str | None = Header(None, alias="X-Access-Key"),
) -> dict:
    _authorize(tenant_id, x_access_key)
    req = req or StopReq()
    f = runner.engine.factories[tenant_id]
    if equipment_id not in f.equipment:
        raise HTTPException(status_code=404, detail=f"설비 '{equipment_id}' 없음 (EQ-01~EQ-06)")

    params = {"reason": req.reason}
    if _needs_approval("stop_equipment"):
        cid = await _log(tenant_id, "stop_equipment", equipment_id, params,
                         "PENDING", None, req.issued_by)
        return {"status": "PENDING", "command_id": cid,
                "message": "승인 대기 — 정지는 되돌릴 수 없는 행동입니다(HITL)."}

    result = f.stop(equipment_id)
    cid = await _log(tenant_id, "stop_equipment", equipment_id, params,
                     "EXECUTED", result, req.issued_by)
    return {"status": "EXECUTED", "command_id": cid, **result}


# ----------------------------------------------------------------- 3. 로봇 파견
@router.post("/{tenant_id}/control/dispatch_robot/{robot_id}",
             summary="dispatch_robot(robot_id, target) — 로봇 파견")
async def dispatch_robot(
    tenant_id: str, robot_id: str, req: DispatchReq,
    x_access_key: str | None = Header(None, alias="X-Access-Key"),
) -> dict:
    _authorize(tenant_id, x_access_key)
    f = runner.engine.factories[tenant_id]
    if robot_id not in f.robots:
        raise HTTPException(status_code=404, detail=f"로봇 '{robot_id}' 없음 (AMR-01, AMR-02)")

    params = {"target": req.target}
    if _needs_approval("dispatch_robot"):
        cid = await _log(tenant_id, "dispatch_robot", robot_id, params,
                         "PENDING", None, req.issued_by)
        return {"status": "PENDING", "command_id": cid,
                "message": "승인 대기 — 로봇 파견은 되돌릴 수 없는 행동입니다(HITL)."}

    try:
        result = f.dispatch(robot_id, req.target)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cid = await _log(tenant_id, "dispatch_robot", robot_id, params,
                     "EXECUTED", result, req.issued_by)
    return {"status": "EXECUTED", "command_id": cid, **result}


# ----------------------------------------------------------------- 4. 알람 확인
@router.post("/{tenant_id}/control/ack_alarm/{alarm_id}",
             summary="ack_alarm(id) — 알람 확인 처리")
async def ack_alarm(
    tenant_id: str, alarm_id: int, req: AckReq | None = None,
    x_access_key: str | None = Header(None, alias="X-Access-Key"),
) -> dict:
    _authorize(tenant_id, x_access_key)
    req = req or AckReq()

    async with db.pool().acquire() as con:
        row = await con.fetchrow(
            "update alarm set state='ACKED', acked_at=now(), acked_by=$3 "
            "where id=$1 and tenant_id=$2 and state='OPEN' "
            "returning id, equipment_id, rule_code, state",
            alarm_id, tenant_id, req.issued_by or "unknown",
        )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"알람 {alarm_id} 가 이 네임스페이스에 없거나 이미 처리됐습니다.",
        )

    f = runner.engine.factories[tenant_id]
    for a in f.alarms.values():
        if a.db_id == alarm_id and a.state == "OPEN":
            a.state = "ACKED"

    result = dict(row)
    cid = await _log(tenant_id, "ack_alarm", str(alarm_id), {"note": req.note},
                     "EXECUTED", result, req.issued_by)
    return {"status": "EXECUTED", "command_id": cid, **result}


# ----------------------------------------------------------------- 감사 로그
@router.get("/{tenant_id}/control/commands", summary="제어 명령 이력 (격리 검증 증거)")
async def commands(
    tenant_id: str,
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """읽기는 키를 요구하지 않는다 — 실수가 아니라 결정이다.

    쓰기(제어 4종)는 `X-Access-Key` 가 있어야 하지만, 이력 조회는 상태 조회와
    같은 급으로 연다. 담기는 것이 명령 이름·대상·rpm 뿐이라 남이 봐도 잃을 것이
    없고, 이 창구를 잠그면 `verify_lab.py`·`리허설.py`·`isolation_test.py` 가
    전부 키를 들고 다녀야 해서 검증 하네스가 무거워진다.
    비밀값(접속 키·토큰)은 여기 실리지 않는다.
    """
    _tenant(tenant_id)
    async with db.pool().acquire() as con:
        rows = await con.fetch(
            "select id, command, target, params, status, result, issued_by, issued_at "
            "from control_command where tenant_id=$1 order by issued_at desc limit $2",
            tenant_id, limit,
        )
    return {"tenant_id": tenant_id, "commands": [dict(r) for r in rows]}


@router.post("/{tenant_id}/control/commands/{command_id}/approve",
             summary="HITL 승인 — PENDING 명령을 실제로 실행")
async def approve(
    tenant_id: str, command_id: int, decided_by: str = Query("operator"),
    x_access_key: str | None = Header(None, alias="X-Access-Key"),
) -> dict:
    _authorize(tenant_id, x_access_key)
    async with db.pool().acquire() as con:
        row = await con.fetchrow(
            "select id, command, target, params from control_command "
            "where id=$1 and tenant_id=$2 and status='PENDING'",
            command_id, tenant_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail=f"승인 대기 중인 명령 {command_id} 없음")

    f = runner.engine.factories[tenant_id]
    params = row["params"]
    if isinstance(params, str):
        params = json.loads(params)

    if row["command"] == "set_equipment_speed":
        result = f.set_speed(row["target"], float(params["rpm"]))
    elif row["command"] == "stop_equipment":
        result = f.stop(row["target"])
    elif row["command"] == "dispatch_robot":
        result = f.dispatch(row["target"], params["target"])
    else:
        raise HTTPException(status_code=400, detail=f"승인 대상이 아닌 명령: {row['command']}")

    async with db.pool().acquire() as con:
        await con.execute(
            "update control_command set status='EXECUTED', result=$2::jsonb, "
            "decided_at=now(), decided_by=$3 where id=$1",
            command_id, json.dumps(result, ensure_ascii=False), decided_by,
        )
    return {"status": "EXECUTED", "command_id": command_id,
            "decided_at": datetime.now(UTC).isoformat(), **result}
