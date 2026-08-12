# -*- coding: utf-8 -*-
"""덱과 같은 데이터에서 [첨부]원고.md · [설명란].md 를 뽑는다.
   덱을 고치면 두 문서가 자동으로 따라 바뀐다 — 어긋날 수 없다.
사용:  python emit_docs.py 1 | 2 | both   (기본 both)
"""
import html
import sys, re, pathlib, importlib
import deckkit as D
import svgs, svgs3
from artdesc import DESC

HERE = pathlib.Path(__file__).parent
MARKS = {
    "그런데 80도를<br>넘은 적이 없습니다": "★ 반전",
    "규칙으로는 여기까지입니다": "★ 넘기는 질문",
    "규칙은 미리 정한 것만 봅니다": "★ 2일차 회수",
    "되돌릴 수 있는가 — 이것이 갈림선입니다": "★ 아하",
    "그런데 이건 전부 소프트웨어입니다": "★ 넘기는 질문",
}
LAYOUT = {1: "표지형", 2: "구간 표지형", 3: "큰 그림 + 짧은 글", 4: "번호 레일형",
          5: "나란히 비교형", 6: "표형", 7: "낱말 나열형", 8: "가는 선 그래프형"}

# SVG 문자열 → 변수명
SVGMAP = {}
for mod in (svgs, svgs3):
    for k, v in vars(mod).items():
        if isinstance(v, str) and v.startswith("<svg") and k not in SVGMAP.values():
            SVGMAP[v] = k


def artname(svg):
    if not svg:
        return None
    if svg in SVGMAP:
        return SVGMAP[svg]
    # .replace() 로 크기만 바꾼 경우 — 앞부분으로 되찾는다
    for s, k in SVGMAP.items():
        if s[:40].split(">", 1)[-1][:60] and s.split(">", 1)[-1][:60] == svg.split(">", 1)[-1][:60]:
            return k
    return None


def art_line(svg):
    k = artname(svg)
    if k and k in DESC:
        return DESC[k]
    return "(삽화 설명 없음 — artdesc.py 에 등록할 것)"


def strip(s):
    """설명란·원고에 넣을 순수 텍스트 — 마크업 제거, 강조는 남긴다"""
    s = s.replace("<br>", " ")
    s = re.sub(r'<span class="mark">(.*?)</span>', r"\1", s)
    s = re.sub(r"<b>(.*?)</b>", r"**\1**", s)
    s = re.sub(r"<[^>]+>", "", s)
    # &gt; &nbsp; 같은 엔티티가 문서에 그대로 노출됐던 적이 있다 — 사람 글자로 되돌린다.
    s = html.unescape(s).replace("\xa0", " ")
    return s.strip()


