# -*- coding: utf-8 -*-
"""덱 전수 검사 — 눈 대신 기계로 잡는다.

    python 레이아웃검사.py              # 세 덱 전부
    python 레이아웃검사.py 노션덱

무엇을 보는가
  ① 슬라이드 밖으로 나간 것            (1600×900 상자 기준, 표지 장식 .rings 는 예외)
  ② 본문(.body) 을 위·아래로 넘은 것    — 제목이나 각주를 침범한다는 뜻
  ③ 잘린 글자                          — 넘쳐서 안 보이는 글이 있는가
  ④ 너무 작은 글자                     — 강의장 뒷자리에서 안 읽힌다
  ⑤ 화면 캡처 속 글자가 읽히는가        — 실제로 그려지는 크기로 환산해서 본다
  ⑥ 강조 상자가 서로 겹치는가
  ⑦ 좌우 기준선 정렬                   — 본문 요소가 좌우 96px 기준을 벗어났는가

왜 이만큼 보는가 — 실행 게이트는 화면을 못 본다. 「폐루프는 일곱 걸음」은 표가 높이를
넘쳐 제목을 가린 채 리허설·검증을 전부 통과했다. 노션 덱은 화면 속 글자가 너무 작아
무엇을 누르라는 건지 안 보이는 채로 나갈 뻔했다.

걸린 장이 하나라도 있으면 종료 코드 1.
"""
import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).parent
덱 = HERE.parents[1] / "제작" / "산출물" / "덱"
names = sys.argv[1:] or ["2일차덱", "3일차덱", "노션덱"]

# 화면 캡처 속 가장 작은 본문 글자는 **원본 그림에서 25px** 이다.
#   (원본 pptx 를 재 보니 7.5pt 였고, 3200px 로 내보내면 1pt = 3.33px 다.
#    눈대중으로 14px 이라고 뒀다가 멀쩡한 장까지 걸렸다 — 값은 재서 넣는다.)
화면글자_원본 = 25.0
# 슬라이드(1600px 폭) 위에서 이보다 작게 그려지면 강의장 뒷자리에서 못 읽는다.
# 본문이 29px 이므로 그 절반이 하한이다.
화면글자_최소 = 14.0
본문글자_최소 = 22.0

JS = r"""
() => {
  const TOL = 3;
  const out = [];
  const 글 = el => (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 34);

  document.querySelectorAll('.s').forEach((s, i) => {
    const sr = s.getBoundingClientRect();
    const issues = [];

    s.querySelectorAll('*').forEach(el => {
      if (el.closest('.rings')) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (r.right > sr.right + TOL || r.bottom > sr.bottom + TOL || r.left < sr.left - TOL)
        issues.push('슬라이드 밖: <' + el.tagName.toLowerCase() + '> ' + 글(el));
    });

    const body = s.querySelector('.body');
    if (body) {
      const br = body.getBoundingClientRect();
      body.querySelectorAll('*').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return;
        if (r.top < br.top - TOL || r.bottom > br.bottom + TOL)
          issues.push('본문 넘침(제목·각주 침범): <' + el.tagName.toLowerCase() + '> ' + 글(el));
      });
    }

    // ③ 잘린 글자 — **잘라내는 상자** 안에서 내용이 넘친 곳만.
    //    overflow 가 visible 이면 넘쳐도 글자는 보인다. 그것까지 세면 오탐만 쌓인다.
    s.querySelectorAll('p, td, th, strong, span, div, h1, h3').forEach(el => {
      if (!el.textContent || !el.textContent.trim()) return;
      if (el.children.length) return;
      const ov = getComputedStyle(el);
      const 자름 = e => ['hidden', 'clip', 'auto', 'scroll'].includes(e);
      if (!자름(ov.overflowY) && !자름(ov.overflowX)) return;
      if (el.scrollHeight > el.clientHeight + 4 || el.scrollWidth > el.clientWidth + 4)
        issues.push('글자 잘림: ' + 글(el));
    });

    // ④ 너무 작은 글자 (슬라이드 자체의 글)
    s.querySelectorAll('p, td, th, li, strong, .sub, .foot, .st span').forEach(el => {
      if (!el.textContent || !el.textContent.trim()) return;
      if (el.children.length) return;
      const fs = parseFloat(getComputedStyle(el).fontSize);
      if (fs < __본문최소__)
        issues.push('글자가 작다 ' + fs.toFixed(0) + 'px: ' + 글(el));
    });

    // ⑤ 화면 캡처가 얼마나 줄어 그려지는가 → 그 안 글자가 읽히는가
    s.querySelectorAll('.shotbox img').forEach(el => {
      // 조망용(전체 모양만 보는 장)은 작은 글자를 읽을 필요가 없다 — 건너뛴다.
      if (el.closest('.shotbox').dataset.view === '1') return;
      const r = el.getBoundingClientRect();
      const 배율 = r.width / el.naturalWidth;
      const 예상 = __화면원본__ * 배율;
      if (예상 < __화면최소__)
        issues.push('화면 속 글자가 작다 — 배율 ' + 배율.toFixed(2)
                    + ' · 환산 ' + 예상.toFixed(1) + 'px (그린 폭 ' + r.width.toFixed(0) + ')');
    });

    // ⑥ 강조 상자끼리 겹침
    const 상자 = [...s.querySelectorAll('.shotbox i')].map(e => e.getBoundingClientRect());
    for (let a = 0; a < 상자.length; a++)
      for (let b = a + 1; b < 상자.length; b++) {
        const A = 상자[a], B = 상자[b];
        const w = Math.min(A.right, B.right) - Math.max(A.left, B.left);
        const h = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top);
        if (w > 2 && h > 2) issues.push('강조 상자 겹침 ' + (a + 1) + '·' + (b + 1));
      }

    // ⑦ 좌우 기준선 — 본문 직계 요소가 왼쪽 기준을 벗어났는가
    if (body) {
      const bl = body.getBoundingClientRect().left;
      [...body.children].forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width === 0) return;
        if (r.left < bl - TOL) issues.push('왼쪽 기준선 벗어남: ' + 글(el));
      });
    }

    if (issues.length) out.push({slide: i + 1, issues: [...new Set(issues)].slice(0, 6)});
  });
  return out;
}
"""


async def main() -> None:
    js = (JS.replace("__본문최소__", str(본문글자_최소))
            .replace("__화면원본__", str(화면글자_원본))
            .replace("__화면최소__", str(화면글자_최소)))
    bad = 0
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1700, "height": 1000},
                              device_scale_factor=1.5)
        for name in names:
            await pg.goto((덱 / f"{name}.html").as_uri())
            await pg.wait_for_timeout(900)
            res = await pg.evaluate(js)
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
