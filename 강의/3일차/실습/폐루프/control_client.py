"""제어 통로 — 여기는 이미 되어 있습니다. 고치지 않아도 됩니다.

조치 에이전트가 실제로 명령을 내보내는 자리입니다. 두 갈래가 있습니다.

    mcp     control_mcp.py 를 MCP 서버로 띄우고 **도구를 호출**한다  ← 교안 8~9장, 기본
    direct  제어 API 를 HTTP 로 직접 호출한다                        ← 우회 경로

**어느 쪽이든 조치 에이전트 쪽 코드는 같습니다.** 그래서 MCP 가 말썽이면
config.json 한 줄만 바꿔 실습을 계속할 수 있습니다.

교안이 정한 것은 "제어 4종을 MCP 도구 형태로 연다"이므로 기본값은 mcp 입니다.
direct 는 「동작 보장 최소 경로」의 마지막 사다리입니다.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTROL_TOOLS = ("set_equipment_speed", "stop_equipment", "dispatch_robot", "ack_alarm")


class MCPControl:
    """MCP 서버를 자식 프로세스로 띄우고 도구를 호출한다.

    오케스트레이터는 동기 코드라, 비동기 MCP 세션을 백그라운드 이벤트 루프에
    한 번 열어 두고 그쪽으로 호출을 넘긴다. 명령마다 서버를 새로 띄우지 않는다.
    """

    def __init__(self, script: Path | None = None, timeout: float = 30.0,
                 api=None):
        self.script = script or (ROOT / "control_mcp.py")
        self.timeout = timeout
        # 자식 프로세스에 접속 정보를 물려준다. config.json 을 다시 읽게 두면
        # 부모가 런타임에 바꾼 값(번호·키·주소)이 반영되지 않는다.
        self.env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        if api is not None:
            self.env.update({"W6_BASE_URL": api.base, "W6_TENANT": api.tenant,
                             "W6_ACCESS_KEY": api.key})
        self.tools: list[str] = []
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._ready = threading.Event()
        self._stop = asyncio.Event()
        self._session = None
        self._error: BaseException | None = None
        asyncio.run_coroutine_threadsafe(self._serve(), self._loop)
        if not self._ready.wait(self.timeout):
            raise TimeoutError("제어 MCP 서버가 시간 안에 뜨지 않았습니다.")
        if self._error:
            raise self._error

    async def _serve(self) -> None:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(command=sys.executable, args=[str(self.script)],
                                       cwd=str(ROOT), env=self.env)
        try:
            with open(ROOT / "_control_mcp.log", "w", encoding="utf-8") as errlog:
                async with stdio_client(params, errlog=errlog) as (r, w):
                    async with ClientSession(r, w) as session:
                        await session.initialize()
                        self.tools = [t.name for t in (await session.list_tools()).tools]
                        self._session = session
                        self._ready.set()
                        await self._stop.wait()
        except BaseException as exc:                               # noqa: BLE001
            self._error = exc
            self._ready.set()

    def call(self, tool: str, **args) -> dict:
        if self._session is None:
            raise RuntimeError("제어 MCP 세션이 없습니다.")
        fut = asyncio.run_coroutine_threadsafe(
            self._session.call_tool(tool, args), self._loop)
        return _payload(fut.result(timeout=self.timeout))

    # 조치 에이전트가 쓰는 이름 — direct 경로와 시그니처가 같다
    def set_equipment_speed(self, equipment_id: str, rpm: float) -> dict:
        return self.call("set_equipment_speed", equipment_id=equipment_id, rpm=rpm)

    def stop_equipment(self, equipment_id: str, reason: str | None = None) -> dict:
        return self.call("stop_equipment", equipment_id=equipment_id, reason=reason)

    def dispatch_robot(self, robot_id: str, target: str) -> dict:
        return self.call("dispatch_robot", robot_id=robot_id, target=target)

    def ack_alarm(self, alarm_id: int, note: str | None = None) -> dict:
        return self.call("ack_alarm", alarm_id=alarm_id, note=note)

    def close(self) -> None:
        try:
            self._loop.call_soon_threadsafe(self._stop.set)
            self._thread.join(timeout=5)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            (ROOT / "_control_mcp.log").unlink(missing_ok=True)


class DirectControl:
    """우회 경로 — MCP 없이 제어 API 를 직접 부른다. 도구 이름과 시그니처는 같다."""

    def __init__(self, api):
        self.api = api
        self.tools = list(CONTROL_TOOLS)

    def set_equipment_speed(self, equipment_id: str, rpm: float) -> dict:
        return self.api.set_equipment_speed(equipment_id, rpm)

    def stop_equipment(self, equipment_id: str, reason: str | None = None) -> dict:
        return self.api.stop_equipment(equipment_id, reason=reason)

    def dispatch_robot(self, robot_id: str, target: str) -> dict:
        return self.api.dispatch_robot(robot_id, target)

    def ack_alarm(self, alarm_id: int, note: str | None = None) -> dict:
        return self.api.ack_alarm(alarm_id, note=note)

    def close(self) -> None:
        return None


def _payload(res) -> dict:
    """도구 결과를 꺼낸다. 에이전트가 실제로 받는 형태(JSON 텍스트)를 그대로 읽는다."""
    if getattr(res, "structured_content", None):
        return res.structured_content
    for c in res.content or []:
        text = getattr(c, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"ok": True, "text": text}
    return {}


def open_control(cfg: dict, api, log=print):
    """config 의 control_transport 대로 통로를 연다. MCP 가 실패하면 직접 경로로 내려온다."""
    want = cfg.get("control_transport", "mcp")
    if want == "direct":
        return DirectControl(api)
    try:
        client = MCPControl(api=api)
        missing = [t for t in CONTROL_TOOLS if t not in client.tools]
        if missing:
            client.close()
            raise RuntimeError(f"제어 도구가 모자랍니다: {missing}")
        log(f"제어  MCP 도구 {len(client.tools)}개 — {', '.join(client.tools)}")
        return client
    except Exception as exc:                                       # noqa: BLE001
        log(f"제어  MCP 를 못 띄웠습니다 ({type(exc).__name__}: {exc}) → 직접 경로로 갑니다")
        return DirectControl(api)
