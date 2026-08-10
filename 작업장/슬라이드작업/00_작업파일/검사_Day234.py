# -*- coding: utf-8 -*-
"""
Day 2~4 설명란·원고 검사
  실행:  python 검사_Day234.py
"""
import pathlib, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

W = pathlib.Path(__file__).resolve().parent.parent      # ...\슬라이드작업
DECKS = [("Day2", 18), ("Day3", 20), ("Day4", 16)]

FORMS = {1: "표지형", 2: "구간 표지형", 3: "큰 그림 + 짧은 글", 4: "번호 레일형",
         5: "나란히 비교형", 6: "표형", 7: "낱말 나열형", 8: "가는 선 그래프형"}

BANNED = ["초대형", "대수치", "대문구", "핵심 수치", "색면", "연한 남색 바탕",
          "남색 띠", "굵은 막대", "가로 막대", "고스트", "좌우 색면"]

# 실습에서 학생이 직접 발견해야 하는 것 — 슬라이드에 나오면 수업이 깨진다
SPOILER = [
    (r"스파이크.{0,20}(잡|검출|3/3|3건)", "Day3", "스파이크 검출 결과 유출"),
    (r"드리프트.{0,20}(못 잡|안 잡|미탐|미검출)", "Day3", "드리프트 미검출 결과 유출"),
    (r"결측.{0,20}(못 잡|0/121)", "Day3", "결측 검출 결과 유출"),
    (r"빈칸.{0,30}정답은", "Day2", "빈칸 정답 유출 가능"),
]

# 바꾸면 안 되는 실측 수치 (있으면 값이 맞는지 본다)
FACTS = {
    "0.5": "드리프트 기울기(℃/h)", "62": "시작 온도", "64": "종료 온도",
    "80": "경보선", "81": "기본 오탐(하루)", "911": "k=2.0 오탐(하루)",
    "60,480": "CSV 행수", "WO-2026-0801": "정비 작업지시 번호",
    "63": "시연 시작 온도", "53": "시연 하강 온도",
}
TOOLS = ["set_equipment_speed", "stop_equipment", "dispatch_robot", "ack_alarm"]

fail = []
def bad(m): fail.append(m); print("  ✗", m)
def ok(m):  print("  ✓", m)

print("\n[1] 장수와 레이아웃 번호")
blocks = {}
for name, n in DECKS:
    p = W / name / f"{name}_[설명란].md"
    if not p.exists(): bad(f"{name} 설명란 없음"); continue
    t = p.read_text(encoding="utf-8")
    pages = len(re.findall(r"^# \d+페이지", t, re.M))
    used = {}
    for m in re.finditer(r"^\*\*레이아웃\*\*\s*(\d+)번\s*\(([^)]+)\)", t, re.M):
        k, nm = int(m.group(1)), m.group(2).strip()
        used[k] = used.get(k, 0) + 1
        if k not in FORMS: bad(f"{name}: 없는 형식 {k}번")
        elif FORMS[k] not in nm: bad(f"{name}: {k}번 이름 불일치 — '{FORMS[k]}' vs '{nm}'")
    tot = sum(used.values())
    if pages != n: bad(f"{name}: {pages}장 (교안 {n}장이어야 함)")
    elif tot != pages: bad(f"{name}: 페이지 {pages} vs 레이아웃 지정 {tot}")
    else: ok(f"{name}: {pages}장 · " + " ".join(f"{k}번×{v}" for k, v in sorted(used.items())))
    try:
        s = t.index("# 기준판 8종 — 레이아웃 번호"); e = t.index("## 무대 설정 (4일 내내 고정")
        blocks[name] = t[s:e]
    except ValueError: bad(f"{name}: 공통 규격 블록 없음")

print("\n[2] 공통 규격이 Day1과 동일한가")
d1 = (W / "Day1" / "Day1_덱A_[설명란].md").read_text(encoding="utf-8")
s = d1.index("# 기준판 8종 — 레이아웃 번호"); e = d1.index("## 무대 설정 (4일 내내 고정")
base = d1[s:e]
same = [k for k, v in blocks.items() if v == base]
diff = [k for k, v in blocks.items() if v != base]
if diff: bad(f"공통 규격 불일치: {', '.join(diff)}")
else: ok(f"Day1 포함 네 덱의 공통 규격이 완전히 동일 ({len(base)}자)")

print("\n[3] 폐기 어휘")
n3 = len(fail)
for name, _ in DECKS:
    for suffix in ("_[설명란].md", "_[첨부]원고.md"):
        p = W / name / f"{name}{suffix}"
        if not p.exists(): continue
        hits = [w for w in BANNED if w in p.read_text(encoding="utf-8")]
        if hits: bad(f"{p.name}: {', '.join(hits)}")
