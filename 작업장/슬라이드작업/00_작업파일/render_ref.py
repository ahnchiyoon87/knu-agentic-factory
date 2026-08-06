from playwright.sync_api import sync_playwright
import pathlib
src = pathlib.Path(r"D:\work\study\경남대특강\작업장\슬라이드\00_작업파일\기준판_원본.html")
out = pathlib.Path(r"D:\work\study\경남대특강\작업장\슬라이드\00_디자인기준판\디자인기준판.pdf")
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1600,"height":900})
    pg.goto(src.as_uri()); pg.wait_for_timeout(1200)
    pg.pdf(path=str(out), width="1600px", height="900px", print_background=True,
           margin={"top":"0","bottom":"0","left":"0","right":"0"})
    for i in range(8):
        pg.locator("section.s").nth(i).screenshot(path=f"ref_{i+1}.png")
    b.close()
print("ok")
