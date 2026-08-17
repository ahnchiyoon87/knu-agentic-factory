import sys
from pathlib import Path
sys.path.insert(0, ".")
from md2pdf import md2html
from playwright.sync_api import sync_playwright
강의 = Path(r"D:\work\study\경남대특강\강의")
out = Path(r"C:\Users\roede\AppData\Local\Temp\claude\d--work-study\eadb5193-27d0-492e-bd94-cf14487e7929\scratchpad")
h = md2html((강의/"실습가이드_2일차.md").read_text(encoding="utf-8"), "미리보기", 강의)
(out/"미리보기.html").write_text(h, encoding="utf-8")
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 800, "height": 1000}, device_scale_factor=2)
    pg.goto((out/"미리보기.html").resolve().as_uri()); pg.wait_for_timeout(1000)
    pg.evaluate("""() => {
        const t = [...document.querySelectorAll('h2')].find(x => x.textContent.includes('사람 눈으로'));
        if (t) t.scrollIntoView({block:'start'});
    }""")
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(out/"지면_3번.png"))
    b.close()
print("찍음")
