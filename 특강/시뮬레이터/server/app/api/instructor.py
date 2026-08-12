"""강사 콘솔 API — 교안 3절 「시나리오 주입」.

이상 이벤트 3종을 원하는 시점에 발생시킨다.
  · temp_drift       온도 드리프트 (서서히 상승)
  · vibration_spike  진동 스파이크 (순간적으로 튐)
  · sensor_dropout   센서 결측 (값이 안 들어옴)

전부 X-Instructor-Token 헤더가 필요하다.
tenant_id 에 '*' 를 주면 전 테넌트에 동시 주입된다(1일차 실습 Step 2 처럼
강사가 한 번에 쏴 주는 상황).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from .. import db
from ..config import get_profile, get_settings
from ..sim.engine import Injection, default_end
from ..sim.runner import runner

router = APIRouter(prefix="/api/instructor", tags=["instructor"])
UTC = timezone.utc

KINDS = ("temp_drift", "vibration_spike", "sensor_dropout")


def _auth(token: str | None) -> None:
    if not token or token != get_settings().instructor_token:
        raise HTTPException(status_code=401, detail="X-Instructor-Token 이 없거나 틀립니다.")


class InjectReq(BaseModel):
    tenant_id: str = Field("*", description="'*' 이면 전 테넌트 일괄")
    equipment_id: str | None = Field(None, description="비우면 이상 종류별 기본 설비")
    kind: str = Field(..., description="temp_drift | vibration_spike | sensor_dropout")
    params: dict = Field(default_factory=dict, description="비운 항목은 sim_profile.json 기본값")
    delay_seconds: float = Field(0, ge=0, description="지금부터 N초 뒤 시작")


def _warnings() -> list[dict]:
    """강사가 잊기 쉬운 조합을 콘솔이 대신 기억한다.

    2일차 는 제어를 개방한 상태로 진행하는데, 이때 배속이 1이면
    4시간짜리 온도 드리프트가 실제로 4시간 걸린다.
    학생 코드가 맞아도 「감지 이상 없음」만 나오고, 학생은 자기 탓인 줄 안다.
    배속은 교안에 없는 항목이라 교안이 알려주지 않는다 — 그래서 여기서 세운다.
    """
    out: list[dict] = []

    # ★ 학생이 아예 못 붙는 상태 — 강사 본인 화면은 멀쩡해서 혼자서는 절대 못 본다.
    #   실제로 .env 의 HOST 가 127.0.0.1 인 채로 남아 있던 적이 있다.
    호스트 = get_settings().host
    if 호스트 in ("127.0.0.1", "localhost", "::1"):
        out.append({
            "code": "학생이_못_붙음",
            "message": (
                f"서버가 {호스트} 에만 열려 있습니다. 강사 PC 에서만 보이고 "
                "학생 39명은 전부 「연결 실패」가 납니다."
            ),
            "fix": ".env 의 HOST 를 0.0.0.0 으로 바꾸고 서버를 다시 켜세요.",
        })

    # 개인 단위 특강인데 팀 네임스페이스가 살아 있으면 번호 배정이 어긋난다
    팀 = [t for t in runner.tenants.values() if t.get("tenant_type") == "team"]
    if 팀:
        out.append({
            "code": "팀_네임스페이스_있음",
            "message": f"팀 네임스페이스가 {len(팀)}개 떠 있습니다. 이번 특강은 개인 단위입니다.",
            "fix": ".env 의 TENANT_MODE 를 individual 로 두고 서버를 다시 켜세요.",
        })

    unlocked = [t for t in runner.tenants.values() if t.get("control_unlocked")]
    if unlocked and runner.time_scale < 2:
        out.append({
            "code": "DAY2_SCALE_IS_1",
            "message": (
                f"제어를 개방한 네임스페이스가 {len(unlocked)}개인데 배속이 x{runner.time_scale:g} 입니다. "
                "이 상태로는 온도 드리프트가 실제로 4시간 걸려 학생 화면에 아무것도 안 뜹니다."
            ),
            "fix": "POST /api/instructor/time-scale?scale=120",
        })
    active = [i for i in runner.engine.injections.values() if i.active]
    if unlocked and not active:
        out.append({
            "code": "DAY2_NO_INJECTION",
            "message": "제어는 열렸는데 진행 중인 이상 주입이 없습니다. 학생은 감지할 대상이 없습니다.",
            "fix": "POST /api/instructor/inject  {\"kind\": \"temp_drift\", \"equipment_id\": \"EQ-03\"}",
        })
    return out


@router.get("/status", summary="러너 상태 · 지표")
async def status(x_instructor_token: str | None = Header(None, alias="X-Instructor-Token")) -> dict:
    _auth(x_instructor_token)
    s = get_settings()
    return {
        "warnings": _warnings(),
        "settings": s.masked(),
        "clock": runner.clock_info(),
        "stats": runner.stats,
        "tenants": len(runner.tenants),
        "active_injections": [
            {
                "id": i.id, "tenant_id": i.tenant_id, "equipment_id": i.equipment_id,
                "kind": i.kind, "params": i.params,
                "starts_at": i.starts_at.isoformat(),
                "ends_at": i.ends_at.isoformat() if i.ends_at else None,
            }
            for i in runner.engine.injections.values() if i.active
        ],
        "server_time": datetime.now(UTC).isoformat(),
    }


@router.get("/tenants", summary="네임스페이스 목록 (제어 개방 상태 포함)")
async def tenants(x_instructor_token: str | None = Header(None, alias="X-Instructor-Token")) -> dict:
    _auth(x_instructor_token)
    async with db.pool().acquire() as con:
        rows = await con.fetch(
            "select t.tenant_id, t.tenant_type, t.display_name, t.control_unlocked, t.active, "
            "       t.access_key, "
            "       coalesce(string_agg(m.team_tenant_id, ',' order by m.team_tenant_id), '') as teams "
            "from tenant t left join tenant_member m on m.student_tenant_id = t.tenant_id "
            "group by t.tenant_id order by t.tenant_type desc, t.tenant_id"
        )
    return {"tenants": [dict(r) for r in rows]}


@router.post("/time-scale", summary="배속 변경 — 라이브 시연용 가상 시계")
async def time_scale(
    scale: float = Query(..., ge=1, le=240, description="1 | 60 | 80 | 120"),
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    """기울기가 아니라 시계를 가속한다.

    드리프트 기울기를 키우면 샘플당 상승폭이 커져 이상감지가 쉽게 잡는다.
    그러면 1일차의 "드리프트는 이동평균이 적응해 미탐된다"와 모순되고,
    1일차의 "사람이 못 알아챌 만큼 미묘하다"도 무너진다.

    배속은 1분 간격 가상 샘플을 그대로 둔 채 그 샘플을 더 빨리 내보낼 뿐이라
    샘플당 상승폭이 7일치 CSV 와 동일하게 유지된다(0.5℃/h → 0.00833℃/샘플).
    """
    _auth(x_instructor_token)
    info = runner.set_time_scale(scale)
    info["drift_per_sample_c"] = round(0.5 * info["virtual_step_seconds"] / 3600, 6)
    info["four_hours_takes_real_minutes"] = round(4 * 3600 / max(1.0, scale) / 60, 2)
    return info


@router.get("/presets", summary="강사 콘솔 프리셋 (sim_profile.json)")
async def presets(
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    _auth(x_instructor_token)
    profile = get_profile()
    return {
        "presets": {k: v for k, v in profile.get("presets", {}).items()
                    if not k.startswith("_")},
        "defaults": profile["anomaly_defaults"],
        "clock": {**profile.get("clock", {}), **runner.clock_info()},
    }


@router.post("/inject", summary="이상 주입 — 3종")
async def inject(
    req: InjectReq,
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    _auth(x_instructor_token)
    if req.kind not in KINDS:
        raise HTTPException(status_code=400, detail=f"kind 는 {KINDS} 중 하나여야 합니다.")
    if req.tenant_id != "*" and req.tenant_id not in runner.tenants:
        raise HTTPException(status_code=404, detail=f"'{req.tenant_id}' 네임스페이스 없음")

    profile = get_profile()
    defaults = dict(profile["anomaly_defaults"][req.kind])
    equipment_id = req.equipment_id or defaults.get("target_equipment")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id 를 정할 수 없습니다.")

    params = {k: v for k, v in defaults.items()
              if not k.startswith("_") and k != "target_equipment"}
    params.update({k: v for k, v in req.params.items() if v is not None})

    # 주입 시각은 공장의 시계(가상) 기준이다. 강사는 "N초 뒤"를 실제 시간으로 생각하므로
    # 배속을 곱해 가상 시간으로 환산한다.
    starts_at = runner.virtual_now + timedelta(
        seconds=(req.delay_seconds or 0) * max(1.0, runner.time_scale)
    )
    ends_at = default_end(req.kind, params, starts_at, profile)

    async with db.pool().acquire() as con:
        row = await con.fetchrow(
            """
            insert into anomaly_injection (tenant_id, equipment_id, kind, params,
                                           starts_at, ends_at, created_by)
            values ($1, $2, $3, $4::jsonb, $5, $6, 'instructor-console')
            returning id
            """,
            req.tenant_id, equipment_id, req.kind,
            json.dumps(params, ensure_ascii=False), starts_at, ends_at,
        )

    runner.engine.injections[row["id"]] = Injection(
        id=row["id"], tenant_id=req.tenant_id, equipment_id=equipment_id,
        kind=req.kind, params=params, starts_at=starts_at, ends_at=ends_at,
    )
    # 지속시간은 가상 시간 기준이다. 배속이 걸려 있으면 실제로는 그만큼 빨리 끝난다.
    # 강사가 "왜 벌써 끝났지?" 하지 않도록 실제 시간을 같이 돌려준다.
    scale = max(1.0, runner.time_scale)
    lasts_virtual = (ends_at - starts_at).total_seconds() if ends_at else None
    return {
        "id": row["id"], "tenant_id": req.tenant_id, "equipment_id": equipment_id,
        "kind": req.kind, "params": params,
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat() if ends_at else None,
        "time_scale": runner.time_scale,
        "lasts_virtual_seconds": lasts_virtual,
        "lasts_real_seconds": round(lasts_virtual / scale, 1) if lasts_virtual else None,
        "note": (
            f"지속시간은 가상 시간 기준입니다. 배속 x{runner.time_scale:g} 이므로 "
            f"실제로는 약 {lasts_virtual / scale / 60:.1f}분 뒤 끝납니다."
            if lasts_virtual else "종료 시각이 없는 주입입니다(수동 중단 필요)."
        ),
    }


@router.delete("/inject/{injection_id}", summary="주입 즉시 중단")
async def stop_injection(
    injection_id: int,
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    _auth(x_instructor_token)
    inj = runner.engine.injections.get(injection_id)
    if inj is None:
        raise HTTPException(status_code=404, detail=f"주입 {injection_id} 없음")
    inj.active = False
    async with db.pool().acquire() as con:
        await con.execute(
            "update anomaly_injection set active=false, ends_at=$2 where id=$1",
            injection_id, runner.virtual_now,
        )
    return {"id": injection_id, "active": False}


@router.delete("/inject", summary="모든 주입 중단")
async def stop_all(
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    _auth(x_instructor_token)
    n = 0
    for inj in runner.engine.injections.values():
        if inj.active:
            inj.active = False
            n += 1
    async with db.pool().acquire() as con:
        await con.execute(
            "update anomaly_injection set active=false, ends_at=$1 where active",
            runner.virtual_now,
        )
    return {"stopped": n}


@router.post("/control-lock", summary="제어 API 개방/잠금 — 교안상 2일차에 개방")
async def control_lock(
    unlocked: bool = Query(..., description="true=개방, false=잠금"),
    tenant_id: str = Query("*", description="'*' 이면 전체"),
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    _auth(x_instructor_token)
    async with db.pool().acquire() as con:
        if tenant_id == "*":
            await con.execute("update tenant set control_unlocked=$1", unlocked)
        else:
            await con.execute(
                "update tenant set control_unlocked=$1 where tenant_id=$2", unlocked, tenant_id
            )
        rows = await con.fetch(
            "select tenant_id, tenant_type, display_name, access_key, control_unlocked "
            "from tenant where active order by tenant_id"
        )
    for r in rows:
        if r["tenant_id"] in runner.tenants:
            runner.tenants[r["tenant_id"]] = dict(r)
    return {"tenant_id": tenant_id, "control_unlocked": unlocked}


@router.post("/reset", summary="테넌트 초기화 — 이력·알람·명령·주입 삭제 후 상태 재생성")
async def reset(
    tenant_id: str = Query(...),
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    _auth(x_instructor_token)
    if tenant_id not in runner.tenants:
        raise HTTPException(status_code=404, detail=f"'{tenant_id}' 네임스페이스 없음")
    async with db.pool().acquire() as con:
        await con.execute("select reset_tenant($1)", tenant_id)
    for iid, inj in list(runner.engine.injections.items()):
        if inj.tenant_id == tenant_id:
            runner.engine.injections.pop(iid)
    runner.engine.drop_tenant(tenant_id)
    runner.engine.ensure_tenant(tenant_id)
    return {"tenant_id": tenant_id, "reset": True}


@router.post("/unclaim", summary="자리 배정 회수 — 노트북을 바꿔 온 학생이 생겼을 때")
async def 배정풀기(
    tenant_id: str = Query(..., description="풀어 줄 번호 (예: S07). '*' 이면 전체"),
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    """그 번호를 다시 「안 쓰는 것」으로 되돌린다.

    쓰는 때 — 학생이 노트북을 바꿔 와서 새 번호를 받아 버렸을 때,
    옛 번호를 풀어 주면 다음 학생이 그것을 받는다.
    """
    _auth(x_instructor_token)
    from .claim import _lock, _장부쓰기, _장부읽기

    with _lock:
        장부 = _장부읽기()
        if tenant_id == "*":
            푼것 = sorted({v["tenant_id"] for v in 장부.values()})
            _장부쓰기({})
            return {"푼_번호": 푼것, "남은_배정": 0}
        지문 = [fp for fp, v in 장부.items() if v.get("tenant_id") == tenant_id]
        if not 지문:
            raise HTTPException(404, f"{tenant_id} 는 배정된 적이 없습니다.")
        for fp in 지문:
            장부.pop(fp, None)
        _장부쓰기(장부)
        return {"푼_번호": [tenant_id], "남은_배정": len(장부)}


@router.post("/prune", summary="보존정책 즉시 실행")
async def prune_now(
    retain_hours: float | None = Query(None, description="비우면 RETENTION_HOURS"),
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    _auth(x_instructor_token)
    hours = retain_hours if retain_hours is not None else get_settings().retention_hours
    return {"retain_hours": hours, **(await db.prune(hours))}


@router.get("/db-size", summary="DB 사용량 — 무료 티어 500MB 감시용")
async def db_size(
    x_instructor_token: str | None = Header(None, alias="X-Instructor-Token"),
) -> dict:
    _auth(x_instructor_token)
    async with db.pool().acquire() as con:
        rows = await con.fetch(
            "select relname as table, pg_total_relation_size(c.oid) as bytes, "
            "       pg_size_pretty(pg_total_relation_size(c.oid)) as pretty "
            "from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname='public' and c.relkind='r' "
            "order by pg_total_relation_size(c.oid) desc"
        )
        total = await con.fetchval("select pg_database_size(current_database())")
    return {
        "database_bytes": total,
        "database_pretty": f"{total / 1024 / 1024:.1f} MB",
        "free_tier_limit_mb": 500,
        "tables": [dict(r) for r in rows],
    }
