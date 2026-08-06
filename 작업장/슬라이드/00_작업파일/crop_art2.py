# -*- coding: utf-8 -*-
"""
삽화 잘라내기 v2 — 가장자리 잉크 검사로 잘림을 자동 보정한다.

방식:
  1) 1차 사각형(crop_art.py의 CROP)에서 시작
  2) 사각형 가장자리 3px 띠에 잉크가 있으면 그 방향으로 2%씩 넓힌다 (최대 12회)
  3) 원본 경계에 닿으면 멈춘다
  4) 마지막에 잉크 bounding box로 타이트하게 다듬고 3% 여백을 두른다
"""
import pathlib, sys, io
import numpy as np
from PIL import Image
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = pathlib.Path("D:/work/study/경남대특강/작업장/슬라이드/00_작업파일/후보")
OUT = pathlib.Path("D:/work/study/경남대특강/작업장/슬라이드/00_작업파일/삽화")
OUT.mkdir(exist_ok=True)

PICK2 = {3, 10, 20, 21, 22, 23, 26, 27, 30}

CROP = {
    2:  (0.03, 0.16, 0.47, 0.97),
    3:  (0.46, 0.13, 1.00, 0.80),
    4:  (0.03, 0.16, 0.44, 0.97),
    5:  (0.03, 0.16, 0.47, 0.97),
    7:  (0.03, 0.16, 0.50, 0.97),
    8:  (0.03, 0.10, 0.48, 0.97),
    9:  (0.42, 0.13, 1.00, 0.85),
    10: (0.05, 0.28, 0.95, 0.80),
    11: (0.03, 0.16, 0.47, 0.97),
    12: (0.05, 0.24, 0.95, 0.70),
    13: (0.05, 0.22, 0.95, 0.83),
    14: (0.03, 0.16, 0.47, 0.97),
    15: (0.05, 0.22, 0.95, 0.83),
    16: (0.03, 0.08, 0.36, 0.97),
    18: (0.03, 0.20, 0.97, 0.72),
    20: (0.03, 0.08, 0.52, 0.97),
    21: (0.03, 0.25, 0.20, 0.95),
    22: (0.05, 0.25, 0.95, 0.72),
    25: (0.03, 0.05, 0.42, 0.97),
    26: (0.03, 0.28, 0.34, 0.90),
    27: (0.03, 0.25, 0.18, 0.80),
    28: (0.02, 0.22, 0.52, 0.97),
    29: (0.10, 0.22, 0.92, 0.80),
    30: (0.05, 0.20, 0.95, 0.78),
    32: (0.02, 0.03, 0.50, 0.97),
    33: (0.03, 0.17, 0.18, 0.83),
    34: (0.03, 0.18, 0.49, 0.90),
    35: (0.02, 0.10, 0.50, 0.90),
}

# 그림이 화면 절반을 정말 쓰는 장은 반대편 글자와 가까워서
# 자동 확장이 글자를 물 수 있다. 확장 한계를 준다 (비율).
LIMIT = {
    3:  (0.44, 0.05, 1.00, 0.92),
    9:  (0.40, 0.05, 1.00, 0.95),
    10: (0.02, 0.20, 0.98, 0.95),
    12: (0.02, 0.18, 0.98, 0.92),
    13: (0.02, 0.15, 0.98, 0.90),
    15: (0.02, 0.15, 0.98, 0.90),
    18: (0.02, 0.12, 0.98, 0.85),
    22: (0.02, 0.18, 0.98, 0.88),
    29: (0.05, 0.15, 0.95, 0.88),
    30: (0.02, 0.12, 0.98, 0.85),
}
DEFAULT_LIMIT = (0.0, 0.03, 0.55, 1.0)   # 왼쪽 절반형 기본 한계

def ink(a):
    return (a < 238).any(axis=2)

def edge_has_ink(m, side, band=4):
    if side == "l": return m[:, :band].any()
    if side == "r": return m[:, -band:].any()
    if side == "t": return m[:band, :].any()
    if side == "b": return m[-band:, :].any()

for page, box in CROP.items():
    cand = 2 if page in PICK2 else 1
    img = Image.open(SRC / f"p{page:02d}_{cand}.png").convert("RGB")
    W, H = img.size
    lim = LIMIT.get(page, DEFAULT_LIMIT if box[2] <= 0.56 else (0.0, 0.03, 1.0, 1.0))
    x0, y0, x1, y1 = box
    for _ in range(12):
        a = np.asarray(img.crop((int(x0*W), int(y0*H), int(x1*W), int(y1*H))))
        m = ink(a)
        grew = False
        if edge_has_ink(m, "l") and x0 > lim[0] + 0.005: x0 = max(lim[0], x0 - 0.02); grew = True
        if edge_has_ink(m, "r") and x1 < lim[2] - 0.005: x1 = min(lim[2], x1 + 0.02); grew = True
        if edge_has_ink(m, "t") and y0 > lim[1] + 0.005: y0 = max(lim[1], y0 - 0.02); grew = True
        if edge_has_ink(m, "b") and y1 < lim[3] - 0.005: y1 = min(lim[3], y1 + 0.02); grew = True
        if not grew:
            break
    # 타이트 박스 + 여백
    a = np.asarray(img.crop((int(x0*W), int(y0*H), int(x1*W), int(y1*H))))
    m = ink(a)
    ys, xs = np.where(m)
    if len(xs):
        pad_x, pad_y = int(a.shape[1]*0.03), int(a.shape[0]*0.03)
        cx0 = max(0, xs.min()-pad_x); cx1 = min(a.shape[1], xs.max()+pad_x)
        cy0 = max(0, ys.min()-pad_y); cy1 = min(a.shape[0], ys.max()+pad_y)
        out_img = Image.fromarray(a[cy0:cy1, cx0:cx1])
    else:
        out_img = Image.fromarray(a)
    out_img.save(OUT / f"art_{page:02d}.png")
    # 최종 가장자리 잘림 재검
    fm = ink(np.asarray(out_img))
    cut = [s for s in "lrtb" if edge_has_ink(fm, s, 2)]
    flag = f"  ← 가장자리 잉크 {cut}" if cut else ""
    print(f"  {page:>2}p  {out_img.size[0]}x{out_img.size[1]}{flag}")

print("\n완료")
