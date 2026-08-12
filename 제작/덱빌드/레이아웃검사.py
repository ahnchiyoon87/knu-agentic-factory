# -*- coding: utf-8 -*-
"""덱 레이아웃 전수 검사 — 눈 대신 기계로 삐져나옴·겹침을 잡는다.

    python 레이아웃검사.py              # 1일차덱·2일차덱 둘 다
    python 레이아웃검사.py 2일차덱

왜 있나 — 「폐루프는 일곱 걸음」(구 2일차 31장)이 표가 슬라이드 높이를 넘쳐
제목을 가리고 각주와 겹친 채로 리허설·검증을 전부 통과했다. 실행 게이트는
화면 겹침을 못 본다. 그래서 렌더링된 HTML 에서 장마다 두 가지를 잰다:

  ① 슬라이드 밖으로 나간 요소 (1600×900 상자 기준, 표지 장식 .rings 는 예외)
  ② 본문(.body) 상자를 위·아래로 넘은 요소 — 제목이나 각주를 침범한다는 뜻

걸린 장이 하나라도 있으면 종료 코드 1. render.py 로 PNG 를 뽑기 전에 돌린다.
"""
import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).parent
names = sys.argv[1:] or ["1일차덱", "2일차덱"]

JS = """
() => {
  const TOL = 3;
  const out = [];
  document.querySelectorAll('.s').forEach((s, i) => {
    const sr = s.getBoundingClientRect();
    const issues = [];
    s.querySelectorAll('*').forEach(el => {
      if (el.closest('.rings')) return;               // 표지 동심원 — 일부러 밖
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (r.right > sr.right + TOL || r.bottom > sr.bottom + TOL || r.left < sr.left - TOL)
        issues.push('슬라이드 밖: <' + el.tagName.toLowerCase() + '> '
                    + (el.textContent || '').trim().slice(0, 34));
    });
    const body = s.querySelector('.body');
    if (body) {
      const br = body.getBoundingClientRect();
      body.querySelectorAll('*').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return;
        if (r.top < br.top - TOL || r.bottom > br.bottom + TOL)
          issues.push('본문 넘침(제목·각주 침범): <' + el.tagName.toLowerCase() + '> '
                      + (el.textContent || '').trim().slice(0, 34));
      });
    }
    if (issues.length) out.push({slide: i + 1, issues: [...new Set(issues)].slice(0, 5)});
  });
  return out;
}
"""


async def main() -> None:
    bad = 0
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1700, "height": 1000},
                              device_scale_factor=1.5)
        for name in names:
            await pg.goto((HERE / f"{name}.html").as_uri())
            await pg.wait_for_timeout(900)
            res = await pg.evaluate(JS)
            n = await pg.evaluate("document.querySelectorAll('.s').length")
            print(f"{name}: {n}장 검사 · 걸린 장 {len(res)}개")
            for r in res:
                bad += 1
                print(f"  {r['slide']:>2}장:")
                for msg in r["issues"]:
                    print(f"     - {msg}")
        await b.close()
    sys.exit(1 if bad else 0)


asyncio.run(main())