if len(fail) == n3: ok("Day2~4 전 문서에서 폐기 어휘 0")

print("\n[4] 실습 반전 유출 (학생이 직접 발견해야 하는 것)")
n4 = len(fail)
for name, _ in DECKS:
    for suffix in ("_[설명란].md", "_[첨부]원고.md"):
        p = W / name / f"{name}{suffix}"
        if not p.exists(): continue
        t = p.read_text(encoding="utf-8")
        # 화면에 나가는 글자만 검사 (백틱 안 + 본문 지시). 금지문은 제외.
        body = "\n".join(l for l in t.split("\n") if not l.startswith("> ") and "말하지 마라" not in l and "쓰지 마라" not in l)
        for rx, deck, why in SPOILER:
            if deck == name and re.search(rx, body):
                bad(f"{p.name}: {why}")
if len(fail) == n4: ok("Day3 실습 반전 유출 없음 · Day2 정답 유출 없음")

print("\n[5] 실측 수치 정합")
n5 = len(fail)
d4 = (W / "Day4" / "Day4_[설명란].md").read_text(encoding="utf-8")
missing = [t_ for t_ in TOOLS if t_ not in d4]
if missing: bad(f"Day4: 제어 도구 누락 — {', '.join(missing)}")
else: ok("Day4: 제어 도구 4개 이름 그대로 존재")
for key, why in [("WO-2026-0801", "정비 작업지시"), ("1~3분", "감지 소요"), ("63", "시연 시작"), ("53", "시연 하강")]:
    if key not in d4: bad(f"Day4: {why}({key}) 없음")
d3 = (W / "Day3" / "Day3_[설명란].md").read_text(encoding="utf-8")
for key, why in [("81", "기본 오탐"), ("911", "k=2.0 오탐"), ("60,480", "CSV 행수")]:
    if key not in d3: bad(f"Day3: {why}({key}) 없음")
if len(fail) == n5: ok("Day3·Day4 실측 수치 전부 반영")

print("\n[6] 원고에 디자인 지시가 남아 있는가")
n6 = len(fail)
DW = ["레이아웃", "핵심 수치", "대문구", "대수치", "좌측 대", "중앙 대"]
for name, _ in DECKS:
    p = W / name / f"{name}_[첨부]원고.md"
    if not p.exists(): bad(f"{name} 원고 없음"); continue
    hits = [w for w in DW if w in p.read_text(encoding="utf-8")]
    if hits: bad(f"{p.name}: {', '.join(hits)}")
if len(fail) == n6: ok("원고 3벌에 디자인 지시 없음 (내용만)")

print("\n[7] 장 안에서 같은 말을 두 번 하는가")
STOP = set("그리고 그런데 하지만 이것 저것 우리 여러분 있다 없다 한다 된다 이다 그것 하는 있는 없는 위해 대해 통해 때문 각각 전부 모두 다시 아주 매우 정말 그냥 바로 오늘 내일 어제".split())
def words(x):
    x = re.sub(r"[^\w가-힣 ]", " ", x)
    return {w for w in x.split() if len(w) >= 2 and w not in STOP}
n7 = len(fail)
for name, _ in DECKS:
    t = (W / name / f"{name}_[설명란].md").read_text(encoding="utf-8")
    for m in re.finditer(r"^# (\d+)페이지[^\n]*\n(.*?)(?=\n# |\n▲)", t, re.S | re.M):
        no, body = m.group(1), m.group(2)
        seg = body.split("**삽화**")[0]
        # 대조표는 같은 항목이 「잘 답함」과 「못 답함」 양쪽에 나와야 대조가 성립한다.
        # 이 구조는 반복이 아니라 설계이므로 검사에서 제외한다.
        if "잘 답하는 질문" in seg and "못 답하는 질문" in seg:
            continue
        frags = [re.sub(r"\s+", " ", x).strip()
                 for x in re.findall(r"`([^`]{14,})`", seg)]
        ws = [(f, words(f)) for f in frags if len(words(f)) >= 4]
        for i in range(len(ws)):
            for j in range(i + 1, len(ws)):
                a, b = ws[i][1], ws[j][1]
                inter = a & b
                if inter and len(inter) / min(len(a), len(b)) >= 0.65:
                    bad(f"{name} {no}p: 같은 말 반복 — '{ws[i][0][:26]}' ↔ '{ws[j][0][:26]}'")
if len(fail) == n7: ok("Day2~4 전 장에서 중복 없음")

print("\n" + "═" * 54)
print(f"  {'모순 없음 — 전 항목 통과' if not fail else f'조치 필요 {len(fail)}건'}")
print("═" * 54)
sys.exit(1 if fail else 0)
