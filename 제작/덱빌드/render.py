# -*- coding: utf-8 -*-
"""덱 HTML 을 장별 PNG 로 찍는다 —  python render.py <덱이름>

PNG 는 pptx 로 묶기 전의 중간물이라 산출물 아래에 둔다(저장소에 안 들어간다).
강의장에서 여는 것은 pptx 하나다 —  빌드도구/pptx만들기.py 가 여기서 읽어 묶는다.
"""
import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).parent
REPO = HERE.parents[1]
name = sys.argv[1] if len(sys.argv) > 1 else "2일차덱"
SRC = REPO / "제작" / "산출물" / "덱" / f"{name}.html"
if not SRC.is_file():                       # 예전 자리(덱빌드 옆)도 받아 준다
    SRC = HERE / f"{name}.html"

이름 = "노션" if name.startswith("노션") else ("2일차" if name.startswith("2") else "3일차")
OUT = REPO / "제작" / "산출물" / "슬라이드" / 이름
OUT.mkdir(parents=True, exist_ok=True)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1700, "height": 1000}, device_scale_factor=1.5)
        await pg.goto(SRC.as_uri())
        await pg.wait_for_timeout(900)
        els = await pg.query_selector_all(".s")
        print("slides:", len(els))
        for i, el in enumerate(els, 1):
            await el.screenshot(path=str(OUT / f"{i:02d}.png"))
        print("done →", OUT)
        await b.close()


asyncio.run(main())
