# -*- coding: utf-8 -*-
import asyncio, pathlib, sys
from playwright.async_api import async_playwright
HERE = pathlib.Path(__file__).parent
name = sys.argv[1] if len(sys.argv) > 1 else "1일차덱"
SRC = HERE / f"{name}.html"
# PNG 는 강의할 때 여는 곳에 바로 떨어뜨린다 — 당일/슬라이드/1일차 · 당일/슬라이드/2일차
OUT = HERE.parents[1] / "당일" / "슬라이드" / ("1일차" if name.startswith("1") else "2일차")
OUT.mkdir(parents=True, exist_ok=True)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1700, "height": 1000}, device_scale_factor=1.5)
        await pg.goto(SRC.as_uri()); await pg.wait_for_timeout(900)
        els = await pg.query_selector_all(".s")
        print("slides:", len(els))
        for i, el in enumerate(els, 1):
            await el.screenshot(path=str(OUT / f"{i:02d}.png"))
        print("done"); await b.close()
asyncio.run(main())
