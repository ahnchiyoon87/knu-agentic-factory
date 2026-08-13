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
import io
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


여백 = 1.2        # 상자를 대상보다 이만큼(%) 키운다 — 테두리가 글자에 닿지 않게
최소간격 = 1.0     # 세로로 이웃한 상자 사이에 이만큼(%)은 비운다
최소폭 = 64.0      # 잘라낸 그림이 원본의 이만큼(%)보다 좁아지지 않게 — 맥락 보존
최소높이 = 88.0    # 낮게 잡으면 자른 자리가 글자 한가운데를 지나 반 토막이 보인다


def _다듬기(항목):
    """여백을 주고, 화면 밖으로 나가지 않게 자르고, 위아래로 붙은 것을 벌린다.

    대상에 딱 붙여 그리면 테두리가 글자를 물고, 상자끼리 맞닿아 지저분해진다.
    좌표를 장마다 손으로 다시 만지는 대신 여기서 한 번에 정리한다.
    """
    결과 = []
    for x, y, w, h, 뱃지 in 항목:
        x2, y2 = x + w, y + h
        x, y = max(0.5, x - 여백), max(0.5, y - 여백)
        x2, y2 = min(99.5, x2 + 여백), min(99.5, y2 + 여백)
        결과.append([x, y, x2 - x, y2 - y, 뱃지])

    # 위에서부터 훑으며, 앞 상자의 아래끝과 겹치면 뒷 상자의 시작을 내린다
    차례 = sorted(range(len(결과)), key=lambda i: 결과[i][1])
    for a, b in zip(차례, 차례[1:]):
        아래끝 = 결과[a][1] + 결과[a][3]
        가로겹침 = (결과[a][0] < 결과[b][0] + 결과[b][2]
                    and 결과[b][0] < 결과[a][0] + 결과[a][2])
        if 가로겹침 and 결과[b][1] < 아래끝 + 최소간격:
            밀기 = 아래끝 + 최소간격 - 결과[b][1]
            결과[b][1] += 밀기
            결과[b][3] = max(2.5, 결과[b][3] - 밀기)
    return 결과


def _잘라내기(경로: str, 항목, 여유: float, 최소세로: float | None = None):
    """표시한 자리만 남기고 잘라, 그 부분이 크게 그려지게 한다.

    화면 전체를 슬라이드 한쪽에 넣으면 0.3~0.6 배로 줄어서, 원본의 작은 글자가
    4~9px 로 그려진다. 강의장 뒷자리에서는 무엇을 누르라는 건지 안 보인다.
    **볼 곳만 남기면 같은 자리에 훨씬 크게 들어간다.**
    잘린 만큼 표시 좌표도 새 그림 기준으로 다시 계산해 돌려준다.
    """
    from PIL import Image

    p = 그림 / 경로
    im = Image.open(p)
    W, H = im.size

    # 위쪽 여유를 넉넉히 둔다 — 창 제목·표 머리 같은 **여기가 어디인지** 알려 주는
    # 것이 대개 위에 있다. 바싹 자르면 글자는 커지지만 무슨 화면인지 모르게 된다.
    x1 = max(0.0, min(t[0] for t in 항목) - 여유)
    y1 = max(0.0, min(t[1] for t in 항목) - 여유 * 2.2)
    x2 = min(100.0, max(t[0] + t[2] for t in 항목) + 여유)
    y2 = min(100.0, max(t[1] + t[3] for t in 항목) + 여유)

    # 너무 잘게 자르지 않는다 — 조각만 남으면 맥락이 사라진다
    if x2 - x1 < 최소폭:
        가운데 = (x1 + x2) / 2
        x1, x2 = max(0.0, 가운데 - 최소폭 / 2), min(100.0, 가운데 + 최소폭 / 2)
        if x2 - x1 < 최소폭:                     # 가장자리에 붙었으면 반대쪽으로 넓힌다
            x1, x2 = (0.0, 최소폭) if x1 <= 0.01 else (100.0 - 최소폭, 100.0)
    세로한도 = 최소높이 if 최소세로 is None else 최소세로
    if y2 - y1 < 세로한도:
        가운데 = (y1 + y2) / 2
        y1, y2 = max(0.0, 가운데 - 세로한도 / 2), min(100.0, 가운데 + 세로한도 / 2)
        if y2 - y1 < 세로한도:
            y1, y2 = (0.0, 세로한도) if y1 <= 0.01 else (100.0 - 세로한도, 100.0)

    box = (round(x1 / 100 * W), round(y1 / 100 * H),
           round(x2 / 100 * W), round(y2 / 100 * H))
    잘린것 = im.convert("RGB").crop(box)

    새폭, 새높이 = (x2 - x1), (y2 - y1)
    옮김 = [((t[0] - x1) / 새폭 * 100, (t[1] - y1) / 새높이 * 100,
             t[2] / 새폭 * 100, t[3] / 새높이 * 100, t[4]) for t in 항목]

    buf = io.BytesIO()
    잘린것.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii"), 옮김


def 화면(이름: str, *표시, 폴더: str = "노션", 확대: bool = False,
         여유: float = 6.0, 조망: bool = False,
         최소세로: float | None = None) -> str:
    """이름.png 를 박고, 표시마다 붉은 상자를 얹은 HTML 을 돌려준다.

    표시 = (왼쪽%, 위%, 너비%, 높이%) 또는 (…, "뱃지글자")
      좌표는 **대상 요소 그대로** 적는다. 여백과 겹침 정리는 `_다듬기` 가 한다.
      뱃지는 상자 **안쪽** 위 왼쪽에 놓는다 — 밖에 두면 화면 여백에 떠 버린다.
    """
    항목 = [(t[0], t[1], t[2], t[3], t[4] if len(t) > 4 else None) for t in 표시]
    if 확대 and 항목:
        자료, 항목 = _잘라내기(f"{폴더}/{이름}.png", 항목, 여유, 최소세로)
    else:
        자료, _w, _h = _읽기(f"{폴더}/{이름}.png")
    img = f'<img src="data:image/png;base64,{자료}" alt="">'
    상자 = ""
    for x, y, w, h, 뱃지 in _다듬기(항목):
        상자 += f'<i style="left:{x}%;top:{y}%;width:{w}%;height:{h}%"></i>'
        if 뱃지:
            # 번호는 상자 **바깥**에 붙인다 — 안에 넣으면 화면의 글자를 가린다.
            # 왼쪽에 자리가 없으면(화면 가장자리에 붙은 상자) 오른쪽으로 보낸다.
            if x >= 5:
                자리 = f'left:{x}%;transform:translate(-118%,-14%)'
            else:
                자리 = f'left:{x + w}%;transform:translate(18%,-14%)'
            상자 += f'<b style="{자리};top:{y}%">{뱃지}</b>'
    # 조망 = 전체 모양만 보는 장. 작은 글자를 읽을 필요가 없어 크기 검사에서 뺀다.
    표식 = ' data-view="1"' if 조망 else ""
    return f'<div class="shotbox"{표식}>{img}{상자}</div>'
