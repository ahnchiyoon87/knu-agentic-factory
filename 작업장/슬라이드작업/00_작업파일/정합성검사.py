# -*- coding: utf-8 -*-
"""
슬라이드 제작 문서 정합성 검사
  기준판 HTML · 설명란 3 · 원고 3 · 전체설계도 사이에 모순이 없는지 본다.
  실행:  python 정합성검사.py
"""
import pathlib, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = pathlib.Path(__file__).resolve().parent.parent      # ...\슬라이드
DAY1 = ROOT / "Day1"
DESCS = ["Day1_오리엔테이션_[설명란].md", "Day1_덱A_[설명란].md", "Day1_덱B_[설명란].md"]
SCRIPTS = ["Day1_오리엔테이션_[첨부]원고.md", "Day1_덱A_[첨부]원고.md", "Day1_덱B_[첨부]원고.md"]
REF_HTML = ROOT / "00_작업파일" / "기준판_원본.html"

# 폐기된 어휘 — 문서 어디에도 남아 있으면 안 된다(금지문 안에서도).
# 이름이 남아 있으면 NotebookLM이 그 이름을 따라간다.
BANNED = ["초대형", "대수치", "대문구", "핵심 수치", "색면", "연한 남색 바탕",
          "남색 띠", "굵은 막대", "가로 막대", "고스트", "좌우 색면"]

# 기준판이 정의한 여덟 형식. 설명란의 레이아웃 번호는 이 안에서만 나와야 한다.
FORMS = {1: "표지형", 2: "구간 표지형", 3: "큰 그림 + 짧은 글", 4: "번호 레일형",
         5: "나란히 비교형", 6: "표형", 7: "낱말 나열형", 8: "가는 선 그래프형"}

fail = []
def bad(m): fail.append(m); print("  ✗", m)
def ok(m):  print("  ✓", m)

print("\n[1] 폐기 어휘가 남아 있는가")
n0 = len(fail)
for fn in DESCS + SCRIPTS:
    p = DAY1 / fn
    if not p.exists(): bad(f"{fn} 없음"); continue
    t = p.read_text(encoding='utf-8')
    hits = [w for w in BANNED if w in t]
    if hits: bad(f"{fn}: {', '.join(hits)}")
p = ROOT / "00_전체설계도_덱구성표.md"
if p.exists():
    hits = [w for w in BANNED if w in p.read_text(encoding='utf-8')]
    if hits: bad(f"전체설계도: {', '.join(hits)}")
if len(fail) == n0: ok("전 문서에서 폐기 어휘 0")

print("\n[2] 공통 규격 블록이 세 설명란에서 동일한가")
blocks = {}
for fn in DESCS:
    t = (DAY1 / fn).read_text(encoding='utf-8')
    try:
        s = t.index("# 기준판 8종 — 레이아웃 번호"); e = t.index("## 무대 설정 (4일 내내 고정")
        blocks[fn] = t[s:e]
    except ValueError: bad(f"{fn}: 공통 규격 블록을 찾지 못함")
if len(blocks) == 3:
    v = list(blocks.values())
    if v[0] == v[1] == v[2]: ok(f"세 설명란의 공통 규격이 완전히 동일 ({len(v[0])}자)")
    else:
        for a in range(3):
            for b in range(a + 1, 3):
                if v[a] != v[b]: bad(f"공통 규격 불일치: {DESCS[a]} ↔ {DESCS[b]}")

print("\n[3] 레이아웃 번호가 기준판 8종 안에 있는가")
for fn in DESCS:
    t = (DAY1 / fn).read_text(encoding='utf-8')
    used = {}
    for m in re.finditer(r"^\*\*레이아웃\*\*\s*(\d+)번\s*\(([^)]+)\)", t, re.M):
        n, name = int(m.group(1)), m.group(2).strip()
        used[n] = used.get(n, 0) + 1
        if n not in FORMS: bad(f"{fn}: 없는 형식 {n}번")
        elif FORMS[n] not in name: bad(f"{fn}: {n}번 이름 불일치 — '{FORMS[n]}' vs '{name}'")
    tot, pages = sum(used.values()), len(re.findall(r"^# O?\d+페이지", t, re.M))
    if tot != pages: bad(f"{fn}: 페이지 {pages}장인데 레이아웃 지정 {tot}건")
    else: ok(f"{fn}: {pages}장 · " + " ".join(f"{k}번×{v}" for k, v in sorted(used.items())))

print("\n[4] 기준판 HTML이 여덟 형식을 모두 갖췄는가")
if not REF_HTML.exists():
    bad("기준판 HTML 없음")
else:
    h = REF_HTML.read_text(encoding='utf-8')
    ids = re.findall(r'class="id">(\d+)\s*·\s*([^<]+)<', h)
    if len(ids) != 8: bad(f"기준판 장수 {len(ids)} (8이어야 함)")
    mism = [f"{n}번 '{nm.strip()}'" for n, nm in ids if FORMS.get(int(n)) != nm.strip()]
    if mism: bad("기준판 이름 불일치: " + ", ".join(mism))
    elif len(ids) == 8: ok("기준판 8장 이름이 설명란 표와 일치")

print("\n[5] 배경 규정이 한 가지로 통일됐는가")
n5 = len(fail)
for fn in DESCS:
    t = (DAY1 / fn).read_text(encoding='utf-8')
    if "모든 장의 바탕은 순백" not in t: bad(f"{fn}: 배경 규정 문장 없음")
    if re.search(r"바탕을 (연한|짙은) 남색으로 만들", t): bad(f"{fn}: 옛 배경 금지문이 남음")
if len(fail) == n5: ok("세 설명란 모두 '순백 + 표지형만 남색' 한 가지 규정")

print("\n[6] 원고에 디자인 지시가 남아 있는가")
n6 = len(fail)
DW = ["레이아웃", "핵심 수치", "대문구", "대수치", "좌측 대", "중앙 대"]
for fn in SCRIPTS:
    t = (DAY1 / fn).read_text(encoding='utf-8')
    hits = [w for w in DW if w in t]
    if hits: bad(f"{fn}: {', '.join(hits)}")
if len(fail) == n6: ok("원고 3개에 디자인 지시 없음 (내용만)")

print("\n[7] 중복 금지 규칙이 세 설명란에 들어 있는가")
n7 = len(fail)
for fn in DESCS:
    if "한 가지 사실은 화면에 한 번만" not in (DAY1 / fn).read_text(encoding='utf-8'):
        bad(f"{fn}: 중복 금지 규칙 없음")
if len(fail) == n7: ok("세 설명란 모두 중복 금지 규칙 포함")

print("\n" + "═" * 54)
print(f"  {'모순 없음 — 전 항목 통과' if not fail else f'모순 {len(fail)}건'}")
print("═" * 54)
sys.exit(1 if fail else 0)
