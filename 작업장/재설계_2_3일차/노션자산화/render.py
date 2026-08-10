# -*- coding: utf-8 -*-
import asyncio, pathlib, sys
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).parent
SRC = HERE / "노션덱_80분.html"
OUT = HERE / "PNG"
OUT.mkdir(exist_ok=True)
want = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else None

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=2)
        await pg.goto(SRC.as_uri())
        await pg.wait_for_timeout(1200)
        els = await pg.query_selector_all(".s")
        print("slides:", len(els))
        for i, el in enumerate(els, 1):
            if want and i not in want:
                continue
            await el.screenshot(path=str(OUT / f"{i:02d}.png"))
        print("done ->", OUT)
        await b.close()

asyncio.run(main())
