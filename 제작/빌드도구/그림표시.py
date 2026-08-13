"""캡처한 화면에 **붉은 강조 테두리**를 그려 강의/그림/ 에 넣는다.

    python 그림표시.py <원본.png> <저장이름> x1,y1,x2,y2 [x1,y1,x2,y2 ...] [--폴더 이름]

좌표는 원본 이미지의 **픽셀**이다. 여러 개를 주면 여러 곳을 표시한다.
선 두께는 이미지 크기에 맞춰 정해진다 — 큰 캡처에 가는 선을 그으면 안 보인다.

왜 있나
    「여기를 누르세요」가 글로만 있으면 학생은 화면에서 그 자리를 못 찾는다.
    설치·터미널·노션 화면 모두 **누를 자리에 테두리**를 둘러 두고 글은 짧게 쓴다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = REPO / "강의" / "그림"


def main() -> int:
    args = [a for a in sys.argv[1:]]
    폴더 = ""
    if "--폴더" in args:
        i = args.index("--폴더")
        폴더 = args[i + 1]
        del args[i:i + 2]
    if len(args) < 3:
        print(__doc__, file=sys.stderr)
        return 1

    try:
        from PIL import Image, ImageDraw
    except ModuleNotFoundError:
        print("Pillow 가 없습니다 — 제작/ 환경에서 돌리세요", file=sys.stderr)
        return 1

    원본, 이름, *상자들 = args
    im = Image.open(원본).convert("RGB")
    d = ImageDraw.Draw(im)
    굵기 = max(3, round(min(im.size) / 220))
    for s in 상자들:
        try:
            x1, y1, x2, y2 = (int(v) for v in s.split(","))
        except ValueError:
            print(f"좌표 형식이 아닙니다: {s}  (x1,y1,x2,y2)", file=sys.stderr)
            return 1
        d.rectangle([x1, y1, x2, y2], outline=(212, 84, 30), width=굵기)

    dst = (OUT / 폴더) if 폴더 else OUT
    dst.mkdir(parents=True, exist_ok=True)
    저장 = dst / f"{이름}.png"
    im.save(저장)
    print(f"  {저장}  ({im.width}x{im.height} · 표시 {len(상자들)}곳)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