def emit(tag, title, scope_note, forbid_common):
    D.LOG.clear()
    importlib.import_module(tag)
    log = list(D.LOG)
    n = len(log)

    # ── [첨부]원고.md
    o = [f"# {tag[-3:]} — 강의 원고 ({n}장)", "",
         f"> **이 문서는 {n}장 범위만 담는다.**",
         *("> " + ln for ln in scope_note.splitlines()), "",
         "## 지켜야 할 사실 (지어내지 말 것)", "",
         "- 무대는 경남 창원의 **가상** 정밀기계 부품 제조사 「K-정밀」. CNC 설비 6대(EQ-01~EQ-06), AMR 2대.",
         "- 값은 **1초마다** 갱신. CNC는 온도·진동·rpm·가동상태, AMR은 위치·배터리·적재상태.",
         "- 새벽 3시 EQ-03 사건 — 시간당 **0.5℃**, **62 → 64℃**, 고정 임계값 **80℃를 끝까지 넘지 않음**.",
         "- 연습용 CSV 의 새벽 실측 — 3시 **61.0℃** → 4시 **61.6℃** (일주기 최저점이라 사건 서사보다 낮게 찍힌다. 6·8장이 이 값을 쓴다 — 둘 다 맞다).",
         "- 연습용 데이터는 CNC 6대 × 7일 × 1분 = **60,480행**. 이상 3종(드리프트·스파이크·결측)이 심어져 있다.",
         "- 오탐 실측 — 기본값에서 하루 **81건**, k를 2.0으로 낮추면 하루 **911건(11배)**.",
         "- 제어 도구 4개 — `set_equipment_speed` `ack_alarm` `stop_equipment` `dispatch_robot`.",
         "  감속·알람확인은 **자동**, 정지·파견은 **사람 승인**.",
         "- 위에 없는 숫자·회사명·제품명을 쓰지 마라.", ""]

    for i, s in enumerate(log, 1):
        star = " " + MARKS[s["h1"]] if s.get("h1") in MARKS else ""
        o.append(f"## {i}장 · {strip(s['h1'])}{star}")
        o.append("")
        if s["t"] == "cover":
            o += [f"- 윗줄 `{s['eyebrow']}`", f"- 제목 `{strip(s['h1'])}`",
                  f"- 부제 `{s['sub']}`", f"- 하단 `{s['tail'][0]}`",
                  f"- 하단 굵게 `{s['tail'][1]}`", ""]
            continue
        o.append(f"부제 — {strip(s['sub'])}")
        o.append("")
        if s["t"] == "sect":
            o += [f"이 장의 낱말 — **{strip(s['word'])}** ({strip(s['wsub'])})", ""]
        if s["t"] in ("sect", "pic", "graph"):
            o.append("본문")
            o += [f"- {strip(x)}" for x in s["ps"]]
            o.append("")
        if s["t"] == "rail":
            o.append("세 항목" if len(s["rows"]) == 3 else f"{len(s['rows'])} 항목")
            o += [f"- **{strip(st)}** — {strip(sp)}" for _, _, st, sp in s["rows"]]
            o.append("")
        if s["t"] == "cmp":
            for side in (s["left"], s["right"]):
                o.append(f"- `{strip(side[0])}` **{strip(side[3])}** — {strip(side[4])}")
            o.append("")
        if s["t"] == "tbl":
            o.append("표 — " + " / ".join(f"`{h}`" for h in s["head"] if h))
            o += ["- " + " · ".join(strip(c) for c in r) for r in s["rows"]]
            o.append("")
        if s["t"] == "words":
            o += [f"- **{strip(w)}** — {strip(d)}" for _, w, d, _ in s["cols"]]
            o.append("")
        if s["foot"]:
            o += [f"하단 — {strip(s['foot'])}", ""]

    (HERE / f"{tag[-3:]}_[첨부]원고.md").write_text("\n".join(o), encoding="utf-8")

    # ── [설명란].md
    e = [f"# {tag[-3:]} — 설명란 ({n}장)", "",
         "> **업로드할 파일 2개**",
         "> ① `제작/기준판/디자인기준판.pdf`",
         f"> ② `{tag[-3:]}_[첨부]원고.md` ← **이 덱 범위만 담긴 원고. 다른 덱 원고를 같이 올리지 마라.**",
         ">",
         "> ※ **NotebookLM이 받는 형식** — PDF · txt · **Markdown(.md)**. HTML·PNG는 안 된다.",
         "> **맞춤설정** — 언어 한국어 / 길이 기본값",
         "> **설명 칸** — 아래 ▼부터 ▲까지 전부 복사해 붙여넣기",
         f"> **생성 결과** — {n}장 → PPT로 내려받아 확정. 머리글·페이지 번호는 슬라이드 마스터에서 일괄 처리한다.",
         "", "---", "", "▼ 복붙 시작 ▼", "",
         f"**정확히 {n}장**의 슬라이드를 만들어라. 아래 1~{n}페이지 지정을 "
         "**한 지정 = 한 장**으로 따르고 합치거나 나누지 마라.", "",
         "## 이 자료에는 발표 대본이 없다", "",
         "강사가 읽을 대본이 따로 없다. **슬라이드만 보고도 뜻이 통해야 한다.**", "",
         "- **글로 다 쓰지 마라.** 화면을 글자로 채우면 읽느라 강의를 못 듣는다.",
         "- **그렇다고 비우지도 마라.** 낱말만 덩그러니 있으면 대본 없이는 아무 뜻도 안 통한다.",
         "- **답은 삽화다.** 그림이 뜻을 지고, 글은 그림이 못 하는 말만 한다.",
         "- **그림만으로 뜻이 안 통하면 그때 라벨을 박아라.** 보면 아는 물건에는 붙이지 않는다.",
         "", "## 범위 — 이걸 어기면 실패다", "", scope_note, "",
         f"- **{n}장을 넘겨 만들지 마라.** {n}페이지가 마지막이다.",
         "- 업로드한 원고에 없는 것을 **만들어 넣지 마라.**", "",
         "## 전 장 공통 금지", ""] + forbid_common + [""]

    for i, s in enumerate(log, 1):
        star = " " + MARKS[s["h1"]] if s.get("h1") in MARKS else ""
        e += [f"# {i}페이지{star}", "",
              f"**레이아웃** {s['n']}번 ({LAYOUT[s['n']]})", "", "**화면 글자**"]
        if s["t"] == "cover":
            e += [f"- 윗줄: `{s['eyebrow']}`", f"- 제목: `{strip(s['h1'])}`",
                  f"- 부제: `{s['sub']}`",
                  f"- 하단 두 줄: `{s['tail'][0]}` / `{s['tail'][1]}`（두 번째 줄 굵게）", "",
                  "**삽화** 오른쪽에 흰 동심원 다섯 겹, 투명도 30%. 다른 그림 금지.", "",
                  "**금지**", "- 배경은 짙은 남색 #12305A 하나. 사진·로고 금지.", "", "---", ""]
            continue
        e.append(f"- 제목: `{strip(s['h1'])}`")
        e.append(f"- 설명문: `{strip(s['sub'])}`")
        if s["t"] == "sect":
            e += [f"- 큰 낱말: `{strip(s['word'])}`", f"- 낱말 아래 한 줄: `{strip(s['wsub'])}`"]
        if s["t"] in ("sect", "pic", "graph"):
            e.append(f"- 본문 {len(s['ps'])}행:")
            e += [f"  - `{strip(x)}`" for x in s["ps"]]
        if s["t"] == "rail":
            e.append(f"- 행 {len(s['rows'])}개 (번호 / 굵은 제목 / 설명 한 줄):")
            e += [f"  - `{no}` · `{strip(st)}` · `{strip(sp)}`" for _, no, st, sp in s["rows"]]
        if s["t"] == "cmp":
            for lbl, side in (("왼쪽", s["left"]), ("오른쪽", s["right"])):
                e.append(f"- {lbl}: 분류 `{strip(side[0])}` / 이름 `{strip(side[3])}` / "
                         f"설명 `{strip(side[4])}`")
        if s["t"] == "tbl":
            e.append("- 표 머리행: " + " / ".join(f"`{h or '(빈칸)'}`" for h in s["head"]))
            for j, r in enumerate(s["rows"]):
                mark = "  ← 이 행만 아주 연한 남색 #EEF3F9" if s.get("on") == j else ""
                e.append("  - " + " / ".join(f"`{strip(c)}`" for c in r) + mark)
        if s["t"] == "words":
            e.append("- 세 칸 (낱말 / 설명):")
            e += [f"  - `{strip(w)}` · `{strip(d)}`" + ("  ← 낱말을 주황으로" if hot else "")
                  for _, w, d, hot in s["cols"]]
        if s["foot"]:
            e.append(f"- 하단 강조(아주 연한 주황 밑칠): `{strip(s['foot'])}`")
        e.append("")
        if s["t"] in ("sect", "pic", "graph"):
            e += [f"**삽화** {art_line(s['art'])}", ""]
        elif s["t"] == "cmp":
            e += [f"**삽화** 왼쪽 — {art_line(s['left'][2])}", "",
                  f"오른쪽 — {art_line(s['right'][2])}", "",
                  "**두 쪽 배경을 다르게 칠하지 마라.** 가운데 가는 세로선 하나로만 나눈다.", ""]
        elif s["t"] == "rail":
            e += ["**삽화** 각 행 왼쪽에 작은 아이콘 하나씩(76×76, 선만, 남색). "
                  "아이콘은 " + " / ".join(art_line(ico).split(" —")[0].split(".")[0]
                                          for ico, _, _, _ in s["rows"]) + ".", ""]
        elif s["t"] == "words":
            e += ["**삽화** 낱말 **위에** 각각 큰 그림 하나씩. 낱말 위 굵은 가로줄을 그리지 마라.", ""]
        elif s["t"] == "tbl":
            e += ["**삽화** 없음. 표만. 세로줄을 긋지 마라. 머리행만 남색.", ""]
        e += ["**금지**", "- 같은 문장을 두 번 쓰지 마라.",
              "- 배경을 갈라 칠하지 마라. 순백 하나다.", "", "---", ""]

    e += ["▲ 복붙 끝 ▲", ""]
    (HERE / f"{tag[-3:]}_[설명란].md").write_text("\n".join(e), encoding="utf-8")
    print(f"{tag[-3:]}: 원고·설명란 {n}장")


