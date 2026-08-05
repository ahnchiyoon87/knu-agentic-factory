# -*- coding: utf-8 -*-
"""문서 전체에서 제어문자 오염과 깨진 경로 표기를 찾는다."""
import pathlib, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

B = pathlib.Path("D:/work/study/경남대특강/작업장")
SKIP = ("node_modules", "__pycache__", "vendor", "호서대 자료 모음")

targets = []
for pat in ("*.md", "*.html", "*.py"):
    for p in B.rglob(pat):
        if any(s in str(p) for s in SKIP) or p.name == "scanraw.py":
            continue
        targets.append(p)

print("═══ 제어문자 오염 ═══")
bad = 0
for p in targets:
    raw = p.read_bytes()
    lone_cr = raw.count(b"\x0d") - raw.count(b"\x0d\x0a")
    ctrl = sum(raw.count(bytes([c])) for c in list(range(0, 9)) + [11, 12] + list(range(14, 32)))
    if lone_cr or ctrl:
        print(f"  ! {p.relative_to(B)}  고립CR={lone_cr} 기타제어={ctrl}")
        bad += 1
if not bad:
    print("  없음")

print("\n═══ 깨진 경로 표기 ═══")
PAT = [
    (r"(?<!r)ender_ref", "render_ref 앞 백슬래시 유실"),
    (r"작업파일[가-힣a-z]", "폴더명 뒤 구분자 유실"),
    (r"(?<!0)_작업파일", "옛 폴더명 _작업파일"),
]
found = 0
for p in targets:
    t = p.read_text(encoding="utf-8", errors="replace")
    for rx, why in PAT:
        for m in re.finditer(rx, t):
            s = max(0, m.start() - 30)
            print(f"  ! {p.relative_to(B)} — {why}")
            print(f"      …{t[s:m.end()+30]}…".replace("\n", "⏎"))
            found += 1
if not found:
    print("  없음")

print("\n═══ 옛 사실 잔재 ═══")
OLD = ["30년", "세계 최고 수준의 로봇", "아무도 안 보는 16시간",
       "임계값 80℃ — 한 번도", "초대형", "좌우 색면"]
hit = 0
for p in targets:
    t = p.read_text(encoding="utf-8", errors="replace")
    for w in OLD:
        if w in t:
            # 전수조사 기록은 제안서 원문 인용이므로 보존이 맞다
            keep = ("전수조사" in p.name) or (p.suffix==".py") or ("핸드오프" in p.name and w in ("초대형","좌우 색면","세계 최고 수준의 로봇"))
            tag = "  (원문 인용 — 보존)" if keep else ""
            print(f"  {'·' if keep else '!'} {p.relative_to(B)}: {w}{tag}")
            if not keep:
                hit += 1
if not hit:
    print("  없음")

print("\n" + "=" * 52)
print("깨끗함" if (bad == 0 and found == 0 and hit == 0) else f"조치 필요 {bad+found+hit}건")
