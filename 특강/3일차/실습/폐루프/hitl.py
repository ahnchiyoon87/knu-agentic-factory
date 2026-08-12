"""승인 관문 — 여기는 이미 되어 있습니다. 고치지 않아도 됩니다.

교안 3일차 10~11장이 정한 규칙 그대로입니다.

    속도를 늦추는 감속은 자동으로 두되,
    정지와 로봇 파견은 사람이 승인해야 실행되게 한다.

왜 이 둘인가 — 되돌릴 수 있는가로 갈립니다.
감속은 rpm 을 되돌리면 그만입니다. 정지는 라인이 서고, 로봇은 이미 움직입니다.

바꾸려면 config.json 의 hitl 만 고칩니다. 코드는 건드리지 않습니다.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

CFG = json.loads((Path(__file__).resolve().parent / "config.json").read_text(encoding="utf-8"))


@dataclass
class Decision:
    allowed: bool
    mode: str          # AUTO | APPROVED | DENIED
    by: str


def needs_approval(command: str) -> bool:
    """이 명령이 사람 승인을 거쳐야 하는가."""
    h = CFG["hitl"]
    if command in h["auto_commands"]:
        return False
    if command in h["approval_commands"]:
        return True
    # 목록에 없는 명령은 안전한 쪽으로 — 물어본다.
    return True


def ask(command: str, target: str, detail: str, why: str) -> Decision:
    """승인 관문. 자동이면 그냥 통과, 아니면 사람에게 묻는다."""
    if not needs_approval(command):
        return Decision(True, "AUTO", "policy")

    if CFG["hitl"].get("auto_approve"):
        # 무인 검증용. 시연·실습에서는 false 로 둡니다.
        return Decision(True, "APPROVED", "auto_approve")

    print("\n" + "─" * 66, file=sys.stderr)
    print("  승인 요청 — 되돌릴 수 없는 행동입니다", file=sys.stderr)
    print(f"    명령   {command}({target})", file=sys.stderr)
    print(f"    내용   {detail}", file=sys.stderr)
    print(f"    이유   {why}", file=sys.stderr)
    print("─" * 66, file=sys.stderr)
    try:
        answer = input("  승인하시겠습니까? [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    if answer in ("y", "yes", "ㅛ"):
        return Decision(True, "APPROVED", "human")
    return Decision(False, "DENIED", "human")