COMMON_FORBID = [
    "- **어떤 이상이 잡히고 어떤 것이 안 잡히는지 한 글자도 쓰지 마라.** "
    "스파이크·드리프트·결측 각각의 결과는 **학생이 코드를 돌려서 발견할 반전이다.**",
    "- 오탐 수치(하루 81건 → 911건, 11배)는 이론으로 다루는 것이라 나와도 된다.",
    "- 화면을 좌우로 갈라 칠하지 마라. 배경은 **순백 하나**, 표지형만 짙은 남색이다.",
    "- **숫자를 화면 절반만 하게 키우지 마라.** 큰 낱말도 제목보다 조금만 크다.",
    "- 격자·청사진 무늬·뜻 없는 숫자 더미를 그림 안에 깔지 마라.",
    "- 사진·제품 로고·회사 이름 금지.",
]

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("1", "both"):
        emit("build_2일차", "2일차",
             "- 이 덱은 **「그럼 누가 판단하나」라는 질문에서 끝난다.**\n"
             "- **그 질문에 답하지 마라.** 에이전트·MCP·제어·승인 관문은 전부 3일차 몫이다. 한 글자도 꺼내지 마라.",
             COMMON_FORBID)
    if which in ("2", "both"):
        emit("build_3일차", "3일차",
             "- 이 덱은 **「그런데 이건 전부 소프트웨어입니다」에서 끝난다.**\n"
             "- **PLC·래더 로직·현장 사고 사례는 마지막 날 몫이다. 한 글자도 꺼내지 마라.**",
             COMMON_FORBID)
