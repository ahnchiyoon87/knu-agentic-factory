"""오늘의 열쇠 캡슐 만들기 — 강사 전용.

    uv run tools/열쇠캡슐.py sk-오늘만든열쇠
    uv run tools/열쇠캡슐.py                  (.env 의 OPENAI_API_KEY 로)

`오늘의열쇠.txt` 가 이 폴더에 만들어진다. **드라이브(자료 폴더)에 올리면 끝.**
학생은 그 파일을 받아 `uv run 3일차준비.py` 만 치면 된다 — 열쇠 원문은
드라이브에도, 학생 화면에도, 공장 .env 에도 나타나지 않는다.

정직하게 적어 둔다 — 이것은 **난독화이지 암호화가 아니다.** 작정한 학생은
풀 수 있다. 진짜 방어선은 절대규칙 6 이다: 전용 프로젝트의 예산 상한,
그리고 수업이 끝나면 키와 이 파일을 같이 지우는 것. 풀어 봤자
하루짜리에 한도 걸린 열쇠다. 이 장치의 몫은 「우연한 노출 0」이다.
"""

from __future__ import annotations

# ── 한글 윈도우(cp949)에서 출력이 깨져 죽는 것을 막는다 ──────────────────
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────────────────

import base64
import sys
from itertools import cycle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 캡슐 표식과 양념 — 서버(config.py)·3일차준비.py 와 세 곳이 같아야 한다.
표식 = "KNU1:"
양념 = b"K-precision-2026-knu"


def 캡슐로(열쇠: str) -> str:
    엮음 = bytes(a ^ b for a, b in zip(열쇠.encode("utf-8"), cycle(양념)))
    return 표식 + base64.urlsafe_b64encode(엮음).decode("ascii")


def 열쇠로(캡슐: str) -> str:
    엮음 = base64.urlsafe_b64decode(캡슐[len(표식):].encode("ascii"))
    return bytes(a ^ b for a, b in zip(엮음, cycle(양념))).decode("utf-8")


def _env열쇠() -> str:
    env = ROOT / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            if line.strip().startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def main() -> int:
    열쇠 = (sys.argv[1] if len(sys.argv) > 1 else _env열쇠()).strip()
    if not 열쇠.startswith("sk-"):
        print("sk- 로 시작하는 열쇠를 주세요 —  uv run tools/열쇠캡슐.py sk-...",
              file=sys.stderr)
        return 1

    캡슐 = 캡슐로(열쇠)
    assert 열쇠로(캡슐) == 열쇠, "캡슐 왕복이 어긋났다"

    나갈곳 = Path.cwd() / "오늘의열쇠.txt"
    나갈곳.write_text(캡슐 + "\n", encoding="utf-8")
    print(f"만들었습니다 — {나갈곳}")
    print("  이 파일을 자료 드라이브 폴더에 올리세요.")
    print("  수업이 끝나면 **이 파일과 OpenAI 키를 같이 지우세요** (절대규칙 6).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
