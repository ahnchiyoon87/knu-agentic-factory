"""이상 시작 — 학생이 자기 공장에 오늘의 고장을 건다.

전에는 강사 리모컨이 39개 공장에 한꺼번에 주입했다. 이제 공장이 학생 PC 에서
하나씩 돌므로, 학생이 자기 화면의 버튼을 눌러 자기 공장에 건다. 강사는
"다 같이 누르세요" 신호만 준다 — 같은 순간을 만드는 방법이 바뀌었을 뿐이다.

**무엇이 고장나는지는 응답에 넣지 않는다.** 2일차 24장 「무엇이 달라졌습니까」가
학생이 스스로 찾는 자리다 — 여기서 말해 버리면 그 장이 죽는다 (절대 규칙 4).

배속도 여기서 같이 다룬다. 4시간짜리 드리프트를 배속 x120 으로 올려 실제
2분 30초에 소진시키고, 끝나면 x60 으로 스스로 돌아온다 — 학생이 되돌릴
스위치를 기억할 필요가 없다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import timezone

from fastapi import APIRouter, HTTPException

from .. import db
from ..config import get_profile
from ..sim.engine import Injection, default_end
from ..sim.runner import runner

router = APIRouter(prefix="/api/v1", tags=["drill"])
UTC = timezone.utc
log = logging.getLogger("sim.drill")

# 오늘의 고장 — 2일차·3일차가 같은 것을 쓴다 (0.5℃/h · 4시간 · 62→64℃).
# 어느 설비인지는 sim_profile.json 의 기본값이 정한다. 여기 적지 않는다.
_KIND = "temp_drift"
_DRILL_SCALE = 120.0        # 가상 4시간 = 실제 2분
_BASE_SCALE = 60.0          # 끝나면 여기로 돌아온다 (sim_profile 기본과 같다)

_revert_task: asyncio.Task | None = None


def _tenant(tenant_id: str) -> str:
    if tenant_id not in runner.tenants:
        raise HTTPException(404, f"'{tenant_id}' 공장이 이 서버에 없습니다.")
    return tenant_id


def _active(tenant_id: str) -> list[Injection]:
    return [i for i in runner.engine.injections.values()
            if i.active and i.tenant_id in (tenant_id, "*")]


async def _revert_later(real_seconds: float) -> None:
    """주입이 소진되면 배속을 기본으로 되돌린다. 학생이 누를 것이 없다."""
    await asyncio.sleep(real_seconds + 5)
    if runner.time_scale != _BASE_SCALE:
        runner.set_time_scale(_BASE_SCALE)
        log.info("이상 소진 — 배속을 x%g 로 되돌림", _BASE_SCALE)


@router.post("/{tenant_id}/drill", summary="이상 시작 — 내 공장에 오늘의 고장을 건다")
async def drill_start(tenant_id: str) -> dict:
    tenant_id = _tenant(tenant_id)

    # 두 번 눌러도 두 개가 걸리지 않는다 — 진행 중이면 그대로 알려 준다
    if _active(tenant_id):
        return {"시작": False, "안내": "이미 진행 중입니다. 화면을 그대로 보세요."}

    profile = get_profile()
    defaults = dict(profile["anomaly_defaults"][_KIND])
    equipment_id = defaults.pop("target_equipment")
    params = {k: v for k, v in defaults.items() if not k.startswith("_")}

    prev = runner.time_scale
    if prev != _DRILL_SCALE:
        runner.set_time_scale(_DRILL_SCALE)

    starts_at = runner.virtual_now
    ends_at = default_end(_KIND, params, starts_at, profile)

    async with db.pool().acquire() as con:
        row = await con.fetchrow(
            """
            insert into anomaly_injection (tenant_id, equipment_id, kind, params,
                                           starts_at, ends_at, created_by)
            values ($1, $2, $3, $4::jsonb, $5, $6, 'student-drill')
            returning id
            """,
            tenant_id, equipment_id, _KIND,
            json.dumps(params, ensure_ascii=False), starts_at, ends_at,
        )
    runner.engine.injections[row["id"]] = Injection(
        id=row["id"], tenant_id=tenant_id, equipment_id=equipment_id,
        kind=_KIND, params=params, starts_at=starts_at, ends_at=ends_at,
    )

    lasts_real = None
    if ends_at:
        lasts_real = (ends_at - starts_at).total_seconds() / _DRILL_SCALE
        global _revert_task
        if _revert_task and not _revert_task.done():
            _revert_task.cancel()
        _revert_task = asyncio.create_task(_revert_later(lasts_real))

    # 어느 설비·무슨 종류인지는 돌려주지 않는다 — 학생이 찾는 것이 오늘의 일이다.
    return {
        "시작": True,
        "안내": "지금 이 공장 어딘가에서 이상이 시작됐습니다. 화면을 보세요.",
        "실제_소요_분": round(lasts_real / 60, 1) if lasts_real else None,
        "배속": runner.time_scale,
    }


@router.post("/{tenant_id}/control-unlock", summary="제어 개방 — 3일차 31장에서 연다")
async def control_unlock(tenant_id: str) -> dict:
    """어제까지 잠겨 있던 제어 통로 넷을 연다.

    재기동이 없다 — 화면의 「제어」 배지가 다음 폴링(2초)에 「개방」으로 바뀐다.
    31장 「지금 제어 권한이 열렸습니다」가 말 그대로 사실이 되는 장치다.
    내 공장(내 DB)만 여는 것이라 남에게 영향이 없다.
    """
    tenant_id = _tenant(tenant_id)
    async with db.pool().acquire() as con:
        await con.execute(
            "update tenant set control_unlocked=true where tenant_id=$1", tenant_id)
    runner.tenants[tenant_id]["control_unlocked"] = True
    return {"제어": "개방", "안내": "화면 위 「제어」가 개방으로 바뀝니다. 이제 네 도구가 실제로 움직입니다."}


@router.post("/{tenant_id}/drill/stop", summary="이상 중단 — 원래대로")
async def drill_stop(tenant_id: str) -> dict:
    tenant_id = _tenant(tenant_id)
    n = 0
    for inj in _active(tenant_id):
        inj.active = False
        n += 1
    async with db.pool().acquire() as con:
        await con.execute(
            "update anomaly_injection set active=false, ends_at=$2 "
            "where active and tenant_id=$1",
            tenant_id, runner.virtual_now,
        )
    if runner.time_scale != _BASE_SCALE:
        runner.set_time_scale(_BASE_SCALE)
    return {"중단": n, "배속": runner.time_scale}
