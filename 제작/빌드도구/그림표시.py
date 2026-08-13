"""안내문 그림에 빨간 테두리를 그린다 — 학생이 글을 안 읽어도 어디를 누를지 보이게.

    python 그림표시.py <원본이미지> <저장이름> x1,y1,x2,y2 [x1,y1,x2,y2 ...]

좌표는 원본 이미지의 픽셀이다. 여러 개를 주면 여러 곳에 그린다.
저장은 항상 `특강/그림/<저장이름>.png` — 안내문이 그 경로를 가리킨다.

왜 있나
    화면 순서를 글로만 적으면 39명 중 몇 명은 반드시 다른 것을 누른다.
    「여기」를 그림으로 보여주는 것이 문장 열 줄보다 확실하다.
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
REPO = ROOT.parents[1]                          # 경남대특강/
OUT = REPO / "특강" / "그림"

# 테두리 굵기는 이미지 크기에 비례 — 작은 캡처에서 너무 굵어지지 않게
최소굵기 = 3


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        from PIL import Image, ImageDraw
    except ModuleNotFoundError:
        print("Pillow 가 없습니다 —  uv sync", file=sys.stderr)
        return 1

    src = Path(sys.argv[1])
    if not src.is_file():
        print(f"원본을 못 찾았습니다: {src}", file=sys.stderr)
        return 1
    이름 = sys.argv[2]

    상자 = []
    for a in sys.argv[3:]:
        try:
            x1, y1, x2, y2 = (int(v) for v in a.split(","))
        except ValueError:
            print(f"좌표 형식이 틀렸습니다: {a}  (x1,y1,x2,y2)", file=sys.stderr)
            return 1
        상자.append((x1, y1, x2, y2))

    im = Image.open(src).convert("RGB")
    굵기 = max(최소굵기, round(min(im.size) / 220))
    d = ImageDraw.Draw(im)
    for (x1, y1, x2, y2) in 상자:
        d.rectangle([x1, y1, x2, y2], outline=(230, 30, 40), width=굵기)

    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{이름}.png"
    im.save(dst)
    print(f"  만듦  {dst.relative_to(REPO)}  ({im.size[0]}x{im.size[1]} · 표시 {len(상자)}곳)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
