"""읽기 API — Day 1 부터 학생이 쓰는 면.

Day 1 Lab 1-1 Step 1 이 "제공 프롬프트 시드로 시뮬레이터 API를 읽어 대시보드 생성"
으로 시작하므로, 이 API 가 40분 안에 전원 성공을 좌우한다.
따라서 인증을 요구하지 않고 tenant_id 만으로 읽힌다(제어 API 만 키를 요구).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from .. import db
from ..config import get_layout, get_settings
from ..sim.runner import runner

router = APIRouter(prefix="/api/v1", tags=["read"])
UTC = timezone.utc


def _factory(tenant_id: str):
    f = runner.engine.factories.get(tenant_id)
    if f is None:
        raise HTTPException(
            status_code=404,
            detail=f"'{tenant_id}' 네임스페이스가 없습니다. /api/v1/tenants 에서 목록을 확인하세요.",
        )
    return f


@router.get("/health", summary="서버·러너 상태")
async def health() -> dict:
    s = get_settings()
    return {
        "status": "ok" if runner.stats["ticks"] > 0 else "starting",
        "tenants": len(runner.tenants),
        "tick_seconds": s.tick_seconds,
        "flush_seconds": s.flush_seconds,
        "retention_hours": s.retention_hours,
        "control_api_open": s.control_api_enabled,
        "clock": runner.clock_info(),
        "stats": runner.stats,
        "server_time": datetime.now(UTC).isoformat(),
    }


@router.get("/layout", summary="공장 배치도 (2D 뷰·경로 그래프)")
async def layout() -> dict:
    return get_layout()


@router.get("/tenants", summary="네임스페이스 목록")
async def tenants() -> dict:
    return {
        "count": len(runner.tenants),
        "tenants": [
            {
                "tenant_id": t["tenant_id"],
                "tenant_type": t["tenant_type"],
                "display_name": t["display_name"],
                "control_unlocked": t["control_unlocked"],
            }
            for t in runner.tenants.values()
        ],
    }


CONTROL_CHANNELS = [
    {"name": "set_equipment_speed", "label": "설비 속도 조절",
     "signature": "set_equipment_speed(id, rpm)"},
    {"name": "stop_equipment", "label": "설비 정지",
     "signature": "stop_equipment(id)"},
    {"name": "dispatch_robot", "label": "로봇 파견",
     "signature": "dispatch_robot(robot_id, target)"},
    {"name": "ack_alarm", "label": "알람 확인 처리",
     "signature": "ack_alarm(id)"},
]


def _control_info(tenant_id: str) -> dict:
    """제어 통로 4개의 존재와 잠금 상태.

    Day 1 강의 덱B 33장이 "명령을 넣는 통로가 네 개 준비돼 있다 / 그 네 개는
    오늘 열지 않는다"를 화면으로 보여줘야 해서 읽기 응답에 포함한다.
    잠겨 있어도 무엇이 있는지는 보인다 — 그게 그 장의 요지다.
    """
    t = runner.tenants.get(tenant_id) or {}
    unlocked = bool(get_settings().control_api_enabled or t.get("control_unlocked"))
    return {
        "unlocked": unlocked,
        "opens_on": "Day 4",
        "channels": CONTROL_CHANNELS,
    }


@router.get("/{tenant_id}/state", summary="공장 전체 스냅샷 — 폴링 1회로 전부")
async def state(tenant_id: str) -> dict:
    snap = _factory(tenant_id).snapshot(runner.virtual_now)
    snap["clock"] = runner.clock_info()
    snap["control"] = _control_info(tenant_id)
    return snap


@router.get("/{tenant_id}/equipment", summary="CNC 설비 6대 현재 상태")
async def equipment(tenant_id: str) -> dict:
    snap = _factory(tenant_id).snapshot(runner.virtual_now)
    return {"tenant_id": tenant_id, "equipment": snap["equipment"], "clock": runner.clock_info()}


@router.get("/{tenant_id}/equipment/{equipment_id}", summary="설비 1대 현재 상태")
async def equipment_one(tenant_id: str, equipment_id: str) -> dict:
    f = _factory(tenant_id)
    if equipment_id not in f.equipment:
        raise HTTPException(status_code=404, detail=f"설비 '{equipment_id}' 없음 (EQ-01~EQ-06)")
    snap = f.snapshot(runner.virtual_now)
    return next(e for e in snap["equipment"] if e["equipment_id"] == equipment_id)


@router.get("/{tenant_id}/robots", summary="AMR 2대 현재 상태")
async def robots(tenant_id: str) -> dict:
    snap = _factory(tenant_id).snapshot(runner.virtual_now)
    return {"tenant_id": tenant_id, "robots": snap["robots"], "clock": runner.clock_info()}


@router.get("/{tenant_id}/alarms", summary="알람 목록")
async def alarms(
    tenant_id: str,
    state: str = Query("OPEN", description="OPEN | ACKED | ALL"),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    _factory(tenant_id)
    where = ["tenant_id = $1"]
    args: list = [tenant_id]
    if state.upper() != "ALL":
        args.append(state.upper())
        where.append(f"state = ${len(args)}")
    args.append(limit)
    sql = (
        "select id, equipment_id, rule_code, severity, message, value, threshold, "
        "state, raised_at, acked_at, acked_by "
        f"from alarm where {' and '.join(where)} "
        f"order by raised_at desc limit ${len(args)}"
    )
    async with db.pool().acquire() as con:
        rows = await con.fetch(sql, *args)
    return {"tenant_id": tenant_id, "alarms": [dict(r) for r in rows]}


@router.get("/{tenant_id}/readings", summary="센서 이력 — 교안 부록 A 6컬럼")
async def readings(
    tenant_id: str,
    equipment_id: str | None = Query(None, description="비우면 전체 설비"),
    minutes: int = Query(
        30, ge=1, le=1440,
        description="최근 N분 — 실제 적재 시각 기준. 배속 x60 이면 가상 N시간분이 들어온다.",
    ),
    limit: int = Query(2000, ge=1, le=20000),
) -> dict:
    _factory(tenant_id)
    args: list = [tenant_id, minutes]
    cond = "tenant_id = $1 and ingested_at > now() - make_interval(mins => $2)"
    if equipment_id:
        args.append(equipment_id)
        cond += f" and equipment_id = ${len(args)}"
    args.append(limit)
    sql = (
        'select equipment_id, "timestamp", temperature, vibration, rpm, run_state '
        f'from sensor_readings where {cond} order by "timestamp" desc limit ${len(args)}'
    )
    async with db.pool().acquire() as con:
        rows = await con.fetch(sql, *args)
    return {
        "tenant_id": tenant_id,
        "columns": ["equipment_id", "timestamp", "temperature", "vibration", "rpm", "run_state"],
        "count": len(rows),
        "readings": [dict(r) for r in rows],
    }


@router.get("/{tenant_id}/maintenance", summary="정비 이력 (Lab 3-3 폴백용)")
async def maintenance(
    tenant_id: str,
    equipment_id: str | None = Query(None, description="비우면 전체 설비"),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """공용 정비 이력.

    Lab 3-3 Step 2 의 "해당 설비의 정비 이력을 조회해" 에 쓰인다.
    다만 **정본은 학생이 Day 2 에 만드는 정비 작업지시 테이블**이다.
    이쪽은 Day 2 를 못 끝낸 팀을 위한 폴백이며, 강사가 우회시킬 때만 쓴다.
    """
    _factory(tenant_id)
    args: list = [tenant_id]
    cond = "tenant_id = $1"
    if equipment_id:
        args.append(equipment_id)
        cond += f" and equipment_id = ${len(args)}"
    args.append(limit)
    sql = (
        "select equipment_id, work_order_no, issued_at, status, action, "
        "       technician, completed_at, note "
        f"from maintenance_log where {cond} order by issued_at desc limit ${len(args)}"
    )
    async with db.pool().acquire() as con:
        rows = await con.fetch(sql, *args)
    return {"tenant_id": tenant_id, "count": len(rows),
            "maintenance": [dict(r) for r in rows]}


@router.get("/{tenant_id}/robot-readings", summary="AMR 이동 이력")
async def robot_readings(
    tenant_id: str,
    robot_id: str | None = Query(None),
    minutes: int = Query(30, ge=1, le=1440),
    limit: int = Query(2000, ge=1, le=20000),
) -> dict:
    _factory(tenant_id)
    args: list = [tenant_id, minutes]
    cond = "tenant_id = $1 and ingested_at > now() - make_interval(mins => $2)"
    if robot_id:
        args.append(robot_id)
        cond += f" and robot_id = ${len(args)}"
    args.append(limit)
    sql = (
        'select robot_id, "timestamp", pos_x, pos_y, battery, payload_state, status '
        f'from robot_readings where {cond} order by "timestamp" desc limit ${len(args)}'
    )
    async with db.pool().acquire() as con:
        rows = await con.fetch(sql, *args)
    return {"tenant_id": tenant_id, "count": len(rows), "readings": [dict(r) for r in rows]}
