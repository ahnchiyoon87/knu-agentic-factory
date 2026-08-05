# -*- coding: utf-8 -*-
# 기준판 자동 검사 — 겹침 / 본문 넘침 / 덮음률 / 본문 하단 미달 / 좌우 쏠림 / 왼쪽 기준선
from playwright.sync_api import sync_playwright
import pathlib, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
src = pathlib.Path(r"D:\work\study\경남대특강\작업장\슬라이드\00_작업파일\기준판_원본.html")
JS = r"""
() => {
 const R=[];
 document.querySelectorAll('section.s').forEach((s,i)=>{
  const sb=s.getBoundingClientRect(), W=sb.width, H=sb.height;
  const head=s.querySelector('.head'), body=s.querySelector('.body'), foot=s.querySelector('.foot');
  const box=e=>{const r=e.getBoundingClientRect();return{l:r.left-sb.left,t:r.top-sb.top,r:r.right-sb.left,b:r.bottom-sb.top};};
  const leaves=[...s.querySelectorAll('*')].filter(e=>{
    if(e.classList.contains('id'))return false;
    const tn=e.tagName.toLowerCase();
    if(tn==='svg')return true;
    if(e.children.length&&tn!=='table')return false;
    return ((e.textContent||'').trim().length>0);
  });
  const zone=e=>{ if(head&&head.contains(e))return 0; if(body&&body.contains(e))return 1; if(foot&&foot.contains(e))return 2; return 3; };
  let overlaps=[];
  for(let a=0;a<leaves.length;a++)for(let b=a+1;b<leaves.length;b++){
    if(zone(leaves[a])===zone(leaves[b]))continue;
    const A=box(leaves[a]),B=box(leaves[b]);
    const ow=Math.min(A.r,B.r)-Math.max(A.l,B.l), oh=Math.min(A.b,B.b)-Math.max(A.t,B.t);
    if(ow>3&&oh>3) overlaps.push([leaves[a].textContent.trim().slice(0,14),leaves[b].textContent.trim().slice(0,14),Math.round(ow),Math.round(oh)]);
  }
  let spill=0, bodygap=0;
  if(body){const bb=box(body); let low=bb.t; leaves.forEach(e=>{if(body.contains(e)){const r=box(e); if(r.b>bb.b+2) spill=Math.max(spill,Math.round(r.b-bb.b)); if(r.b>low) low=r.b;}}); bodygap=Math.round(bb.b-low);}
  const g=8,cols=Math.ceil(W/g),rows=Math.ceil(H/g),cell=new Uint8Array(cols*rows);
  leaves.forEach(e=>{const r=box(e); if(r.r-r.l<2||r.b-r.t<2)return;
    for(let y=Math.max(0,Math.floor(r.t/g));y<=Math.min(rows-1,Math.floor(r.b/g));y++)
     for(let x=Math.max(0,Math.floor(r.l/g));x<=Math.min(cols-1,Math.floor(r.r/g));x++)cell[y*cols+x]=1;});
  const band=(a,b)=>{let n=0,d=0;for(let y=Math.floor(rows*a);y<Math.floor(rows*b);y++)for(let x=0;x<cols;x++){d++;if(cell[y*cols+x])n++;}return d?100*n/d:0;};
  const cb=(a,b)=>{let n=0,d=0;for(let y=0;y<rows;y++)for(let x=Math.floor(cols*a);x<Math.floor(cols*b);x++){d++;if(cell[y*cols+x])n++;}return d?100*n/d:0;};
  R.push({n:i+1,name:(s.querySelector('.id')||{textContent:''}).textContent.split('·').pop().trim(),
    overlaps, spill, bodygap, all:band(0,1), bot:band(.67,1), L:cb(0,.5), R2:cb(.5,1),
    headL:head?Math.round(box(head).l):-1, bodyL:body?Math.round(box(body).l):-1, footL:foot?Math.round(box(foot).l):-1});
 });
 return R;
}
"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1600,"height":900})
    pg.goto(src.as_uri()); pg.wait_for_timeout(900); D=pg.evaluate(JS); b.close()
bad=0
print(f"{'p':>2} {'형식':<14}{'덮음':>5}{'하단':>5}{'좌':>5}{'우':>5}{'넘침':>5}{'하단여백':>7}{'겹침':>5}  {'기준선':<8} 판정")
for r in D:
    v=[]
    if r['overlaps'] and r['n']!=1: v.append('겹침'); bad+=1
    if r['spill']>0:  v.append('본문넘침'); bad+=1
    if r['n']!=1:
        if r['bodygap']>70: v.append('하단빔'); bad+=1
        if r['all']<28: v.append('성김'); bad+=1
        if r['all']>62: v.append('빽빽'); bad+=1
        if abs(r['L']-r['R2'])>32: v.append('좌우쏠림'); bad+=1
    al=[x for x in (r['headL'],r['bodyL'],r['footL']) if x>=0]
    ok='OK' if len(set(al))<=1 else '어긋남'
    if ok!='OK': bad+=1
    print(f"{r['n']:>2} {r['name']:<14}{r['all']:>5.0f}{r['bot']:>5.0f}{r['L']:>5.0f}{r['R2']:>5.0f}{r['spill']:>5}{r['bodygap']:>7}{len(r['overlaps']):>5}  {ok:<8} {'/'.join(v) or '통과'}")
print("\n" + ("전 항목 통과" if bad==0 else f"{bad}건"))
