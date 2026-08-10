# -*- coding: utf-8 -*-
import asyncio, pathlib, sys
from playwright.async_api import async_playwright
HERE = pathlib.Path(__file__).parent
name = sys.argv[1] if len(sys.argv) > 1 else "Day2덱"
SRC, OUT = HERE / f"{name}.html", HERE / f"PNG_{name}"
OUT.mkdir(exist_ok=True)
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
