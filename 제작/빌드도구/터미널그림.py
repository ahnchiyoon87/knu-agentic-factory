# -*- coding: utf-8 -*-
"""터미널 로그 → VS Code 터미널 패널 그림 (PNG)

★ 이 도구가 만드는 것은 **재현 그림**이지 실제 캡처가 아니다.
   원칙은 여전히 「화면은 실제 캡처」다. 강사가 직접 못 찍는 장면에만 쓴다.
   로그 본문은 **실제로 돌려서 나온 것만** 넣는다 — 지어낸 출력은 넣지 않는다.

규격은 강사 PC 의 실제 VS Code 화면(1536×864)에서 픽셀로 재서 뽑았다.
  셀 폭 9.0px · 줄 높이 22px · 배경 #191A1B
  본문 #CCCCCC · 밝은흰 #E5E5E5 · 청록 #11A8CD · 노랑 #F5F543 · 흐림 #727373
  오른쪽 세로 구분선 #2A2B2C

쓰는 법
    uv run 터미널그림.py 원고.txt 실습_2_확인.png

원고 문법 — 한 줄에 하나씩. 대괄호 표시로 색을 준다.
    [y]…[/]  노랑(명령어·warning)      [c]…[/]  청록(경로·버전·주소)
    [w]…[/]  밝은 흰(강조)             [d]…[/]  흐림(부차 정보)
    #프롬프트 D:\경로  →  `PS D:\경로> ` 프롬프트를 자동으로 그린다
    #커서                →  입력 대기 커서(▌)를 그 줄 끝에 둔다
표시가 없으면 본문색(#CCCCCC)으로 나간다.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

# ── 실측 규격 ────────────────────────────────────────────────────────────────
셀폭 = 9.0                      # 등폭 한 칸의 가로 (px) — 실측
줄높이 = 22                      # 한 줄의 세로 (px) — 실측
글자크기 = 셀폭 / 0.5498         # Consolas 의 advance 비율(0.5498)로 역산 → 16.37px
왼여백 = 20
위여백 = 12

배경 = "#191A1B"
본문 = "#CCCCCC"
밝은흰 = "#E5E5E5"
청록 = "#11A8CD"
노랑 = "#F5F543"
흐림 = "#727373"
구분선 = "#2A2B2C"

색표 = {"y": 노랑, "c": 청록, "w": 밝은흰, "d": 흐림}
마크 = re.compile(r"\[([ycwd])\](.*?)\[/\]", re.S)


def 칠하기(줄: str) -> str:
    """`[y]…[/]` 같은 표시를 span 으로 바꾼다. 나머지는 그대로 이스케이프한다."""
    나온다 = []
    끝 = 0
    for m in 마크.finditer(줄):
        나온다.append(html.escape(줄[끝:m.start()]))
        나온다.append(f'<span style="color:{색표[m.group(1)]}">'
                      f'{html.escape(m.group(2))}</span>')
        끝 = m.end()
    나온다.append(html.escape(줄[끝:]))
    return "".join(나온다)


def 한줄(줄: str) -> str:
    """원고 한 줄을 HTML 한 줄로."""
    커서 = False
    if 줄.rstrip().endswith("#커서"):
        줄 = 줄.rstrip()[:-3].rstrip("\n")
        커서 = True

    if 줄.startswith("#프롬프트"):
        경로, _, 뒤 = 줄[len("#프롬프트"):].lstrip().partition(">")
        줄 = f"[w]PS [/][c]{경로.rstrip()}[/][w]> [/]" + 뒤.lstrip()

    본 = 칠하기(줄)
    if 커서:
        본 += f'<span style="background:{본문};color:{배경}">&nbsp;</span>'
    return f'<div class="줄">{본 or "&nbsp;"}</div>'


TEMPLATE = """<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box }}
  html,body {{ background:{배경} }}
  #판 {{
    width:{폭}px; background:{배경}; position:relative;
    padding:{위여백}px 0 14px {왼여백}px;
    font-family:Consolas,'D2Coding','Cascadia Mono','Courier New',monospace;
    font-size:{글자크기}px; line-height:{줄높이}px;
    color:{본문}; letter-spacing:0;
    -webkit-font-smoothing:antialiased;
  }}
  /* 줄 단위로만 pre — #판 에 걸면 HTML 소스의 개행까지 빈 줄로 찍힌다 */
  #판 > div.줄 {{ white-space:pre; height:{줄높이}px }}
  /* 실제 화면 오른쪽 끝의 세로 구분선 */
  #선 {{ position:absolute; top:0; right:8px; width:1px; height:100%; background:{구분선} }}
</style>
<div id="판"><div id="선"></div>{줄들}</div>
"""


def 만들기(원고: Path, 나갈곳: Path, 폭: int = 1076) -> None:
    from playwright.sync_api import sync_playwright

    # utf-8-sig — PowerShell 의 `Out-File -Encoding utf8` 은 BOM 을 붙인다.
    # 그냥 utf-8 로 읽으면 BOM 이 첫 글자에 붙어 `#프롬프트` 를 못 알아본다
    # (첫 줄만 표시가 그대로 찍혔다 — 실제로 당했다).
    줄들 = 원고.read_text(encoding="utf-8-sig").rstrip("\n").split("\n")
    본문html = "".join(한줄(l) for l in 줄들)
    페이지 = TEMPLATE.format(배경=배경, 본문=본문, 구분선=구분선, 폭=폭,
                            위여백=위여백, 왼여백=왼여백,
                            글자크기=f"{글자크기:.2f}", 줄높이=줄높이, 줄들=본문html)

    임시 = 나갈곳.with_suffix(".html")
    임시.write_text(페이지, encoding="utf-8")

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 폭, "height": 200},
                        device_scale_factor=1)
        pg.goto(임시.resolve().as_uri())
        # 규격이 맞는지 스스로 잰다 — 어긋나면 그림이 실제와 달라진다
        잰값 = pg.evaluate("""() => {
            const 판 = getComputedStyle(document.getElementById('판'));
            const s = document.createElement('span');
            s.style.position   = 'absolute';
            s.style.visibility = 'hidden';
            s.style.whiteSpace = 'pre';
            s.style.font       = 판.fontSize + ' ' + 판.fontFamily;   // 폭 제약 없이 글꼴만
            s.textContent      = 'M'.repeat(100);
            document.body.appendChild(s);
            const w = s.getBoundingClientRect().width / 100;
            s.remove();
            return w;
        }""")
        판 = pg.query_selector("#판")
        판.screenshot(path=str(나갈곳))
        b.close()

    임시.unlink(missing_ok=True)
    상태 = "맞음" if abs(잰값 - 셀폭) < 0.15 else f"어긋남 (실측 {셀폭})"
    print(f"  {나갈곳.name}  줄 {len(줄들)}개 · 셀폭 {잰값:.3f}px — {상태}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("쓰는 법:  uv run 터미널그림.py 원고.txt 나갈파일.png")
    만들기(Path(sys.argv[1]), Path(sys.argv[2]))
