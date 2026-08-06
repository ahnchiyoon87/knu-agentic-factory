# -*- coding: utf-8 -*-
"""
문제 장만 고정 좌표로 재크롭 (자동 확장 없음 — 자동 확장이 글자를 물었다).
좌표는 후보 원본(1376x768) 비율. 잘라낸 뒤 잉크 bbox + 2% 여백으로 다듬는다.
"""
import pathlib, sys, io
import numpy as np
from PIL import Image
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = pathlib.Path("D:/work/study/경남대특강/작업장/슬라이드/00_작업파일/후보")
OUT = pathlib.Path("D:/work/study/경남대특강/작업장/슬라이드/00_작업파일/삽화")
PICK2 = {3, 10, 20, 21, 22, 23, 26, 27, 30}

# 그림만 (글자·제목·결론 제외). 눈으로 원본을 보고 정한 값.
FIX = {
    3:  (0.46, 0.24, 0.99, 0.76),   # 곡선 + 양끝 라벨
    4:  (0.04, 0.16, 0.42, 0.96),   # 온도계
    9:  (0.44, 0.14, 0.99, 0.90),   # 임계선 그래프 (16℃ 남음 포함)
    12: (0.03, 0.09, 0.97, 0.44),   # 자동차·로봇·공장 그림 줄만 (낱말·풀이는 새로 찍음)
    14: (0.04, 0.16, 0.44, 0.99),   # 제어반 (바닥까지)
    21: (0.04, 0.28, 0.16, 0.92),   # 왼쪽 아이콘 3개 열만
    26: (0.04, 0.32, 0.32, 0.84),   # 조립 라인 아이콘 블록만
    27: (0.03, 0.26, 0.15, 0.76),   # 세 갈래 길 아이콘 열만
    28: (0.02, 0.26, 0.50, 0.94),   # 설비 6대 (제목·본문 제외)
    29: (0.34, 0.14, 0.62, 0.72),   # 가운데 총괄 타워+돋보기만 (담당 아이콘·라벨은 새로)
    32: (0.02, 0.04, 0.49, 0.96),   # 공장 도면만
    33: (0.04, 0.18, 0.15, 0.82),   # 아이콘 열만
    34: (0.04, 0.18, 0.47, 0.90),   # 닫힌 고리
    35: (0.02, 0.12, 0.48, 0.88),   # 말→화면
}

def ink(a): return (a < 238).any(axis=2)

for page, (x0, y0, x1, y1) in FIX.items():
    cand = 2 if page in PICK2 else 1
    img = Image.open(SRC / f"p{page:02d}_{cand}.png").convert("RGB")
    W, H = img.size
    a = np.asarray(img.crop((int(x0*W), int(y0*H), int(x1*W), int(y1*H))))
    m = ink(a); ys, xs = np.where(m)
    if len(xs):
        px, py = int(a.shape[1]*0.02), int(a.shape[0]*0.02)
        a = a[max(0,ys.min()-py):min(a.shape[0],ys.max()+py),
              max(0,xs.min()-px):min(a.shape[1],xs.max()+px)]
    Image.fromarray(a).save(OUT / f"art_{page:02d}.png")
    print(f"  {page:>2}p  {a.shape[1]}x{a.shape[0]}")

# 12p는 12번 낱말 아이콘 3개를 쓰는 대신, 그림 줄이 낮으면 확인 필요
print("\n재크롭 완료")
