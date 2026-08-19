"""도구 호출 창구 — 3일차 오전 「AI 가 내 도구를 스스로 부른다」

    학생 코드 ──(내 접속 키 + 내 도구 목록)──> 내 공장 ──(OPENAI_API_KEY)──> OpenAI
    학생 코드 <──(어느 도구를 어떤 인자로 부를지)──┘
    학생 코드 ──(도구를 직접 실행한 결과)────────> 내 공장 ──> OpenAI ──> 리포트

왜 진단 창구(`diagnose.py`)를 안 쓰고 따로 두는가
    진단 창구는 **단발**이다 — 프롬프트를 주면 JSON 하나를 돌려준다.
    오전은 성격이 다르다. AI 가 도구를 **고르고**, 결과를 보고 **또 고른다**.
    여기가 잘못돼도 오후는 영향이 없다.

키는 공장 설정에 있다
    배포본 .env 에 캡슐로 실려 온다. 수업 뒤 강사가 키를 지우면 캡슐도 죽는다.
    도구는 학생 코드에서 실행된다. 공장은 「어느 도구를 부를지」만 중계한다.

★ 재시도는 여기서 한다 — 진단 창구와 같은 이유(39명 동시 혼잡, 줄 세울
  서버 없음). 백오프 규칙도 같은 것을 쓴다.

상태를 서버가 들고 있지 않다
    대화(messages)는 학생 러너가 들고 다닌다. 서버는 매번 받은 것을 그대로 넘긴다.
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

router = APIRouter(prefix="/api/v1", tags=["agent"])

_CALLS: dict[str, deque[float]] = defaultdict(deque)
_USED: dict[str, int] = defaultdict(int)
_KEY_TURN = itertools.count()
_KEY_DEAD: dict[int, float] = {}

# 한 번의 리포트에 모델을 몇 번까지 부를 수 있나.
# 도구 고르기 → 결과 보고 또 고르기 → 최종 리포트. 넉넉해도 이 정도면 끝난다.
# 학생 러너가 무한 루프에 빠져도 여기서 멈춘다(돈이 나가는 호출이다).
최대왕복 = 6


def _keys() -> list[str]:
    all_keys = get_settings().openai_api_keys
    now = time.monotonic()
    live = [k for i, k in enumerate(all_keys) if now - _KEY_DEAD.get(i, -1e9) > 600]
    return live or all_keys


class AgentReq(BaseModel):
    """학생 러너가 보내는 것 — 지금까지의 대화와 내가 만든 도구 목록."""

    messages: list[dict] = Field(..., description="OpenAI 형식 대화. 학생 러너가 들고 다닌다")
    tools: list[dict] = Field(..., description="내가 만든 도구의 이름·설명·인자 (function 형식)")
    max_tokens: int = Field(1500, ge=64, le=4000)
    왕복: int = Field(0, ge=0, description="지금 몇 번째 왕복인가 — 러너가 세어서 보낸다")

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
            f"호출이 1분에 {s.diagnose_per_min}회를 넘었습니다. "
            "같은 도구를 계속 부르고 있지 않은지 화면을 보세요.",
        )
    q.append(now)


async def _ask(req: AgentReq) -> dict:
    """도구 목록을 함께 넘기고, 모델이 낸 답 한 통을 그대로 돌려준다."""
    from openai import AsyncOpenAI

    from .diagnose import _잠깐대기          # 백오프 규칙은 한 벌만 둔다

    s = get_settings()
    keys = _keys()
    last: Exception | None = None
    시도 = 6

    for attempt in range(시도):
        key = keys[next(_KEY_TURN) % len(keys)]
        client = AsyncOpenAI(api_key=key, timeout=60, max_retries=0,
                             base_url=s.openai_base_url or None)
        try:
            res = await client.chat.completions.create(
                model=s.diagnose_model,
                max_completion_tokens=req.max_tokens,
                messages=req.messages,
                tools=req.tools,
                tool_choice="auto",
            )
            m = res.choices[0].message
            return {
                "content": m.content,
                "tool_calls": [
                    {"id": c.id, "name": c.function.name, "arguments": c.function.arguments}
                    for c in (m.tool_calls or [])
                ],
                "finish_reason": res.choices[0].finish_reason,
            }
        except Exception as exc:                                    # noqa: BLE001
            last = exc
            name = type(exc).__name__
            if "Authentication" in name or "PermissionDenied" in name:
                try:
                    _KEY_DEAD[s.openai_api_keys.index(key)] = time.monotonic()
                except ValueError:
                    pass
                continue
            # 크레딧 소진은 기다려도 안 풀린다 — 재시도하지 않고 바로 알린다
            if "insufficient_quota" in str(exc) or "credit" in str(exc).lower():
                break
            일시적 = ("RateLimit" in name or "APIConnection" in name
                    or "APITimeout" in name or "InternalServer" in name
                    or "429" in str(exc) or "503" in str(exc))
            if not 일시적 or attempt == 시도 - 1:
                break
            await asyncio.sleep(_잠깐대기(exc, attempt))

    from .diagnose import _실패안내          # 안내 문구도 한 벌만 둔다
    raise _실패안내(last)


@router.post("/{tenant_id}/agent", summary="도구 호출 중계 (서버가 LLM 키를 쥔다)")
async def agent(tenant_id: str, req: AgentReq,
                x_access_key: str | None = Header(None)) -> dict:
    s = get_settings()
    _authorize(tenant_id, x_access_key)

    if not s.diagnose_enabled:
        raise HTTPException(503, "AI 중계가 꺼져 있습니다. 강사에게 알리세요.")
    if not s.openai_api_keys:
        raise HTTPException(503, "서버에 OPENAI_API_KEY 가 없습니다. 강사에게 알리세요.")
    if not req.tools:
        raise HTTPException(400, "도구 목록이 비었습니다. mcp_server.py 의 ★ 두 자리를 먼저 채우세요.")
    if req.왕복 >= 최대왕복:
        raise HTTPException(
            400,
            f"도구를 {최대왕복}번 넘게 불렀습니다. 여기서 멈춥니다 — "
            "도구가 같은 값을 계속 돌려주고 있지 않은지 보세요.",
        )

    _rate_check(tenant_id)
    out = await _ask(req)

    _USED[tenant_id] += 1
    return out


