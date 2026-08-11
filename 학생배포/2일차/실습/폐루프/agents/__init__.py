"""에이전트 등록표 — 오케스트레이터가 여기만 봅니다.

1일차에 배운 Orchestrator-Worker 패턴을 여기서 회수합니다.
오케스트레이터(loop.py)는 누가 무슨 일을 하는지 모릅니다. 이 표만 읽습니다.

    감지  →  진단  →  조치        오늘 할 것. 이 세 자리는 이미 꽂혀 있습니다.
    +α                            먼저 끝냈다면. EXTRA 에 한 줄 추가하면 붙습니다.

────────────────────────────────────────────────────────────────
에이전트 하나를 더 붙이는 법 (세 줄이면 끝납니다) — 선택

  1. agents/my_agent.py 를 만들고
  2. run(ctx, record) -> dict 함수를 하나 쓰고
  3. 아래 EXTRA 에 등록합니다

        from . import my_agent
        EXTRA = [my_agent]

  record 에는 그 회차의 감지·진단·조치 결과가 전부 들어 있습니다.
  ctx.api 로 공장을 읽고 움직일 수 있습니다.
  오케스트레이터(loop.py)는 고치지 않습니다 — 이 표만 봅니다.
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from . import actuator, detector, diagnoser

# 기본 미션 — 교안 2일차 4~7장의 세 책임
SENSE = detector
DIAGNOSE = diagnoser
ACT = actuator

# 더 붙일 에이전트 — 여기에 추가합니다 (비어 있는 채로도 정상 동작합니다)
EXTRA: list = []

# 채울 자리 — 아직 안 채운 곳을 만났을 때 어디를 열어야 하는지 알려 주기 위한 표.
# 오케스트레이터가 에이전트 파일 이름을 몰라도 되게 여기에 둔다.
BLANKS = {
    "judge": ("agents/detector.py", "감지"),
    "build_prompt": ("agents/diagnoser.py", "진단"),
    "to_commands": ("agents/actuator.py", "조치"),
}
FILL_ORDER = "judge → build_prompt → to_commands"


def where(function_name: str) -> tuple[str, str]:
    """안 채운 함수 이름 → (파일, 역할). 모르면 빈 표시."""
    return BLANKS.get(function_name, ("agents/", ""))


__all__ = ["SENSE", "DIAGNOSE", "ACT", "EXTRA", "BLANKS", "FILL_ORDER", "where"]
