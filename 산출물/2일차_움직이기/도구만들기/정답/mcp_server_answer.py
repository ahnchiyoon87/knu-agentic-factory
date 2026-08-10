"""2일차 도구만들기 참고 답안 서버 — 강사용.

템플릿의 두 자리를 tool_bodies.py 의 본문으로 채운 것과 같습니다.
Step 2 가 막힌 팀에 강사가 대신 띄워 주거나, 공용 서버로 쓸 때 사용합니다.

    python 정답/mcp_server_answer.py            config.json 의 transport 를 따름
"""
from __future__ import annotations

import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "정답"))

from mcp.server import MCPServer
from tool_bodies import detect_anomaly, query_equipment

CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

mcp = MCPServer(
    name="k-precision-tools",
    instructions="K-정밀 공장의 센서 이상감지와 설비 조회 도구입니다. 조회만 하며 설비를 움직이지 않습니다.",
)
mcp.tool()(detect_anomaly)
mcp.tool()(query_equipment)


def main() -> None:
    if CFG["transport"] == "http":
        mcp.settings.host = CFG["http"]["host"]
        mcp.settings.port = int(CFG["http"]["port"])
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
