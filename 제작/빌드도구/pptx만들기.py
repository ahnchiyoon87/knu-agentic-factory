"""슬라이드 PNG 를 pptx 한 벌로 묶는다 — 강의장에서 넘기기 위한 것.

    python pptx만들기.py

왜 필요한가
    슬라이드 원본은 코드(`제작/덱빌드/build_*.py`)이고 산출물은 PNG 다.
    내용을 고치는 것은 계속 코드에서 하지만, **강의장에서 넘기는 것은 pptx** 여야 한다.
    이미지 뷰어로 넘기면 창이 닫히거나 순서가 섞일 수 있고, 발표자 화면도 못 쓴다.

    **pptx 를 손으로 고치지 말 것.** 다음에 다시 뽑으면 사라진다.
    글자를 고치려면 `build_*.py` 를 고치고 render 한 뒤 여기를 다시 돌린다.
"""

from __future__ import annotations

import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # 제작/빌드도구/
REPO = ROOT.parents[1]                          # 경남대특강/ (저장소 루트)
슬라이드 = REPO / "특강" / "당일" / "슬라이드"
OUT = REPO / "특강" / "당일"


def main() -> int:
    try:
        from pptx import Presentation
        from pptx.util import Emu
    except ModuleNotFoundError:
        print("python-pptx 가 없습니다 —  pip install python-pptx", file=sys.stderr)
        return 1
    try:
        from PIL import Image
    except ModuleNotFoundError:
        print("Pillow 가 없습니다 —  pip install Pillow", file=sys.stderr)
        return 1

    for 일차 in ("1일차", "2일차"):
        src = 슬라이드 / 일차
        pngs = sorted(src.glob("*.png"), key=lambda p: int(p.stem))
        if not pngs:
            print(f"  [빠짐] {src} 에 PNG 가 없습니다", file=sys.stderr)
            return 1

        w, h = Image.open(pngs[0]).size
        prs = Presentation()
        # 슬라이드 크기를 PNG 비율에 정확히 맞춘다 — 안 맞추면 여백이 생기거나 잘린다
        prs.slide_width = Emu(int(12192000))                      # 16:9 기준 폭
        prs.slide_height = Emu(int(12192000 * h / w))

        빈레이아웃 = prs.slide_layouts[6]                          # 완전 빈 장
        for p in pngs:
            s = prs.slides.add_slide(빈레이아웃)
            s.shapes.add_picture(str(p), 0, 0,
                                 width=prs.slide_width, height=prs.slide_height)

        dst = OUT / f"{일차} 슬라이드.pptx"
        prs.save(str(dst))
        print(f"  만듦  {dst.name}  ({len(pngs)}장 · {dst.stat().st_size // 1024}KB)")

    print("\n  ※ pptx 를 손으로 고치지 마세요. 다시 뽑으면 사라집니다.")
    print("     글자를 고치려면 —  제작/덱빌드/build_*.py  →  render.py  →  이 스크립트")
    return 0


if __name__ == "__main__":
    sys.exit(main())
