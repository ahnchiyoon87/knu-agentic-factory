# -*- coding: utf-8 -*-
"""전체설계도 §6 첫 문단의 제어문자 오염을 바이트 단위로 고친다."""
import pathlib, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p = pathlib.Path("D:/work/study/경남대특강/작업장/슬라이드/00_전체설계도_덱구성표.md")
raw = p.read_bytes()

lone_cr = raw.count(b"\x0d") - raw.count(b"\x0d\x0a")
print("고립된 CR:", lone_cr)

NEW = (
    "`00_디자인기준판` 폴더의 **디자인기준판.pdf** 8장이 목표 디자인이다.\n"
    "소스는 `00_작업파일` 폴더의 **기준판_원본.html**이고, 같은 폴더의 **render_ref.py**로 PDF를 다시 뽑는다.\n"
    "고친 뒤에는 반드시 **check.py · gap.py · dup.py · 정합성검사.py**를 돌린다."
).encode("utf-8")

# §6 제목 다음 첫 문단을 통째로 교체
head = "## 6. 디자인 규격 (v2 — 2026-08-05 전면 개정)".encode("utf-8")
mark = "### 왜 개정했는가".encode("utf-8")
i = raw.find(head)
j = raw.find(mark)
if i < 0 or j < 0:
    print("앵커를 못 찾음"); sys.exit(1)

before = raw[: i + len(head)]
after = raw[j:]
raw2 = before + b"\r\n\r\n" + NEW + b"\r\n\r\n" + after
p.write_bytes(raw2)

chk = p.read_bytes()
print("복구 후 고립 CR:", chk.count(b"\x0d") - chk.count(b"\x0d\x0a"))
t = p.read_text(encoding="utf-8")
k = t.index("## 6. 디자인 규격")
print("─── 결과 ───")
print(t[k : k + 260])
