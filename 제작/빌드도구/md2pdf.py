"""마크다운 → PDF. 학생이 드라이브에서 **클릭 한 번으로 열 수 있게** 만든다.

    python md2pdf.py <입력.md> <출력.pdf> [제목]

왜 필요한가
    `.md` 를 드라이브에 올리면 미리보기가 안 되고, 받아도 메모장에서
    `**굵게**` `|표|` 가 그대로 보인다. 학생이 이틀 내내 볼 문서다.

무엇으로 만드나
    playwright(크롬 엔진). 슬라이드 렌더링에 이미 쓰고 있어 새로 깔 것이 없다.
    pandoc·LibreOffice 는 이 PC 에 없다.

한글 폰트
    맑은 고딕을 쓴다. 크롬이 시스템 폰트를 그대로 쓰므로 깨지지 않는다.
"""

from __future__ import annotations

import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import html
import re
import sys
from pathlib import Path

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "Malgun Gothic","맑은 고딕",sans-serif; font-size: 10.5pt;
       line-height: 1.75; color: #1a1a1a; }
h1 { font-size: 19pt; border-bottom: 2.5px solid #1b4b8f; padding-bottom: 7px;
     margin: 0 0 16px; color: #14335e; }
h2 { font-size: 14.5pt; margin: 26px 0 10px; color: #1b4b8f;
     border-left: 5px solid #1b4b8f; padding-left: 9px; }
h3 { font-size: 12pt; margin: 18px 0 7px; color: #24405f; }
p { margin: 8px 0; }
code { font-family: Consolas,monospace; font-size: 9.5pt; background: #f0f2f5;
       padding: 1px 4px; border-radius: 3px; color: #b03030; }
pre { background: #f7f8fa; border: 1px solid #dde1e6; border-left: 4px solid #1b4b8f;
      padding: 10px 13px; border-radius: 4px; overflow-x: auto;
      page-break-inside: avoid; margin: 10px 0; }
pre code { background: none; padding: 0; color: #1a1a1a; font-size: 9.5pt; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 9.5pt;
        page-break-inside: avoid; }
th { background: #eef2f7; border: 1px solid #c9d2dc; padding: 7px 9px;
     text-align: left; font-weight: 600; }
td { border: 1px solid #d8dee6; padding: 6px 9px; vertical-align: top; }
blockquote { border-left: 4px solid #f0a500; background: #fffaf0; margin: 12px 0;
             padding: 9px 14px; page-break-inside: avoid; }
img { max-width: 100%; border: 1px solid #c9d2dc; border-radius: 5px;
      margin: 10px 0; page-break-inside: avoid; }
.cap { font-size: 9pt; color: #5a6672; margin: -6px 0 12px; }

/* ── 굵은 글씨가 세 가지 다른 일을 하고 있었다 ────────────────────────────
   ①②③ 조작 단계 · 「안 되면」 같은 구역 이름 · 마무리 한 문장.
   전부 같은 모양이라 어디가 「할 일」이고 어디가 「읽을 것」인지 안 갈렸다.
   셋을 눈으로 구분되게 나눈다. */

/* 학생이 실제로 하는 것 — 제일 눈에 띄어야 한다 */
.step { margin: 15px 0 7px; padding: 7px 12px; font-size: 11pt; font-weight: 700;
        color: #14335e; background: #eaf1f8; border-left: 4px solid #1b4b8f;
        border-radius: 3px; page-break-after: avoid; }

/* 구역 이름 — 작고 조용하게, 위에 선을 그어 구역을 뗀다 */
.label { margin: 20px 0 7px; padding-top: 9px; font-size: 9.5pt; font-weight: 700;
         color: #67717c; letter-spacing: .03em;
         border-top: 1px solid #e2e7ec; page-break-after: avoid; }
.label .x { color: #67717c; font-weight: 400; }

/* 마무리 한 문장 — 그 단계에서 남길 것 */
.punch { margin: 13px 0; padding: 8px 13px; font-weight: 700; color: #1f4636;
         background: #f2f8f4; border-left: 4px solid #4f8f68; border-radius: 3px; }
.punch code { background: #e6f0ea; color: #1f4636; }
/* 「안 되면」 카드 — 한 덩어리가 눈에 보이게 박스로 묶는다.
   두 줄이 그냥 <p> 로 흩어지면 어디까지가 한 항목인지 안 보인다. */
.trouble { border: 1px solid #e6d2d2; border-left: 5px solid #c0392b;
           background: #fdf8f7; border-radius: 4px; padding: 9px 13px;
           margin: 9px 0; page-break-inside: avoid; }
.trouble .t { margin: 0 0 4px; font-weight: 700; color: #8a2020; font-size: 10pt; }
.trouble .t code { background: #f6e7e7; color: #8a2020; }
.trouble .b { margin: 0; font-size: 10pt; }
blockquote p { margin: 4px 0; }
ul, ol { margin: 8px 0; padding-left: 24px; }
li { margin: 4px 0; }
hr { border: 0; border-top: 1px solid #dde1e6; margin: 22px 0; }
strong { color: #14335e; }
h1, h2, h3 { page-break-after: avoid; }
"""


def 인라인(t: str) -> str:
    """굵게·코드·링크만 바꾼다. 순서가 중요하다 — 코드 안은 건드리지 않는다."""
    조각: list[str] = []

    def 보관(m: re.Match) -> str:
        조각.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(조각) - 1}\x00"

    t = re.sub(r"`([^`]+)`", 보관, t)
    t = html.escape(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)          # 링크는 글자만 남긴다
    t = re.sub(r"\x00(\d+)\x00", lambda m: 조각[int(m.group(1))], t)
    return t


# 구역 이름 — 조작이 아니라 「여기부터 이런 내용」을 알리는 표찰이다.
# 조용하게 두고 위에 선만 그어 구역을 뗀다 (굵게 강조하면 조작 단계와 뒤섞인다).
구역이름 = ("먼저 나오는 화면", "이어서 나오는 화면", "나오는 화면",
         "승인 요청 화면", "안 되면", "막혔으면", "읽는 법")


def 특수한줄(l: str) -> bool:
    """문단에 이어 붙이면 안 되는 줄 — 표·목록·그림·코드·**줄 전체가 굵은 것**.

    `**` 로 시작만 하는 줄은 이어지는 문장이다.
    (`**전부 정상**입니다. 원래 …` — 이걸 제외하면 한 문장이 중간에서 벌어진다)
    """
    s = l.strip()
    return (s.startswith(("#", "|", "```", "!", ">", "→", "<!--", "---"))
            or bool(re.fullmatch(r"\*\*[^*].*\*\*", s))     # 줄 전체가 굵은 것만
            or bool(re.match(r"^\s*[-*]\s+", l))
            or bool(re.match(r"^\s*\d+\.\s+", l)))


def md2html(md: str, 제목: str, 기준폴더: Path | None = None) -> str:
    out: list[str] = []
    줄들 = md.splitlines()
    i = 0
    while i < len(줄들):
        line = 줄들[i]

        # 그림 — `![설명](경로)`. 상대 경로는 md 파일 위치 기준으로 절대화한다.
        if m := re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line.strip()):
            설명, 경로 = m.group(1), Path(m.group(2))
            if not 경로.is_absolute() and 기준폴더 is not None:
                경로 = (기준폴더 / 경로).resolve()
            # 그림이 없으면 PDF 에 깨진 자리만 남는다 — 학생이 받는 문서다. 여기서 멈춘다.
            if not 경로.is_file():
                raise SystemExit(f"안내문이 가리키는 그림이 없습니다: {경로}\n"
                                 f"  (원본 캡처를 제작/빌드도구/그림표시.py 로 만들어 두세요)")
            out.append(f'<img src="{경로.as_uri()}" alt="{html.escape(설명)}">')
            if 설명:
                out.append(f'<div class="cap">{html.escape(설명)}</div>')
            i += 1
            continue

        if line.startswith("```"):                                  # 코드블록
            i += 1
            buf = []
            while i < len(줄들) and not 줄들[i].startswith("```"):
                buf.append(줄들[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            i += 1
            continue

        # 주석 — `<!-- 사진 … -->`. 아직 안 찍은 화면의 자리를 가이드에 표시해 둔 것이다.
        # 그냥 두면 인라인()이 `<` 를 이스케이프해 **학생 PDF 에 태그가 그대로 찍힌다.**
        # 코드블록 안의 `<!--` 는 위에서 이미 소비되므로 여기 안 온다.
        if line.strip().startswith("<!--"):
            while i < len(줄들) and "-->" not in 줄들[i]:
                i += 1
            i += 1                                                  # `-->` 가 있는 줄까지 버린다
            continue

        if re.match(r"^\s*\|.*\|\s*$", line):                       # 표
            표 = []
            while i < len(줄들) and re.match(r"^\s*\|.*\|\s*$", 줄들[i]):
                표.append(줄들[i])
                i += 1
            칸 = [[c.strip() for c in r.strip().strip("|").split("|")] for r in 표]
            머리 = 칸[0]
            몸 = [r for r in 칸[1:] if not re.match(r"^[\s:\-]+$", "".join(r))]
            out.append("<table><thead><tr>"
                       + "".join(f"<th>{인라인(c)}</th>" for c in 머리)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{인라인(c)}</td>" for c in r)
                                 + "</tr>" for r in 몸)
                       + "</tbody></table>")
            continue

        if m := re.match(r"^(#{1,4})\s+(.*)$", line):
            n = len(m.group(1))
            out.append(f"<h{min(n,3)}>{인라인(m.group(2))}</h{min(n,3)}>")
        elif line.startswith(">"):
            buf = []
            while i < len(줄들) and 줄들[i].startswith(">"):
                buf.append(줄들[i].lstrip(">").strip())
                i += 1
            out.append("<blockquote>"
                       + "".join(f"<p>{인라인(x)}</p>" for x in buf if x)
                       + "</blockquote>")
            continue
        elif re.match(r"^\s*[-*]\s+", line):
            buf = []
            while i < len(줄들) and re.match(r"^\s*[-*]\s+", 줄들[i]):
                buf.append(re.sub(r"^\s*[-*]\s+", "", 줄들[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{인라인(x)}</li>" for x in buf) + "</ul>")
            continue
        elif re.match(r"^\s*\d+\.\s+", line):
            buf = []
            while i < len(줄들) and re.match(r"^\s*\d+\.\s+", 줄들[i]):
                buf.append(re.sub(r"^\s*\d+\.\s+", "", 줄들[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{인라인(x)}</li>" for x in buf) + "</ol>")
            continue
        # ── 「안 되면」 카드 ──────────────────────────────────────────────
        #    **화면에 뜬 문구**
        #    → 무슨 뜻인가 — 이렇게 하세요
        #    두 줄을 한 박스로 묶는다. 따로 <p> 로 내보내면 경계가 안 보인다.
        elif (re.fullmatch(r"\*\*[^*].*\*\*", line.strip())
              and i + 1 < len(줄들) and 줄들[i + 1].lstrip().startswith("→")):
            제목 = line.strip()[2:-2]
            본문 = 줄들[i + 1].lstrip()[1:].strip()      # `→` 는 표시일 뿐, 지면엔 안 낸다
            i += 2                                      # `line` 은 아직 안 소비됐다 — 둘 다 넘긴다
            out.append(f'<div class="trouble"><p class="t">{인라인(제목)}</p>'
                       f'<p class="b">{인라인(본문)}</p></div>')
            continue
        # ── 조작 단계 — `**① …**`. 학생이 실제로 하는 것이라 제일 세워 둔다
        elif m := re.fullmatch(r"\*\*([①-⑳])\s*(.+?)\*\*", line.strip()):
            out.append(f'<p class="step">{m.group(1)} {인라인(m.group(2))}</p>')

        # ── 구역 이름 — `**안 되면**`, `**나오는 화면** — 덧말`
        elif m := re.fullmatch(r"\*\*(" + "|".join(구역이름) + r")\*\*(.*)", line.strip()):
            덧말 = m.group(2).strip()
            꼬리 = f' <span class="x">{인라인(덧말)}</span>' if 덧말 else ""
            out.append(f'<p class="label">{m.group(1)}{꼬리}</p>')

        # ── 마무리 한 문장 — 줄 전체가 굵고 위 둘이 아닌 것.
        #    코드만 굵은 것(에러 카드 제목)은 여기 안 온다 — 위에서 이미 소비된다.
        elif (re.fullmatch(r"\*\*[^*].*\*\*", line.strip())
              and not line.strip().startswith("**`")):
            out.append(f'<p class="punch">{인라인(line.strip()[2:-2])}</p>')

        elif re.match(r"^\s*---+\s*$", line):
            out.append("<hr>")

        # ── 보통 문단 — **이어지는 줄은 한 문단으로 붙인다.**
        #    한 줄이 곧 한 문단이 되면, 원본에서 보기 좋게 줄바꿈한 자리가
        #    지면에서 문단 나눔이 되어 **한 문장이 중간에서 벌어진다.**
        elif line.strip():
            묶음 = [line.strip()]
            i += 1
            while i < len(줄들) and 줄들[i].strip() and not 특수한줄(줄들[i]):
                묶음.append(줄들[i].strip())
                i += 1
            out.append(f"<p>{인라인(' '.join(묶음))}</p>")
            continue
        elif line.strip():
            out.append(f"<p>{인라인(line)}</p>")
        i += 1

    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{html.escape(제목)}</title><style>{CSS}</style></head>"
            f"<body>{''.join(out)}</body></html>")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    제목 = sys.argv[3] if len(sys.argv) > 3 else dst.stem

    if not src.is_file():
        print(f"입력 파일이 없습니다: {src}", file=sys.stderr)
        return 1

    html_str = md2html(src.read_text(encoding="utf-8"), 제목, 기준폴더=src.parent)
    tmp = dst.with_suffix(".tmp.html")
    tmp.write_text(html_str, encoding="utf-8")

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("playwright 가 없습니다 —  pip install playwright  후  playwright install chromium",
              file=sys.stderr)
        return 1

    dst.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(tmp.resolve().as_uri())
        pg.pdf(path=str(dst), format="A4", print_background=True,
               margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"})
        b.close()
    tmp.unlink(missing_ok=True)
    print(f"  만듦  {dst.name}  ({dst.stat().st_size / 1024:.0f}KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
