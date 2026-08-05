# -*- coding: utf-8 -*-
"""설명란 각 페이지 안에서 같은 말을 두 번 하는 곳을 찾는다.
   화면 글자(백틱 안)끼리 내용어가 얼마나 겹치는지로 판정한다."""
import re, sys, io, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
D = pathlib.Path(r"D:\work\study\경남대특강\작업장\슬라이드\Day1")
FILES = ["Day1_오리엔테이션_[설명란].md", "Day1_덱A_[설명란].md", "Day1_덱B_[설명란].md"]

STOP = set("그리고 그런데 하지만 이것 저것 우리 여러분 있다 없다 한다 된다 이다 그것 하는 있는 없는 위해 대해 통해 때문 만약 각각 전부 모두 다시 아주 매우 정말 그냥 바로 오늘 내일 어제".split())
def words(s):
    s = re.sub(r"[^\w가-힣 ]", " ", s)
    return {w for w in s.split() if len(w) >= 2 and w not in STOP}

def blocks(t):
    """페이지별로 (제목, [화면글자 조각])"""
    out = []
    for m in re.finditer(r"^# (O?\d+페이지[^\n]*)\n(.*?)(?=\n# |\n▲)", t, re.S | re.M):
        head, body = m.group(1), m.group(2)
        seg = body.split("**삽화**")[0]
        frags = [(f, re.sub(r"\s+", " ", x).strip())
                 for f, x in re.findall(r"(?:^|\n)\s*-?\s*([^`\n]{0,28}?):?\s*`([^`]{12,})`", seg)]
        lbl = re.findall(r"`([^`]{4,})`", body.split("**삽화**")[-1] if "**삽화**" in body else "")
        out.append((head, frags, [re.sub(r"\s+", " ", x).strip() for x in lbl]))
    return out

total = 0
for fn in FILES:
    t = (D / fn).read_text(encoding="utf-8")
    hits = []
    for head, frags, lbls in blocks(t):
        seen = [(f, s, words(s)) for f, s in frags if len(words(s)) >= 3]
        for i in range(len(seen)):
            for j in range(i + 1, len(seen)):
                a, b = seen[i], seen[j]
                inter = a[2] & b[2]
                if not inter: continue
                ratio = len(inter) / min(len(a[2]), len(b[2]))
                if ratio >= 0.6:
                    hits.append((head, a[1][:34], b[1][:34], round(ratio, 2), sorted(inter)[:4]))
        # 라벨 ↔ 화면글자
        for L in lbls:
            wl = words(L)
            if len(wl) < 2: continue
            for f, s, ws in seen:
                inter = wl & ws
                if len(inter) / len(wl) >= 0.7:
                    hits.append((head, "[라벨] " + L[:28], s[:34], round(len(inter)/len(wl), 2), sorted(inter)[:4]))
    print(f"\n── {fn} ──")
    if not hits: print("   겹치는 곳 없음")
    for h in hits:
        total += 1
        print(f"   {h[0]}")
        print(f"      A: {h[1]}")
        print(f"      B: {h[2]}   겹침 {h[3]}  {h[4]}")
print(f"\n{'='*50}\n중복 의심 {total}건\n{'='*50}")
