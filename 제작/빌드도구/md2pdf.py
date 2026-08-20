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
/* ─────────────────────────────────────────────────────────────────────────
   역할마다 생김새가 달라야 한다.
   전에는 큰 단계·작은 단계·터미널 명령·파일에 쓰는 코드가 **전부 같은 회색 상자**라
   학생이 「치는 것」과 「쓰는 것」을 구별하지 못했다.
   ───────────────────────────────────────────────────────────────────────── */

@page { size: A4; margin: 20mm 17mm 18mm; }

body { font-family: "Malgun Gothic","맑은 고딕",sans-serif; font-size: 10.5pt;
       line-height: 1.85; color: #1f2429;
       /* 한국어는 어절 단위로 끊는다 — 안 두면 낱말이 두 줄로 쪼개진다. */
       word-break: keep-all; overflow-wrap: break-word; }

/* 한글이 든 명령을 Consolas 로만 찍으면 한글이 다른 글꼴로 튀어 자간이 벌어진다.
   («cd 2일차/실습» 이 «cd  2일차 /실 습» 으로 보이던 자리)
   DotumChe(돋움체)는 한글 고정폭이라 폭이 맞는다. */
:root { --mono: Consolas,"DotumChe","돋움체","Cascadia Mono",monospace; }

h1 { font-size: 20pt; margin: 0 0 26px; padding-bottom: 10px; color: #14335e;
     border-bottom: 3px solid #1b4b8f; letter-spacing: -.01em; }

/* 큰 단계 — 여기서 확실히 끊긴다. 위에 굵은 줄, 아래위로 넉넉히. */
h2 { font-size: 15.5pt; color: #14335e; letter-spacing: -.01em;
     margin: 40px 0 16px; padding: 15px 0 0;
     border-top: 2.5px solid #1b4b8f; }

h3 { font-size: 12pt; margin: 34px 0 10px; color: #24405f; }

/* 소단계 문단 — `**1. …**` 시작. 위를 띄워 단계 경계가 지면에서 보인다. */
p.nstep { margin-top: 30px; }

p  { margin: 11px 0; }
ul, ol { margin: 11px 0; padding-left: 25px; }
li { margin: 6px 0; }

/* 글 속의 짧은 코드 */
code { font-family: var(--mono); font-size: 9.5pt; background: #eef1f5;
       padding: 1px 5px; border-radius: 3px; color: #a83232;
       letter-spacing: 0; }

/* ── 터미널에 치는 것 — 검은 화면. 한눈에 「이건 친다」 ─────────────────── */
.term { background: #1b2029; border-radius: 7px; margin: 14px 0 20px;
        padding: 11px 15px 13px; page-break-inside: avoid; }
.term .h { font-size: 8pt; color: #7f93ad; letter-spacing: .09em;
           margin: 0 0 7px; font-weight: 700; }
.term pre { margin: 0; padding: 0; background: none; border: 0; }
.term code { background: none; padding: 0; color: #eaf0f7; font-size: 10pt;
             white-space: pre; letter-spacing: 0; }
.term .g { color: #63d68f; }                      /* > 프롬프트 */

/* ── 파일에 쓰는 코드 — 밝은 카드 + 위에 라벨 ────────────────────────────── */
.codecard { border: 1px solid #d5dbe3; border-radius: 7px; margin: 14px 0 20px;
            overflow: hidden; page-break-inside: avoid; }
.codecard .h { background: #eef2f7; border-bottom: 1px solid #d5dbe3;
               font-size: 8pt; color: #46587a; letter-spacing: .09em;
               font-weight: 700; padding: 6px 14px; }
.codecard pre { margin: 0; border: 0; border-radius: 0; background: #fbfcfe;
                padding: 12px 15px; }
.codecard code { background: none; padding: 0; color: #1f2429; font-size: 9.5pt;
                 white-space: pre; }

/* 위 둘에 안 걸린 나머지 */
pre { background: #f7f8fa; border: 1px solid #dde1e6; border-radius: 5px;
      padding: 11px 14px; margin: 14px 0; page-break-inside: avoid; }
pre code { font-family: var(--mono); background: none; padding: 0; color: #1f2429; }

table { border-collapse: collapse; width: 100%; margin: 16px 0 20px;
        font-size: 9.5pt; page-break-inside: avoid; }
th { background: #eef2f7; border: 1px solid #c9d2dc; padding: 8px 10px;
     text-align: left; font-weight: 700; color: #24405f; }
td { border: 1px solid #d8dee6; padding: 8px 10px; vertical-align: top; }

blockquote { border-left: 4px solid #f0a500; background: #fffaf0; margin: 16px 0;
             padding: 11px 16px; page-break-inside: avoid; }
blockquote p { margin: 5px 0; }

/* 세로로 긴 캡처가 쪽에 안 들어가면 통째로 다음 쪽에 밀려 큰 공백이 남는다 —
   높이를 눌러 밀림 자체를 줄인다. 사진+설명은 figure 한 덩어리라
   쪽 경계에서 서로 갈라지지 않는다. */
figure { margin: 14px 0 18px; page-break-inside: avoid; break-inside: avoid; }
img { max-width: 100%; max-height: 90mm; border: 1px solid #c9d2dc;
      border-radius: 6px; margin: 0 0 4px; display: block; }
.cap { font-size: 9pt; color: #5a6672; margin: 0; }

/* 작은 단계 ①②③ — 상자를 없앤다. 숨 막히던 원인이 이것이다.
   왼쪽에 짧은 막대 하나만 두고 글씨로 승부한다. */
.step { margin: 24px 0 10px; padding: 0 0 0 13px; font-size: 11.5pt;
        font-weight: 700; color: #14335e; letter-spacing: -.01em;
        border-left: 4px solid #f0a500; page-break-after: avoid; }

/* 구역 이름 — 조용하게 */
.label { margin: 24px 0 8px; font-size: 9pt; font-weight: 700;
         color: #7a848f; letter-spacing: .09em; page-break-after: avoid; }
.label .x { color: #7a848f; font-weight: 400; }

/* 마무리 한 문장 */
.punch { margin: 18px 0; padding: 11px 15px; font-weight: 700; color: #1f4636;
         background: #f2f8f4; border-left: 4px solid #4f8f68; border-radius: 5px; }
.punch code { background: #e2efe7; color: #1f4636; }

.trouble { border: 1px solid #e6d2d2; border-left: 5px solid #c0392b;
           background: #fdf8f7; border-radius: 5px; padding: 10px 14px;
           margin: 10px 0; page-break-inside: avoid; }
.trouble .t { margin: 0 0 5px; font-weight: 700; color: #8a2020; font-size: 10pt; }
.trouble .t code { background: #f6e7e7; color: #8a2020; }
.trouble .b { margin: 0; font-size: 10pt; }

hr { border: 0; border-top: 1px solid #e4e8ed; margin: 30px 0; }
hr:has(+ h2) { display: none; }        /* 큰 단계가 제 윗줄을 갖는다 */
h1 + hr { display: none; }
/* 제목 바로 밑 큰 단계는 제 윗줄을 안 그린다 — h1 밑줄과 겹쳐 빈 띠로 보인다 */
h1 + h2, h1 + hr + h2 { border-top: 0; margin-top: 24px; padding-top: 0; }
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


# 명령·출력·파일코드·수식·지시문은 **하는 일이 다르다.**
# 전에는 전부 같은 회색 상자라 학생이 명령을 파일에 붙여넣는 일이 났다.
#
# ★ 여기 없는 낱말로 시작하면 「화면에 이렇게 나옵니다」로 뒤집힌다 —
#   치라고 준 명령에 「나옵니다」가 붙으면 학생은 그 상자가 입력인지 결과인지
#   모른다. 실제로 docker·wsl·powershell 이 빠져 다섯 곳이 그랬다.
#   명령을 새로 쓰면 그 첫 낱말이 여기 있는지 본다.
명령시작 = ("uv ", "cd ", "python ", "py ", "git ", "pip ", "code ", "npx ",
        "docker ", "wsl ", "powershell ")

# 말머리(``` 뒤에 적는 것) → (칸 종류, 위에 붙일 라벨)
칸종류 = {
    "python": ("codecard", "파일에 씁니다"),
    "py":     ("codecard", "파일에 씁니다"),
    "json":   ("codecard", "파일에 이렇게 있습니다"),
    "모양":    ("codecard", "이런 모양으로 돌려줍니다"),
    "지시문":  ("codecard", "AI 에게 주는 말 — 그대로 씁니다"),
    "주소":    ("term",     "크롬 주소창에 붙여넣습니다"),
    "수식":    ("plain",    ""),
}


def 코드칸(줄: list[str], 말: str) -> str:
    """말머리로 갈라 놓고, 안 적었으면 명령인지 화면 출력인지 스스로 가른다."""
    본문 = "\n".join(줄).rstrip()
    안전 = html.escape(본문)
    종류, 라벨 = 칸종류.get(말, (None, None))

    if 종류 == "plain":
        return f"<pre><code>{안전}</code></pre>"
    if 종류 == "codecard":
        return (f'<div class="codecard"><div class="h">{라벨}</div>'
                f'<pre><code>{안전}</code></pre></div>')
    if 종류 == "term":
        return (f'<div class="term"><div class="h">{라벨}</div>'
                f'<pre><code>{안전}</code></pre></div>')

    쓸것 = [x for x in 줄 if x.strip()]
    if 쓸것 and all(x.lstrip().startswith(명령시작) for x in 쓸것):
        몸 = "\n".join(html.escape(x.strip()) for x in 쓸것)
        return ('<div class="term"><div class="h">터미널에 칩니다</div>'
                f'<pre><code>{몸}</code></pre></div>')

    return ('<div class="term"><div class="h">화면에 이렇게 나옵니다</div>'
            f'<pre><code>{안전}</code></pre></div>')


def md2html(
md: str, 제목: str, 기준폴더: Path | None = None) -> str:
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
            # 사진과 설명 글귀는 한 덩어리 — 쪽 경계에서 따로 갈라지면 안 된다.
            꼬리 = f'<div class="cap">{html.escape(설명)}</div>' if 설명 else ""
            out.append(f'<figure><img src="{경로.as_uri()}" '
                       f'alt="{html.escape(설명)}">{꼬리}</figure>')
            i += 1
            continue

        if line.startswith("```"):                                  # 코드블록
            말 = line[3:].strip().lower()
            i += 1
            buf = []
            while i < len(줄들) and not 줄들[i].startswith("```"):
                buf.append(줄들[i])
                i += 1
            i += 1
            out.append(코드칸(buf, 말))
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
            # 원본에서 보기 좋게 줄바꿈한 자리가 문단 나눔이 되면 안 된다 —
            # 빈 `>` 줄에서만 문단을 가르고, 이어지는 줄은 한 문단으로 붙인다.
            문단들: list[str] = []
            모음: list[str] = []
            for x in buf:
                if x and not x.startswith(("-", "→")):
                    모음.append(x)
                    continue
                if 모음:
                    문단들.append(" ".join(모음))
                    모음 = []
                if x:
                    문단들.append(x)
            if 모음:
                문단들.append(" ".join(모음))
            out.append("<blockquote>"
                       + "".join(f"<p>{인라인(x)}</p>" for x in 문단들)
                       + "</blockquote>")
            continue
        elif re.match(r"^\s*[-*]\s+", line):
            # 들여쓴 이어짐 줄은 그 항목의 뒷문장이다 — 따로 내보내면
            # 항목 밖으로 떨어져 나가 문장이 끊긴다.
            buf: list[str] = []
            while i < len(줄들):
                if re.match(r"^\s*[-*]\s+", 줄들[i]):
                    buf.append(re.sub(r"^\s*[-*]\s+", "", 줄들[i]))
                elif (buf and 줄들[i].startswith((" ", "\t")) and 줄들[i].strip()
                      and not 줄들[i].lstrip().startswith(("![", "```", "|", ">"))):
                    buf[-1] += " " + 줄들[i].strip()
                else:
                    break
                i += 1
            out.append("<ul>" + "".join(f"<li>{인라인(x)}</li>" for x in buf) + "</ul>")
            continue
        elif re.match(r"^\s*\d+\.\s+", line):
            # 항목 사이에 사진이 끼면 목록이 여기서 끊겼다 다시 시작한다 —
            # 원문의 숫자를 살려야 「2. 3. 4.」가 전부 「1.」로 리셋되지 않는다.
            첫숫자 = int(re.match(r"^\s*(\d+)\.", line).group(1))
            buf = []
            while i < len(줄들):
                if re.match(r"^\s*\d+\.\s+", 줄들[i]):
                    buf.append(re.sub(r"^\s*\d+\.\s+", "", 줄들[i]))
                elif (buf and 줄들[i].startswith((" ", "\t")) and 줄들[i].strip()
                      and not 줄들[i].lstrip().startswith(("![", "```", "|", ">"))):
                    buf[-1] += " " + 줄들[i].strip()
                else:
                    break
                i += 1
            시작 = f' start="{첫숫자}"' if 첫숫자 != 1 else ""
            out.append(f"<ol{시작}>" + "".join(f"<li>{인라인(x)}</li>" for x in buf) + "</ol>")
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
            # `**1. …**` 로 시작하는 문단은 큰 단계의 소단계다 — 위를 띄워
            # 어디서 새 단계가 시작되는지 지면에서 보이게 한다.
            칸이름 = "nstep" if re.match(r"\*\*\d+\.", 묶음[0]) else ""
            붙임 = f' class="{칸이름}"' if 칸이름 else ""
            out.append(f"<p{붙임}>{인라인(' '.join(묶음))}</p>")
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
