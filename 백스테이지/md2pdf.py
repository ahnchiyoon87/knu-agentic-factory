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


def md2html(md: str, 제목: str) -> str:
    out: list[str] = []
    줄들 = md.splitlines()
    i = 0
    while i < len(줄들):
        line = 줄들[i]

        if line.startswith("```"):                                  # 코드블록
            i += 1
            buf = []
            while i < len(줄들) and not 줄들[i].startswith("```"):
                buf.append(줄들[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            i += 1
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
        elif re.match(r"^\s*---+\s*$", line):
            out.append("<hr>")
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

    html_str = md2html(src.read_text(encoding="utf-8"), 제목)
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
