# -*- coding: utf-8 -*-
"""만든 pptx 를 낱장 PNG 로 내보낸다 — **눈으로 보고 고치기 위한 것.**

    python 제작/검증도구/pptx눈으로.py 노션

왜
    자동 검사는 「글자가 상자를 넘었나」까지만 본다. 번호가 원 밖으로 나갔는지,
    밑칠이 글자와 어긋났는지, 캡처가 찌그러졌는지는 **보아야** 안다.
    검사만 믿고 넘겼다가 여러 장이 그대로 나갔다.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
어디 = {"노션": "2일차/강의자료/노션_자산화.pptx",
        "2일차": "2일차/강의자료/슬라이드.pptx",
        "3일차": "3일차/강의자료/슬라이드.pptx"}


def main() -> int:
    이름 = sys.argv[1] if len(sys.argv) > 1 else "노션"
    원본 = REPO / "강의" / 어디[이름]
    낼곳 = REPO / "제작" / "산출물" / "눈으로" / 이름
    if 낼곳.exists():
        for p in 낼곳.glob("*.PNG"):
            p.unlink()
        for p in 낼곳.glob("*.png"):
            p.unlink()
    낼곳.mkdir(parents=True, exist_ok=True)

    import win32com.client as w
    app = w.Dispatch("PowerPoint.Application")
    p = app.Presentations.Open(str(원본), True, False, False)
    p.SaveCopyAs(str(낼곳 / "s.png"), 18)          # 18 = ppSaveAsPNG
    p.Close()
    app.Quit()

    # SaveCopyAs 는 「s」 폴더를 만들어 그 안에 슬라이드N.PNG 를 넣는다 — 꺼내서 번호로 맞춘다
    안 = 낼곳 / "s"
    if 안.is_dir():
        for f in 안.glob("*.PNG"):
            n = int("".join(ch for ch in f.stem if ch.isdigit()))
            f.replace(낼곳 / f"{n:02d}.png")
        안.rmdir()
    수 = len(list(낼곳.glob("*.png")))
    print(f"  {수}장  →  {낼곳}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
