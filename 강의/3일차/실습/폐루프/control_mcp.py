"""제어 MCP 도구 4개 — 교안 3일차 8~9장.

    "물리 세계를 움직이는 도구 공개 — 시뮬레이터 제어용 MCP 도구 4개를 이제야 열어 줍니다:
     set_equipment_speed / stop_equipment / dispatch_robot / ack_alarm"

오전에 만든 도구는 **읽는 손**이었습니다. 조회만 했습니다.
오늘 열리는 이 네 개가 **움직이는 손**입니다.

이 파일은 **완성되어 있습니다.** 강사가 열어 주는 것이지 학생이 만드는 것이 아닙니다.
학생이 채우는 자리는 agents/ 안의 ★ 세 곳입니다.

    uv run control_mcp.py --check     서버 없이 도구 목록만 확인
    uv run control_mcp.py             MCP 서버 실행 (오케스트레이터가 자동으로 띄웁니다)

────────────────────────────────────────────────────────────────────
승인 관문은 여기 없습니다 — 일부러입니다.

  이 서버는 '통로'일 뿐이고, 승인 여부를 판단하는 것은
  조치 에이전트(agents/actuator.py)와 hitl.py 입니다.

  왜 이렇게 나눴는가 — 교안 10~11장의 승인 관문은 **에이전트가 판단하는 자리**여야
  합니다. 통로 쪽에서 막아 버리면 "에이전트가 사람에게 승인을 요청한다"가
  성립하지 않고 그냥 "API 가 거부한다"가 됩니다.
────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

# ── 한글 윈도우(cp949)에서 출력이 깨져 죽는 것을 막는다 ──────────────────
#    학생 PC 기본 콘솔은 cp949 라 `—` `→` 같은 글자에서 UnicodeEncodeError 가 난다.
#    이 파일은 stdio MCP 서버이기도 해서, 안내문은 전부 stderr 로만 낸다.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────────────────

import argparse
import json
import sys
from pathlib import Path

from mcp.server import MCPServer

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from factory_api import CFG, FactoryAPI  # noqa: E402

mcp = MCPServer(
    name="k-precision-control",
    instructions=(
        "K-정밀 공장의 설비·로봇 제어 도구입니다. 실제로 공장을 움직입니다. "
        "정지와 로봇 파견은 되돌릴 수 없으므로 사람 승인을 받은 뒤에만 호출하십시오."
    ),
)

_api: FactoryAPI | None = None


def api() -> FactoryAPI:
    global _api
    if _api is None:
        _api = FactoryAPI()
    return _api


def _guard(fn) -> dict:
    """도구는 예외를 밖으로 던지지 않는다. 에이전트가 읽을 수 있게 돌려준다."""
    try:
        return {"ok": True, **fn()}
    except Exception as exc:                                       # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


# =============================================================================
# 도구 1 — set_equipment_speed(id, rpm)   설비 속도 조절
# =============================================================================
@mcp.tool()
def set_equipment_speed(equipment_id: str, rpm: float) -> dict:
    """설비의 목표 회전수를 바꾼다. 온도는 회전수의 함수라 감속하면 온도가 내려간다.

    되돌릴 수 있는 행동이다 — 교안상 사람 승인 없이 자동 실행한다.

    Args:
        equipment_id: EQ-01 ~ EQ-06
        rpm: 목표 회전수 (0 ~ 3000)
    """
    return _guard(lambda: api().set_equipment_speed(equipment_id, rpm, issued_by="mcp"))


# =============================================================================
# 도구 2 — stop_equipment(id)   설비 정지
# =============================================================================
@mcp.tool()
def stop_equipment(equipment_id: str, reason: str | None = None) -> dict:
    """설비를 정지시킨다. **라인이 선다. 되돌릴 수 없는 행동이다.**

    사람 승인을 받은 뒤에만 호출하십시오.

    Args:
        equipment_id: EQ-01 ~ EQ-06
        reason: 정지 사유 (감사 로그에 남는다)
    """
    return _guard(lambda: api().stop_equipment(equipment_id, reason=reason, issued_by="mcp"))


# =============================================================================
# 도구 3 — dispatch_robot(robot_id, target)   로봇 파견
# =============================================================================
@mcp.tool()
def dispatch_robot(robot_id: str, target: str) -> dict:
    """AMR 을 목적지로 보낸다. **로봇이 실제로 움직인다. 되돌릴 수 없는 행동이다.**

    사람 승인을 받은 뒤에만 호출하십시오.

    Args:
        robot_id: AMR-01(정비), AMR-02(운반)
        target: 노드명 — EQ-01~EQ-06, WH, DOCK, J1~J4, W-END
    """
    return _guard(lambda: api().dispatch_robot(robot_id, target, issued_by="mcp"))


# =============================================================================
# 도구 4 — ack_alarm(id)   알람 확인 처리
# =============================================================================
@mcp.tool()
def ack_alarm(alarm_id: int, note: str | None = None) -> dict:
    """알람을 '확인함' 상태로 바꾼다. 되돌릴 수 있는 행동이다.

    Args:
        alarm_id: 알람 번호
        note: 처리 메모
    """
    return _guard(lambda: api().ack_alarm(alarm_id, note=note, issued_by="mcp"))


# =============================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="3일차 제어 MCP 서버")
    ap.add_argument("--확인", "--check", dest="확인", action="store_true", help="서버 없이 연결·도구 목록만 확인")
    args = ap.parse_args()

    if args.확인:
        # 설정을 안 채웠으면 여기서 잡힌다 — 역추적 대신 사람이 읽을 말로 세운다
        try:
            info = api().preflight()
        except ValueError as exc:
            print(f"\n{exc}\n", file=sys.stderr)
            return 1
        except Exception as exc:                                   # noqa: BLE001
            print(f"공장에 닿지 못했습니다 — {type(exc).__name__}: {exc}", file=sys.stderr)
            print(f"  주소 {CFG['base_url']} · 네임스페이스 {CFG['tenant']}", file=sys.stderr)
            print("  공장이 켜져 있나요?  공장 폴더에서 —", file=sys.stderr)
            print("      docker compose up -d", file=sys.stderr)
            print("  그래도 안 되면 손 드세요.", file=sys.stderr)
            return 1
        print(json.dumps({
            "연결": info, "도구": ["set_equipment_speed", "stop_equipment",
                                  "dispatch_robot", "ack_alarm"],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"제어 MCP 서버 (stdio) — {CFG['tenant']} @ {CFG['base_url']}", file=sys.stderr)
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
