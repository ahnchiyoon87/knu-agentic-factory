"""3일차 준비 — 단톡방에서 받은 열쇠를 붙여 이 한 줄이면 끝입니다.

    uv run 3일차준비.py sk-여기에열쇠

무엇을 하나
  1. 받은 AI 열쇠를 공장 설정(`공장/.env`)에 넣습니다.
  2. 공장을 새 설정으로 다시 켭니다.

제어 통로는 여기서 안 엽니다 — 오후에 강사 신호에 맞춰 `uv run 제어열기.py` 로 엽니다.

여러분이 파일을 열어 고칠 일이 없습니다. 화면에 「3일차 준비 끝」이 나오면 됩니다.
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

import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def 공장폴더() -> Path:
    for cand in (BASE / "공장", BASE / "시뮬레이터", BASE / "강의" / "시뮬레이터"):
        if (cand / "docker-compose.yml").is_file():
            return cand
    sys.exit("공장 폴더를 못 찾았습니다 — 실습 저장소를 통째로 내려받았는지 확인하세요.")


def _다듬기(s: str) -> str:
    """붙여넣기로 딸려 오는 보이지 않는 글자(BOM·폭 없는 공백)를 털어 낸다."""
    for c in ("﻿", "​", "‌", "‍", " "):
        s = s.replace(c, "")
    return s.strip()


def env고치기(열쇠: str) -> None:
    env = 공장폴더() / ".env"
    lines = env.read_text(encoding="utf-8-sig").splitlines()
    out, 열쇠씀 = [], False
    for line in lines:
        if line.strip().startswith("OPENAI_API_KEY="):
            out.append(f"OPENAI_API_KEY={열쇠}"); 열쇠씀 = True
        else:
            out.append(line)
    if not 열쇠씀:
        out.append(f"OPENAI_API_KEY={열쇠}")
    env.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="3일차 준비")
    ap.add_argument("열쇠", nargs="?", default=None, help="단톡방에서 받은 sk- 로 시작하는 열쇠")
    args = ap.parse_args()

    열쇠 = _다듬기(args.열쇠 or "")
    if not 열쇠:
        print("단톡방에서 받은 열쇠를 뒤에 붙여 주세요 —")
        print("    uv run 3일차준비.py sk-여기에열쇠")
        return 1
    if not 열쇠.startswith("sk-"):
        print("열쇠가 sk- 로 시작해야 합니다. 단톡방에서 **전체를** 복사했는지 확인하세요.")
        return 1

    env고치기(열쇠)
    print("① 열쇠를 넣었습니다.")

    try:
        p = subprocess.run(["docker", "compose", "up", "-d", "--force-recreate"],
                           cwd=str(공장폴더()), capture_output=True, timeout=600)
    except FileNotFoundError:
        print("② 공장은 못 켰습니다 — docker 명령을 못 찾았습니다. 손 드세요.")
        return 1
    except subprocess.TimeoutExpired:
        print("② 공장 켜기가 10분 안에 안 끝났습니다. 손 드세요.")
        return 1
    if p.returncode != 0:
        err = p.stderr.decode("utf-8", errors="replace")
        if "pipe" in err.lower() or "daemon" in err.lower() or "connect" in err.lower():
            print("② **Docker Desktop 이 꺼져 있습니다.** 켜고 이 명령을 한 번 더 실행하세요.")
        else:
            print("② 공장을 못 켰습니다 — 손 드세요.")
            if err.strip():
                print("   " + err.strip().splitlines()[-1][:90])
        return 1

    print("② 공장을 새 설정으로 다시 켰습니다.")
    print()
    print("=" * 58)
    print("  3일차 준비 끝 — 오늘 AI 가 이 열쇠로 움직입니다")
    print("     http://localhost:8000")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
