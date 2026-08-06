# -*- coding: utf-8 -*-
"""
본문 블록형 재크롭 — 낱말나열·비교형은 그림+낱말+풀이가 한 덩어리.
그 덩어리(제목·설명문·결론 제외)를 통째로 삽화로 쓴다.
안의 글자는 설명란 원문과 일치함을 눈으로 확인했다.
"""
import pathlib, sys, io
import numpy as np
from PIL import Image
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = pathlib.Path("D:/work/study/경남대특강/작업장/슬라이드/00_작업파일/후보")
OUT = pathlib.Path("D:/work/study/경남대특강/작업장/슬라이드/00_작업파일/삽화")
PICK2 = {3, 10, 20, 21, 22, 23, 26, 27, 30}

FIX = {
    10: (0.03, 0.26, 0.97, 0.84),   # 눈·저울·손 + 낱말 + 풀이
    12: (0.03, 0.24, 0.97, 0.83),   # 자동차·로봇·공장 + 낱말 + 풀이
    13: (0.03, 0.22, 0.97, 0.84),   # 에어컨/전자레인지 + 태그 + 소제목 + 본문
    15: (0.03, 0.20, 0.97, 0.84),   # 사람/규칙 블록
    22: (0.03, 0.24, 0.97, 0.85),   # 뇌·도구·루프·자율성 + 낱말 + 풀이
    29: (0.03, 0.12, 0.97, 0.88),   # 차이문단 + 총괄타워 + 담당 3열 + 라벨
    30: (0.03, 0.20, 0.97, 0.84),   # 만드는 쪽/검사하는 쪽 블록
}

def ink(a): return (a < 238).any(axis=2)

for page, (x0, y0, x1, y1) in FIX.items():
    cand = 2 if page in PICK2 else 1
    img = Image.open(SRC / f"p{page:02d}_{cand}.png").convert("RGB")
    W, H = img.size
    a = np.asarray(img.crop((int(x0*W), int(y0*H), int(x1*W), int(y1*H))))
    m = ink(a); ys, xs = np.where(m)
    if len(xs):
        px, py = int(a.shape[1]*0.015), int(a.shape[0]*0.02)
        a = a[max(0,ys.min()-py):min(a.shape[0],ys.max()+py),
              max(0,xs.min()-px):min(a.shape[1],xs.max()+px)]
    Image.fromarray(a).save(OUT / f"art_{page:02d}.png")
    print(f"  {page:>2}p  {a.shape[1]}x{a.shape[0]}")
print("완료")
