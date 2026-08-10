"""진단 중계 창구 — 학생 PC 에 LLM 키를 두지 않기 위한 것.

    학생 PC ──(내 접속 키)──> 이 서버 ──(OPENAI_API_KEY 1개)──> OpenAI

왜 이렇게 하는가
    39명에게 키를 나눠 주면 **회수가 안 된다.** 종이로 나간 키는 사진으로 남는다.
    여기서 중계하면 키는 서버 `.env` 에만 있고, 특강이 끝나면 서버만 내리면 된다.
    한도 초과도 한 곳에서 줄을 세워 막는다.

프롬프트는 서버가 만들지 않는다
    학생이 `diagnoser.py` 에서 고친 프롬프트가 그대로 쓰여야 실습이 성립한다.
    그래서 이 창구는 **받은 프롬프트를 그대로 넘기는 중계**다.
    대신 ① 응답을 진단 스키마로 강제하고 ② 분당 한도를 걸고 ③ 토큰 상한을 둔다.

떨어질 때
    키가 없거나 OpenAI 가 막히면 **503 을 돌려준다.** 학생 쪽 diagnoser 가
    그것을 받아 규칙 기반으로 내려가고, 폐루프 일곱 걸음은 끝까지 간다.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import random
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..config import get_settings
from ..sim.runner import runner

router = APIRouter(prefix="/api/v1", tags=["diagnose"])

# 동시에 OpenAI 로 나가는 요청 수 — 39명이 몰려도 여기서 줄을 선다
_GATE: asyncio.Semaphore | None = None
# 테넌트별 최근 호출 시각 (분당 한도용)
_CALLS: dict[str, deque[float]] = defaultdict(deque)
_USED: dict[str, int] = defaultdict(int)
_KEY_TURN = itertools.count()          # 키를 돌아가며 쓰기 위한 순번
_KEY_DEAD: dict[int, float] = {}       # 인증·결제로 죽은 키는 잠시 건너뛴다


def _keys() -> list[str]:
    """지금 쓸 수 있는 키. 죽은 것으로 표시된 키는 10분간 건너뛴다."""
    all_keys = get_settings().openai_api_keys
    now = time.monotonic()
    live = [k for i, k in enumerate(all_keys)
            if now - _KEY_DEAD.get(i, -1e9) > 600]
    return live or all_keys        # 전부 죽었으면 그래도 한 번은 시도한다


def _gate() -> asyncio.Semaphore:
    global _GATE
    if _GATE is None:
        _GATE = asyncio.Semaphore(get_settings().diagnose_concurrency)
    return _GATE


class DiagnoseReq(BaseModel):
    system: str = Field(..., max_length=8000, description="시스템 지시문")
    user: str = Field(..., max_length=16000, description="근거 자료가 담긴 사용자 지시문")
    schema_: dict = Field(..., alias="schema", description="응답 스키마 (구조화 출력)")
    max_tokens: int = Field(2000, ge=64, le=4000)

    model_config = {"populate_by_name": True}


def _authorize(tenant_id: str, access_key: str | None) -> dict:
    t = runner.tenants.get(tenant_id)
    if t is None:
        raise HTTPException(404, f"'{tenant_id}' 네임스페이스가 없습니다.")
    if not access_key or access_key != t["access_key"]:
        raise HTTPException(401, "X-Access-Key 헤더가 없거나 이 네임스페이스의 키와 다릅니다.")
    return t


def _rate_check(tenant_id: str) -> None:
    s = get_settings()
    now = time.monotonic()
    q = _CALLS[tenant_id]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= s.diagnose_per_min:
        raise HTTPException(
            429,
            f"진단 호출이 1분에 {s.diagnose_per_min}회를 넘었습니다. "
            "루프가 같은 설비를 반복해서 진단하고 있지 않은지 보세요.",
        )
    q.append(now)


async def _ask_openai(req: DiagnoseReq) -> dict:
    """재시도 포함. 한도 초과는 기다렸다 다시 넣는다."""
    from openai import AsyncOpenAI

    s = get_settings()
    keys = _keys()
    last: Exception | None = None

    for attempt in range(4):
        key = keys[next(_KEY_TURN) % len(keys)]      # 돌아가며 쓴다
        client = AsyncOpenAI(api_key=key, timeout=60)
        try:
            res = await client.chat.completions.create(
                model=s.diagnose_model,
                max_completion_tokens=req.max_tokens,
                messages=[{"role": "system", "content": req.system},
                          {"role": "user", "content": req.user}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "diagnosis", "strict": True,
                                                 "schema": req.schema_}},
            )
            choice = res.choices[0]
            if getattr(choice.message, "refusal", None):
                raise RuntimeError(f"모델이 응답을 거부했습니다: {choice.message.refusal}")
            return json.loads(choice.message.content)
        except Exception as exc:                                    # noqa: BLE001
            last = exc
            name = type(exc).__name__
            if "Authentication" in name or "PermissionDenied" in name:
                # 인증·결제로 죽은 키다. 10분간 건너뛰고 다음 키로 간다.
                try:
                    _KEY_DEAD[s.openai_api_keys.index(key)] = time.monotonic()
                except ValueError:
                    pass
                continue
            일시적 = ("RateLimit" in name or "APIConnection" in name
                    or "APITimeout" in name or "InternalServer" in name
                    or "429" in str(exc) or "503" in str(exc))
            if not 일시적 or attempt == 3:
                break
            await asyncio.sleep((2 ** attempt) + random.random())    # 1·2·4초 + 흔들기
    raise HTTPException(503, f"진단 모델 호출 실패 — {type(last).__name__}: {last}")


@router.post("/{tenant_id}/diagnose", summary="진단 중계 (서버가 LLM 키를 쥔다)")
async def diagnose(tenant_id: str, req: DiagnoseReq,
                   x_access_key: str | None = Header(None)) -> dict:
    s = get_settings()
    _authorize(tenant_id, x_access_key)

    if not s.diagnose_enabled:
        raise HTTPException(503, "진단 중계가 꺼져 있습니다. 강사에게 알리세요.")
    if not s.openai_api_keys:
        raise HTTPException(503, "서버에 OPENAI_API_KEY 가 없습니다. 강사에게 알리세요.")

    _rate_check(tenant_id)
    async with _gate():
        out = await _ask_openai(req)

    _USED[tenant_id] += 1
    out["backend"] = "server"
    return out


@router.get("/diagnose/usage", summary="누가 얼마나 썼나 (강사 확인용)")
async def usage() -> dict:
    return {"calls": dict(sorted(_USED.items())), "total": sum(_USED.values()),
            "키": len(get_settings().openai_api_keys),
            "쉬는키": len(_KEY_DEAD)}
