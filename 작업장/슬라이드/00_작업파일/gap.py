# -*- coding: utf-8 -*-
# 줄간격 검사 — 인접한 글줄 사이가 글자 크기 대비 과하게 벌어졌는지
from playwright.sync_api import sync_playwright
import pathlib, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
src = pathlib.Path(r"D:\work\study\경남대특강\작업장\슬라이드\00_작업파일\기준판_원본.html")
JS = r"""
() => {
 const out=[];
 document.querySelectorAll('section.s').forEach((s,i)=>{
  const sb=s.getBoundingClientRect();
  const blocks=[...s.querySelectorAll('.body p, .body .rt span, .sub')];
  const lines=[];
  blocks.forEach(b=>{
    const fs=parseFloat(getComputedStyle(b).fontSize);
    const rng=document.createRange(); rng.selectNodeContents(b);
    [...rng.getClientRects()].forEach(r=>{
      if(r.height<4||r.width<4)return;
      lines.push({top:r.top-sb.top, fs, txt:(b.textContent||'').trim().slice(0,18)});
    });
  });
  lines.sort((a,b)=>a.top-b.top);
  const bad=[];
  for(let k=1;k<lines.length;k++){
    const g=lines[k].top-lines[k-1].top;
    const fs=Math.max(lines[k].fs,lines[k-1].fs);
    if(g>0 && g < fs*4 && g > fs*2.05) bad.push({gap:Math.round(g), fs:Math.round(fs), ratio:+(g/fs).toFixed(2), txt:lines[k].txt});
  }
  out.push({n:i+1, name:(s.querySelector('.id')||{textContent:''}).textContent.split('·').pop().trim(), bad});
 });
 return out;
}
"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1600,"height":900})
    pg.goto(src.as_uri()); pg.wait_for_timeout(900); D=pg.evaluate(JS); b.close()
n=0
for r in D:
    if r['bad']:
        n+=len(r['bad']); print(f"p{r['n']} {r['name']}")
        for x in r['bad']: print(f"    간격 {x['gap']}px / 글자 {x['fs']}px = {x['ratio']}배   '{x['txt']}'")
print(f"\n{'과한 줄간격 없음' if n==0 else str(n)+'건'}  (기준: 글자 크기의 2.05배 초과)")
