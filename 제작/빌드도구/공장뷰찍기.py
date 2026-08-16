# -*- coding: utf-8 -*-
"""학생이 보는 공장 화면을 **라이브로** 캡처한다.

    uv run 공장뷰찍기.py S04
    uv run 공장뷰찍기.py S04 실습_2_공장뷰.png

왜 도구로 두나
    「화면은 실제 캡처만」이 이 프로젝트의 절대 규칙이다. 그런데 전에 찍어 둔
    `실습_2_공장뷰.png` 은 **주황 강조 상자가 그림에 구워져** 설비 이름과 AMR 을
    가리고 있었다. 원본이 안 남아 있어 지울 수도 없었다.
    그래서 **주석 없는 원본을 언제든 다시 뽑을 수 있게** 도구로 남긴다.
    강조가 필요하면 그림표시.py 로 따로 얹는다 — 원본은 늘 깨끗하게 둔다.
"""
from __future__ import annotations

import sys
from pathlib import Path

기본서버 = "http://34.64.94.16:8000"
나갈폴더 = Path(__file__).resolve().parents[2] / "강의" / "그림" / "실습"


def 찍기(번호: str, 파일명: str, 서버: str = 기본서버) -> Path:
    from playwright.sync_api import sync_playwright

    주소 = f"{서버}/view?tenant={번호}"
    나갈곳 = 나갈폴더 / 파일명
    나갈폴더.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        b = p.chromium.launch()
        # 학생 화면과 같은 비율로. 2배로 찍어 PDF 에서 글자가 뭉개지지 않게 한다.
        pg = b.new_page(viewport={"width": 1440, "height": 860},
                        device_scale_factor=2)
        pg.goto(주소, wait_until="networkidle")
        # 값이 한 번은 갱신된 화면을 찍는다 — 빈 칸이 찍히면 학생이 헷갈린다
        pg.wait_for_timeout(3000)
        pg.screenshot(path=str(나갈곳))
        b.close()

    print(f"  {파일명}  ({나갈곳.stat().st_size // 1024}KB)  ← {주소}")
    return 나갈곳


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("쓰는 법:  uv run 공장뷰찍기.py <번호> [나갈파일명]")
    찍기(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "실습_2_공장뷰.png")
