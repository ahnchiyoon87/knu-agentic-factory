"""에이전트 등록표 — 오케스트레이터가 여기만 봅니다.

2일차에 배운 Orchestrator-Worker 패턴을 여기서 회수합니다.
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
# 진단이 실패했을 때 오케스트레이터가 잡는 예외.
# 여기서 한 번 더 내놓는 이유 — 오케스트레이터가 `agents.diagnoser` 를 직접 import 하면
# **누가 진단을 맡는지 알게 되어** 담당을 갈아 끼울 수 없다. 등록표만 보게 한다.
from .diagnoser import DiagnoseFailed

# 기본 미션 — 교안 3일차 4~7장의 세 책임
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


# =============================================================================
# 「아직 안 채웠다」를 어떻게 아는가
# =============================================================================
class 안채움(RuntimeError):
    """그 자리가 아직 비어 있다. loop.py 가 이것만 잡아 사람 말로 안내한다."""

    def __init__(self, 이름: str) -> None:
        self.이름 = 이름
        super().__init__(이름)


def 비었나(이름: str) -> bool:
    """소스를 읽어 그 함수 속이 비어 있는지 본다.

    전에는 `raise NotImplementedError` 를 잡아서 판정했는데, 그 줄을 없애면서
    학생이 「지울지 고칠지」 헷갈리던 것이 사라진 대신 판정 근거도 같이 사라졌다.
    **설명글(docstring)과 주석 말고 실행되는 줄이 하나도 없으면** 안 채운 것으로 본다.

    안 그러면 빈 함수가 조용히 None 을 돌려주고, 감지는 「이상 없음」으로만 찍힌다.
    학생은 몇 분을 기다리다 **자기가 뭘 안 했는지도 모른 채** 코드를 의심하게 된다.

    `--열기` 로 완성본을 꽂았으면 그 함수는 다른 파일에서 온다 — 그때는 채운 것으로 본다.
    """
    import ast
    from pathlib import Path

    파일, _역할 = BLANKS.get(이름, ("", ""))
    if not 파일:
        return False

    모듈 = {"judge": detector, "build_prompt": diagnoser, "to_commands": actuator}[이름]
    fn = getattr(모듈, 이름, None)
    if fn is not None and getattr(fn, "__code__", None) is not None:
        if Path(fn.__code__.co_filename).name != Path(파일).name:
            return False                     # --열기 로 완성본이 꽂혀 있다

    경로 = Path(__file__).resolve().parents[1] / 파일
    try:
        나무 = ast.parse(경로.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False                         # 없거나 깨진 파일은 부르는 쪽이 따로 짚는다
    for n in ast.walk(나무):
        if isinstance(n, ast.FunctionDef) and n.name == 이름:
            몸 = [x for x in n.body
                  if not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant)
                          and isinstance(x.value.value, str))]
            return not 몸
    return False


def 확인(이름: str) -> None:
    """그 자리를 쓸 차례다. 안 채웠으면 여기서 멈춘다 — 조용히 넘어가지 않는다."""
    if 비었나(이름):
        raise 안채움(이름)


def 안채운자리() -> list[tuple[str, str, str]]:
    """아직 안 채운 자리 전부 — (함수, 파일, 역할). 채울 순서대로 돌려준다."""
    return [(이름, 파일, 역할) for 이름, (파일, 역할) in BLANKS.items() if 비었나(이름)]


__all__ = ["SENSE", "DIAGNOSE", "ACT", "EXTRA", "BLANKS", "FILL_ORDER", "where",
           "DiagnoseFailed", "안채움", "비었나", "확인", "안채운자리"]
