# -*- coding: utf-8 -*-
"""실습 가이드 두 권을 저장소 루트에 PDF 로 뽑는다 — 강사가 실습하며 바로 보려고.

    uv run 가이드보기.py          두 권 다시 뽑기
    uv run 가이드보기.py --열기    뽑고 바로 열기

왜 루트인가
    학생 실습 폴더(k-precision-lab)에는 **코드와 데이터만** 들어간다. 문서를 넣지 않는다.
    그래서 강사가 볼 것은 여기 루트에 둔다. `.gitignore` 가 커밋을 막는다.

원본은 `강의/실습가이드_*.md` 다. 고친 뒤 이걸 다시 돌리면 된다.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MD2PDF = ROOT / "제작" / "빌드도구" / "md2pdf.py"

일감 = [("실습가이드_2일차", "2일차 실습 가이드"),
       ("실습가이드_3일차", "3일차 실습 가이드")]


def main() -> int:
    열기 = "--열기" in sys.argv
    for 이름, 제목 in 일감:
        원본 = ROOT / "강의" / f"{이름}.md"
        나갈곳 = ROOT / f"{이름}.pdf"
        if not 원본.is_file():
            print(f"  [빠짐] {원본}", file=sys.stderr)
            return 1
        r = subprocess.run([sys.executable, str(MD2PDF), str(원본), str(나갈곳), 제목],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0 or not 나갈곳.is_file():
            # md2pdf 는 그림이 하나라도 없으면 일부러 멈춘다 — 그 이유를 그대로 보여 준다
            print(f"  [실패] {이름}\n{r.stdout}{r.stderr}", file=sys.stderr)
            return 1
        print(f"  {나갈곳.name}  ({나갈곳.stat().st_size // 1024}KB)")
        if 열기:
            subprocess.Popen(["cmd", "/c", "start", "", str(나갈곳)], shell=False)
    print("\n  원본을 고쳤으면 이걸 다시 돌리세요 —  uv run 가이드보기.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
