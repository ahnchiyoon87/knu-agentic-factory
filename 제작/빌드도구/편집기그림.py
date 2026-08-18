# -*- coding: utf-8 -*-
"""실제 파일 내용 → VS Code 편집기 화면 그림 (PNG)

★ 터미널그림.py 와 같은 원칙의 **재현 그림**이다.
   코드 영역의 글자는 **실제 파일에서 그대로 읽는다** — 지어낸 코드는 넣지 않는다.
   틀(탐색기·탭·줄번호)만 VS Code 다크 테마 실측 색으로 그린다.

쓰는 법
    uv run --with playwright 편집기그림.py detect     → 실습_2_detect열기.png
    uv run --with playwright 편집기그림.py config     → 실습_3_config.png
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
나갈곳 = REPO / "강의" / "그림" / "실습"

# ── VS Code Dark 실측 색 ────────────────────────────────────────────────────
배경, 사이드, 탭줄, 경계 = "#1E1E1E", "#252526", "#2D2D2D", "#3C3C3C"
본문, 줄번호, 주석, 문자열 = "#D4D4D4", "#6E7681", "#6A9955", "#CE9178"
키워드, 함수, 숫자색, 상수 = "#C586C0", "#DCDCAA", "#B5CEA8", "#569CD6"


def 색칠(줄: str) -> str:
    """파이썬/JSON 한 줄을 VS Code 색으로. 단순 규칙 — 이 두 장면에 충분한 만큼만."""
    t = html.escape(줄)
    if t.lstrip().startswith("#"):
        return f'<span style="color:{주석}">{t}</span>'
    t = re.sub(r"(&quot;.*?&quot;|&#x27;.*?&#x27;)",
               rf'<span style="color:{문자열}">\1</span>', t)
    t = re.sub(r"\b(def|return|if|for|in|is|not|None|True|False|import|from)\b",
               rf'<span style="color:{키워드}">\1</span>', t)
    t = re.sub(r"\b(\d+\.?\d*)\b", rf'<span style="color:{숫자색}">\1</span>', t)
    return t


def 그리기(제목: str, 트리: list[tuple[int, str, bool]], 파일탭: str,
          코드: list[str], 첫줄번호: int, 강조줄: int | None, 나갈이름: str) -> None:
    from playwright.sync_api import sync_playwright

    나무 = ""
    for 깊이, 이름, 선택 in 트리:
        bg = "background:#37373D;" if 선택 else ""
        화살 = "▸ " if 이름.endswith("/") and not 선택 else ("▾ " if 이름.endswith("/") else "")
        나무 += (f'<div style="padding:3px 0 3px {14 + 깊이 * 16}px;{bg}'
                f'color:#CCCCCC">{화살}{html.escape(이름.rstrip("/"))}</div>')

    줄들 = ""
    for i, 줄 in enumerate(코드):
        번호 = 첫줄번호 + i
        bg = "background:#2A2D2E;" if 강조줄 == 번호 else ""
        줄들 += (f'<div style="display:flex;{bg}">'
                f'<span style="width:44px;text-align:right;padding-right:16px;'
                f'color:{줄번호};flex:none">{번호}</span>'
                f'<span style="white-space:pre">{색칠(줄)}</span></div>')

    높이 = max(300, 58 + len(코드) * 20 + 26)
    페이지 = f"""<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box }}
  body {{ background:{배경}; width:1360px;
         font-family:"Malgun Gothic",sans-serif; font-size:13px }}
  .mono {{ font-family:Consolas,"DotumChe",monospace; font-size:14px; line-height:20px }}
</style>
<div style="display:flex;height:{높이}px">
  <div style="width:52px;background:#333333;flex:none;padding-top:12px;text-align:center">
    <div style="font-size:20px;color:#FFFFFF;margin-bottom:18px">&#128459;</div>
    <div style="font-size:20px;color:#858585;margin-bottom:18px">&#128269;</div>
  </div>
  <div style="width:238px;background:{사이드};flex:none;border-right:1px solid {경계}">
    <div style="padding:10px 14px;color:#BBBBBB;font-size:11px;letter-spacing:.06em">탐색기</div>
    <div style="padding:4px 14px;color:#CCCCCC;font-weight:700;font-size:12px">▾ {제목}</div>
    {나무}
  </div>
  <div style="flex:1;display:flex;flex-direction:column">
    <div style="background:{탭줄};display:flex">
      <div style="background:{배경};color:#FFFFFF;padding:8px 16px;font-size:13px;
                  border-top:1px solid #0078D4">{html.escape(파일탭)}</div>
    </div>
    <div class="mono" style="flex:1;padding:10px 0;overflow:hidden">{줄들}</div>
  </div>
</div>"""

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1360, "height": 높이})
        경로 = 나갈곳 / 나갈이름
        임시 = 경로.with_suffix(".html")
        임시.write_text(페이지, encoding="utf-8")
        pg.goto(임시.as_uri()); pg.wait_for_timeout(400)
        pg.screenshot(path=str(경로))
        b.close(); 임시.unlink()
    print(f"  {나갈이름}  ({len(코드)}줄)")


def 장면_detect() -> None:
    src = (REPO / "강의" / "2일차" / "실습" / "detect.py").read_text(encoding="utf-8")
    줄들 = src.splitlines()
    # 「빈칸 1」 표식이 있는 줄을 실제로 찾아 그 앞뒤를 자른다 — 파일이 바뀌면 그림도 따라온다
    표식 = next(i for i, l in enumerate(줄들) if "빈칸 1" in l)
    시작 = 표식 - 16
    조각 = 줄들[시작:표식 + 5]
    강조 = next(i for i, l in enumerate(줄들) if l.strip().startswith("mean = ...")) + 1
    그리기("K-PRECISION-LAB",
          [(1, "2일차/", False), (2, "실습/", False), (3, "데이터/", False),
           (3, "정답/", False), (3, "detect.py", True), (3, "내번호.py", False),
           (3, "돌려보기.py", False), (3, "확인.py", False), (1, "3일차/", False)],
          "detect.py", 조각, 시작 + 1, 강조, "실습_2_detect열기.png")


def 장면_config() -> None:
    src = (REPO / "강의" / "3일차" / "실습" / "도구만들기" / "config.json").read_text(encoding="utf-8")
    줄들 = src.splitlines()
    그리기("K-PRECISION-LAB",
          [(1, "2일차/", False), (1, "3일차/", False), (2, "실습/", False),
           (3, "도구만들기/", False), (4, "정답/", False), (4, "agent.py", False),
           (4, "config.json", True), (4, "mcp_server.py", False), (4, "확인.py", False),
           (3, "폐루프/", False)],
          "config.json", 줄들[:26], 1, None, "실습_3_config.png")


if __name__ == "__main__":
    장면 = sys.argv[1] if len(sys.argv) > 1 else "전부"
    if 장면 in ("detect", "전부"):
        장면_detect()
    if 장면 in ("config", "전부"):
        장면_config()
