# -*- coding: utf-8 -*-
"""실제 화면(PNG)을 슬라이드에 박고, 누를 자리에 붉은 표시를 얹는다.

    화면("완성_홈")                      → 화면만
    화면("만들기_04_표메뉴",
         (6, 22, 88, 16, "1"))          → 그 자리에 붉은 상자 + 번호 뱃지

좌표는 **화면 이미지 기준 백분율** (왼쪽, 위, 너비, 높이) 로 적는다.
픽셀이 아니라 %  — 화면을 다시 뽑아 크기가 달라져도 표시가 안 어긋난다.

왜 그림이 아니라 캡처인가
    학생은 진짜 노션을 보면서 따라온다. 흉내 낸 그림은 실제와 조금씩 달라서
    「내 화면엔 이게 없는데」로 이어진다. 화면은 캡처, 설명은 그 화면에 대해서만.
"""

from __future__ import annotations

import base64
import functools
import struct
from pathlib import Path

그림 = Path(__file__).resolve().parents[2] / "강의" / "그림"


@functools.lru_cache(maxsize=64)
def _읽기(경로: str) -> tuple[str, int, int]:
    """base64 와 함께 **가로·세로 픽셀**을 돌려준다.

    비율을 CSS 에 못 박아야 화면이 본문 상자 높이에 정확히 맞는다.
    비율 없이 max-height 만 주면 상자를 넘쳐 제목·각주를 침범한다(실제로 겪음).
    """
    p = 그림 / 경로
    if not p.is_file():
        raise SystemExit(f"화면 그림이 없습니다: {p}\n"
                         f"  노션 화면 —  python 제작/빌드도구/노션화면추출.py\n"
                         f"  그 밖 —  실제로 캡처해서 강의/그림/ 에 두세요")
    raw = p.read_bytes()
    # PNG 머리(IHDR)에서 크기를 직접 읽는다 — 이것 때문에 Pillow 를 끌어오지 않는다
    w, h = struct.unpack(">II", raw[16:24])
    return base64.b64encode(raw).decode("ascii"), w, h


def 화면(이름: str, *표시, 폴더: str = "노션") -> str:
    """이름.png 를 박고, 표시마다 붉은 상자를 얹은 HTML 을 돌려준다.

    표시 = (왼쪽%, 위%, 너비%, 높이%) 또는 (…, "뱃지글자")
    """
    자료, w, h = _읽기(f"{폴더}/{이름}.png")
    img = f'<img src="data:image/png;base64,{자료}" alt="">'
    상자 = ""
    for t in 표시:
        x, y, w, h = t[:4]
        뱃지 = t[4] if len(t) > 4 else None
        상자 += f'<i style="left:{x}%;top:{y}%;width:{w}%;height:{h}%"></i>'
        if 뱃지:
            # 상자 왼쪽 위 모서리에 걸친다 — 상자를 가리지 않는다
            상자 += (f'<b style="left:{x}%;top:{y}%;'
                     f'transform:translate(-58%,-58%)">{뱃지}</b>')
    _ = (w, h)   # 크기는 CSS 가 이미지에 직접 건다 (비율 유지를 브라우저에 맡긴다)
    return f'<div class="shotbox">{img}{상자}</div>'
