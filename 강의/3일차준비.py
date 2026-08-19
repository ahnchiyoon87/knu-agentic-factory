"""3일차 준비 — 드라이브에서 「오늘의열쇠.txt」 를 받은 뒤, 이 한 줄이면 끝입니다.

    uv run 3일차준비.py

무엇을 하나
  1. 받아 둔 「오늘의열쇠.txt」 를 스스로 찾습니다 — 다운로드 폴더에 있어도 됩니다.
  2. 그 열쇠를 공장 설정(`공장/.env`)에 넣습니다. 내용은 화면에 보여 주지 않습니다.
  3. 공장을 새 설정으로 다시 켭니다.

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
    """붙여넣기·저장으로 딸려 오는 보이지 않는 글자(BOM·폭 없는 공백)를 털어 낸다."""
    for c in ("﻿", "​", "‌", "‍", " "):
        s = s.replace(c, "")
    return s.strip()


def 열쇠찾기(직접: str | None) -> str:
    """오늘의 열쇠를 찾는다. 내용은 화면에 찍지 않는다.

    ① 인자로 직접 준 것 (강사·검증용 — sk- 평문도 받는다)
    ② 실습 저장소 맨 위의 오늘의열쇠*.txt
    ③ 내 다운로드 폴더의 오늘의열쇠*.txt — 드라이브에서 받으면 여기 떨어진다.
       같은 파일을 두 번 받으면 「오늘의열쇠 (1).txt」 가 되므로 가장 최근 것을 쓴다.
    """
    if 직접:
        return _다듬기(직접)

    후보: list[Path] = []
    for 폴더 in (BASE, Path.home() / "Downloads", Path.home() / "다운로드"):
        if 폴더.is_dir():
            후보 += list(폴더.glob("오늘의열쇠*.txt"))
    if not 후보:
        print("「오늘의열쇠.txt」 를 못 찾았습니다.")
        print("  자료 드라이브 폴더에서 그 파일을 먼저 받으세요 — 다운로드 폴더에")
        print("  그대로 있어도 됩니다. 받은 뒤 이 명령을 한 번 더 치세요.")
        sys.exit(1)
    최신 = max(후보, key=lambda p: p.stat().st_mtime)
    print(f"① 열쇠 파일을 찾았습니다 — {최신.name}")
    return _다듬기(최신.read_text(encoding="utf-8-sig"))


def 값확인(값: str) -> None:
    if 값.startswith("KNU1:") or 값.startswith("sk-"):
        return
    print("열쇠 파일 내용이 예상과 다릅니다. 드라이브에서 **오늘 올라온 파일**을")
    print("다시 받아 보세요. 그래도 안 되면 손 드세요.")
    sys.exit(1)


def env고치기(값: str) -> None:
    env = 공장폴더() / ".env"
    lines = env.read_text(encoding="utf-8-sig").splitlines()
    out, 씀 = [], False
    for line in lines:
        if line.strip().startswith("OPENAI_API_KEY="):
            out.append(f"OPENAI_API_KEY={값}"); 씀 = True
        else:
            out.append(line)
    if not 씀:
        out.append(f"OPENAI_API_KEY={값}")
    env.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="3일차 준비")
    # 학생은 인자가 필요 없다. 강사·검증이 평문 키로 돌릴 때만 쓴다.
    ap.add_argument("열쇠", nargs="?", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    값 = 열쇠찾기(args.열쇠)
    값확인(값)
    env고치기(값)
    print("② 열쇠를 공장에 넣었습니다.")

    try:
        p = subprocess.run(["docker", "compose", "up", "-d", "--force-recreate"],
                           cwd=str(공장폴더()), capture_output=True, timeout=600)
    except FileNotFoundError:
        print("③ 공장은 못 켰습니다 — docker 명령을 못 찾았습니다. 손 드세요.")
        return 1
    except subprocess.TimeoutExpired:
        print("③ 공장 켜기가 10분 안에 안 끝났습니다. 손 드세요.")
        return 1
    if p.returncode != 0:
        err = p.stderr.decode("utf-8", errors="replace")
        if "pipe" in err.lower() or "daemon" in err.lower() or "connect" in err.lower():
            print("③ **Docker Desktop 이 꺼져 있습니다.** 켜고 이 명령을 한 번 더 실행하세요.")
        else:
            print("③ 공장을 못 켰습니다 — 손 드세요.")
            if err.strip():
                print("   " + err.strip().splitlines()[-1][:90])
        return 1

    print("③ 공장을 새 설정으로 다시 켰습니다.")
    print()
    print("=" * 58)
    print("  3일차 준비 끝 — 오늘 AI 가 이 열쇠로 움직입니다")
    print("     http://localhost:8000")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
