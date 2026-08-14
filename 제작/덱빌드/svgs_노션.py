# -*- coding: utf-8 -*-
"""노션 1교시 전용 삽화 — 기준판 v2

원칙 — **그림이 내용을 설명해야 한다.** 남의 그림을 빌려 글자만 갈아 끼우지 않는다.
화면 목업은 `screen(하이라이트)` 하나로 만들고, 그 단계에서 만지는 자리만 붉게 띄운다.
"""

F = 'font-family="Malgun Gothic, sans-serif"'

# 기준판 색
INK, SUB, LINE, BG = "#1b2430", "#5b6675", "#d8dee7", "#ffffff"
HOT, HOT_BG = "#e2483c", "#fdecea"
BLUE, BLUE_BG = "#2f6fdb", "#eaf1fd"
PAPER = "#faf7f0"


def _s(w, h, vb, inner):
    return (f'<svg width="{w}" height="{h}" viewBox="{vb}" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg">{inner}</svg>')


# ─────────────────────────────────────────────────────────────────────
# 1. 강의를 듣고 나면 — 머릿속이 흩어져 있다
# ─────────────────────────────────────────────────────────────────────
def _조각(x, y, w, h, r, op):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" '
            f'transform="rotate({r} {x + w / 2} {y + h / 2})" '
            f'fill="{SUB}" opacity="{op}"/>')


# ─────────────────────────────────────────────────────────────────────
# AI 에게 던져 받은 정리본이 쌓이는 장면 — 예쁘지만 다시 읽어야 한다
# ─────────────────────────────────────────────────────────────────────
def _문서(x, y, 진하기=1.0):
    return f"""
  <rect x="{x}" y="{y}" width="86" height="112" rx="6" fill="{BG}"
        stroke="{LINE}" stroke-width="1.6" opacity="{진하기}"/>
  <rect x="{x + 12}" y="{y + 16}" width="62" height="7" rx="3" fill="{SUB}" opacity=".45"/>
  <rect x="{x + 12}" y="{y + 32}" width="48" height="6" rx="3" fill="{LINE}"/>
  <rect x="{x + 12}" y="{y + 46}" width="62" height="6" rx="3" fill="{LINE}"/>
  <rect x="{x + 12}" y="{y + 60}" width="40" height="6" rx="3" fill="{LINE}"/>
  <rect x="{x + 12}" y="{y + 74}" width="58" height="6" rx="3" fill="{LINE}"/>
  <rect x="{x + 12}" y="{y + 88}" width="34" height="6" rx="3" fill="{LINE}"/>"""


PRETTY = _s(560, 400, "0 0 560 400", f"""
  <text x="0" y="18" fill="{SUB}" font-size="17" {F}>내 필기 · 강의자료를 던지면</text>
  <rect x="0" y="34" width="150" height="46" rx="10" fill="{BLUE_BG}" stroke="{BLUE}" stroke-width="1.6"/>
  <text x="75" y="63" text-anchor="middle" fill="{BLUE}" font-size="18" font-weight="700" {F}>AI 가 정리</text>
  <path d="M160 57 L206 57" stroke="{SUB}" stroke-width="2"/>
  <path d="M198 51 L206 57 L198 63" stroke="{SUB}" stroke-width="2" fill="none"/>
  <text x="216" y="63" fill="{INK}" font-size="18" font-weight="700" {F}>예쁜 정리본이 쌓인다</text>

  {_문서(0, 110)}
  {_문서(100, 110, .85)}
  {_문서(200, 110, .7)}
  {_문서(300, 110, .55)}
  {_문서(400, 110, .4)}
  <text x="470" y="176" fill="{SUB}" font-size="26" font-weight="700" {F}>…</text>

  <path d="M0 262 L560 262" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="5 5"/>
  <text x="0" y="296" fill="{HOT}" font-size="18" font-weight="700" {F}>그런데 —</text>
  <text x="0" y="326" fill="{INK}" font-size="18" {F}>이걸 다시 <tspan font-weight="700">읽고 이해</tspan>해야 하고,</text>
  <text x="0" y="356" fill="{INK}" font-size="18" {F}>시험 때 가서 <tspan font-weight="700" fill="{HOT}">또 외웁니다.</tspan></text>
  <text x="0" y="388" fill="{SUB}" font-size="16" {F}>일이 줄지 않았습니다.</text>
""")


# ─────────────────────────────────────────────────────────────────────
# 말로 뱉어 보기 — 막히는 자리가 곧 모르는 자리
# ─────────────────────────────────────────────────────────────────────
SPEAK = _s(560, 400, "0 0 560 400", f"""
  <rect x="0" y="0" width="560" height="250" rx="12" fill="{BG}"
        stroke="{LINE}" stroke-width="1.8"/>
  <rect x="0" y="0" width="560" height="34" rx="12" fill="#f6f8fb"/>
  <rect x="0" y="24" width="560" height="10" fill="#f6f8fb"/>
  <text x="16" y="23" fill="{SUB}" font-size="14" {F}>빈 메모장 — 말하면 글자로 적힙니다</text>

  <text x="20" y="66" fill="{INK}" font-size="17" {F}>"함수는 값을 넣으면 답을 돌려주는 상자예요."</text>
  <text x="20" y="98" fill="{INK}" font-size="17" {F}>"같은 걸 여러 번 쓸 때 만들어 두면 편하고요."</text>
  <text x="20" y="130" fill="{INK}" font-size="17" {F}>"그러니까 매개변수는… 어… 그게…"</text>

  <rect x="14" y="112" width="330" height="30" rx="6" fill="{HOT_BG}" stroke="{HOT}" stroke-width="1.8"/>
  <text x="356" y="133" fill="{HOT}" font-size="16" font-weight="700" {F}>← 여기서 막혔다</text>

  <text x="20" y="176" fill="{SUB}" font-size="16" {F}>…</text>

  <text x="0" y="292" fill="{BLUE}" font-size="17" font-weight="700" {F}>설명한 부분</text>
  <text x="110" y="292" fill="{INK}" font-size="17" {F}>— 이미 아는 것. 넘어간다</text>
  <text x="0" y="326" fill="{HOT}" font-size="17" font-weight="700" {F}>막힌 부분</text>
  <text x="110" y="326" fill="{INK}" font-size="17" {F}>— 내가 모르는 것. <tspan font-weight="700">여기만 판다</tspan></text>
""")


SCATTER = _s(520, 400, "0 0 520 400", f"""
  <circle cx="260" cy="200" r="150" fill="{PAPER}"/>
  {_조각(120, 90, 120, 12, -14, .55)}
  {_조각(300, 110, 90, 12, 9, .45)}
  {_조각(160, 150, 150, 12, 5, .5)}
  {_조각(320, 178, 70, 12, -7, .38)}
  {_조각(130, 214, 100, 12, 11, .42)}
  {_조각(260, 246, 130, 12, -5, .5)}
  {_조각(170, 286, 80, 12, 7, .35)}
  <text x="260" y="360" text-anchor="middle" fill="{SUB}" font-size="19" {F}>
    수업이 끝난 뒤 머릿속
  </text>
""")


# ─────────────────────────────────────────────────────────────────────
# 2. 자산화가 하는 일 — 흩어진 것이 한 곳에 쌓이고, 다시 꺼내진다
# ─────────────────────────────────────────────────────────────────────
FUNNEL = _s(540, 400, "0 0 540 400", f"""
  <!-- 위: 흩어진 조각 -->
  {_조각(90, 34, 110, 11, -12, .5)}
  {_조각(250, 26, 80, 11, 8, .42)}
  {_조각(350, 46, 100, 11, -6, .45)}
  {_조각(150, 66, 130, 11, 4, .4)}
  <!-- 깔때기 -->
  <path d="M110 110 L430 110 L305 210 L305 268 L235 268 L235 210 Z"
        fill="{BLUE_BG}" stroke="{BLUE}" stroke-width="2"/>
  <text x="270" y="168" text-anchor="middle" fill="{BLUE}" font-size="17"
        font-weight="700" {F}>내 말로 다시 쓴다</text>
  <!-- 아래: 카드 세 장 -->
  <rect x="120" y="300" width="90" height="66" rx="8" fill="{BG}"
        stroke="{LINE}" stroke-width="2"/>
  <rect x="225" y="300" width="90" height="66" rx="8" fill="{BG}"
        stroke="{LINE}" stroke-width="2"/>
  <rect x="330" y="300" width="90" height="66" rx="8" fill="{BG}"
        stroke="{BLUE}" stroke-width="2"/>
  <rect x="134" y="316" width="52" height="7" rx="3" fill="{SUB}" opacity=".5"/>
  <rect x="134" y="332" width="62" height="7" rx="3" fill="{LINE}"/>
  <rect x="239" y="316" width="52" height="7" rx="3" fill="{SUB}" opacity=".5"/>
  <rect x="239" y="332" width="62" height="7" rx="3" fill="{LINE}"/>
  <rect x="344" y="316" width="52" height="7" rx="3" fill="{BLUE}" opacity=".6"/>
  <rect x="344" y="332" width="62" height="7" rx="3" fill="{LINE}"/>
  <text x="270" y="392" text-anchor="middle" fill="{SUB}" font-size="17" {F}>
    한 줄이 하루 · 쌓이면 학기 하나
  </text>
""")


# ─────────────────────────────────────────────────────────────────────
# 3. 노션 화면 목업 — 만지는 자리만 붉게 띄운다
#    하이라이트: sidebar · title · block · table · prop · card
#               template · body · view · share · none
# ─────────────────────────────────────────────────────────────────────
def screen(hot="none", 설명=""):
    def 틀(x, y, w, h, key, r=8):
        칠 = HOT_BG if hot == key else BG
        선 = HOT if hot == key else LINE
        굵기 = 2.5 if hot == key else 1.5
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
                f'fill="{칠}" stroke="{선}" stroke-width="{굵기}"/>')

    def 글(x, y, t, size=13, col=SUB, w=400, anchor="start"):
        return (f'<text x="{x}" y="{y}" fill="{col}" font-size="{size}" '
                f'font-weight="{w}" text-anchor="{anchor}" {F}>{t}</text>')

    캡션 = 글(300, 392, 설명, 16, HOT, 700, "middle") if 설명 else ""
    return _s(600, 400, "0 0 600 400", f"""
      <rect x="0" y="0" width="600" height="360" rx="10" fill="{BG}"
            stroke="{LINE}" stroke-width="1.5"/>
      <!-- 사이드바 -->
      {틀(0, 0, 150, 360, "sidebar", 10)}
      {글(20, 34, "김민준의 노션", 12, SUB, 700)}
      {글(20, 66, "🔍  검색")}
      {글(20, 92, "🏠  홈")}
      {글(20, 126, "개인 페이지", 11, LINE, 700)}
      {글(20, 152, "📚  내 학습 노트", 12, INK if hot in ("sidebar", "none") else SUB, 700)}
      {글(30, 176, "📄  8/11 이상 감지", 11)}
      {글(30, 198, "📄  8/12 …", 11)}
      <!-- 본문 제목 -->
      {틀(168, 20, 412, 52, "title")}
      {글(184, 44, "📚", 18, INK)}
      {글(212, 52, "내 학습 노트", 22, INK, 700)}
      <!-- 안내 블록 -->
      {틀(168, 84, 412, 44, "block")}
      {글(184, 104, "수업을 듣고 온 날, 카드를 하나 만듭니다.", 12)}
      {글(184, 120, "카드 안에는 개념을 제목으로 나눠 씁니다.", 12)}
      <!-- 뷰 탭 -->
      {틀(168, 140, 412, 32, "view")}
      {글(184, 161, "▦ 표", 12, INK, 700)}
      {글(226, 161, "🖼 갤러리", 12)}
      {글(292, 161, "▥ 분야별", 12)}
      {글(354, 161, "🔁 남은 것", 12)}
      <!-- 표 -->
      {틀(168, 182, 412, 128, "table")}
      {글(184, 204, "이름", 11, LINE, 700)}
      {글(330, 204, "분야", 11, LINE, 700)}
      {글(430, 204, "이해도", 11, LINE, 700)}
      <line x1="176" y1="212" x2="572" y2="212" stroke="{LINE}"/>
      {글(184, 234, "📊 8/11 이상 감지", 12, INK)}
      {글(184, 262, "🤖 8/12 에이전트 기초", 12, INK)}
      {글(184, 290, "🔧 8/13 파이프라인", 12, INK)}
      <!-- 속성 칸 -->
      {틀(320, 216, 250, 88, "prop")}
      {글(330, 234, "AI 실습", 11, BLUE)}
      {글(430, 234, "설명가능", 11, BLUE)}
      {글(330, 262, "AI 실습", 11, BLUE)}
      {글(430, 262, "대충앎", 11, HOT)}
      {글(330, 290, "데이터", 11, BLUE)}
      {글(430, 290, "설명못함", 11, HOT)}
      <!-- 새로 만들기 -->
      {틀(168, 318, 130, 28, "card")}
      {글(184, 337, "＋ 새로 만들기 ▾", 12, BLUE, 700)}
      <!-- 템플릿 -->
      {틀(306, 318, 120, 28, "template")}
      {글(320, 337, "＋ 새 템플릿", 12, BLUE if hot == "template" else SUB, 700)}
      <!-- 공유 -->
      {틀(470, 318, 110, 28, "share")}
      {글(484, 337, "공유 → 게시", 12, BLUE if hot == "share" else SUB, 700)}
      {캡션}
    """)


# 자주 쓰는 것 미리 굳혀 둔다
SC_SIDEBAR = screen("sidebar", "왼쪽에 새 페이지를 만든다")
SC_TITLE = screen("title", "제목 · 아이콘 · 커버를 넣는다")
SC_BLOCK = screen("block", "슬래시 / 로 블록을 넣는다")
SC_TABLE = screen("table", "표 하나에 전부 쌓는다")
SC_PROP = screen("prop", "칸은 분야 · 이해도 둘만")
SC_CARD = screen("card", "줄 하나가 하루")
SC_TPL = screen("template", "카드 양식을 한 번만 만든다")
SC_VIEW = screen("view", "데이터는 하나, 보는 창만 늘린다")
SC_SHARE = screen("share", "링크 하나가 나온다")
SC_DONE = screen("none", "완성하면 이 모습입니다")


# ─────────────────────────────────────────────────────────────────────
# 4. 카드 안 — 하루치가 한 화면에
# ─────────────────────────────────────────────────────────────────────
CARD = _s(560, 400, "0 0 560 400", f"""
  <rect x="0" y="0" width="560" height="400" rx="10" fill="{BG}"
        stroke="{LINE}" stroke-width="1.5"/>
  <text x="28" y="46" fill="{INK}" font-size="22" font-weight="700" {F}>
    📊 8/11 이상 감지</text>
  <text x="28" y="78" fill="{LINE}" font-size="12" {F}>◐ 분야</text>
  <text x="110" y="78" fill="{BLUE}" font-size="12" font-weight="700" {F}>AI 실습</text>
  <text x="210" y="78" fill="{LINE}" font-size="12" {F}>◐ 이해도</text>
  <text x="300" y="78" fill="{BLUE}" font-size="12" font-weight="700" {F}>설명가능</text>
  <line x1="28" y1="94" x2="532" y2="94" stroke="{LINE}"/>

  <text x="28" y="126" fill="{INK}" font-size="16" font-weight="700" {F}>
    z-score 가 재는 것</text>
  <text x="28" y="150" fill="{SUB}" font-size="13" {F}>
    평균에서 몇 칸 떨어졌는지를 재는 값.</text>
  <text x="28" y="170" fill="{SUB}" font-size="13" {F}>
    단위가 달라도 같은 잣대로 비교할 수 있다.</text>

  <rect x="28" y="188" width="504" height="76" rx="6" fill="#f6f8fb"
        stroke="{LINE}"/>
  <text x="44" y="212" fill="{SUB}" font-size="12"
        font-family="Consolas, monospace">mu = data.mean()</text>
  <text x="44" y="232" fill="{SUB}" font-size="12"
        font-family="Consolas, monospace">z = (x - mu) / sigma</text>
  <text x="44" y="252" fill="{HOT}" font-size="12"
        font-family="Consolas, monospace"># 이상치가 평균을 끌어당긴다</text>

  <text x="28" y="296" fill="{INK}" font-size="16" font-weight="700" {F}>
    다음에 확인할 것</text>
  <text x="28" y="322" fill="{SUB}" font-size="13" {F}>☐  창을 60분으로 둔 이유</text>
  <text x="28" y="346" fill="{SUB}" font-size="13" {F}>☑  표준편차가 0이면 어떻게 되나</text>
  <text x="28" y="378" fill="{BLUE}" font-size="13" font-weight="700" {F}>
    개념 하나 = 제목 하나. 그 아래 내 문장.</text>
""")


# ─────────────────────────────────────────────────────────────────────
# 5. 채우는 순서 — 내가 먼저, AI 는 그다음
# ─────────────────────────────────────────────────────────────────────
def _칩(x, y, w, t, col, bg, size=14):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="42" rx="21" fill="{bg}" '
            f'stroke="{col}" stroke-width="1.5"/>'
            f'<text x="{x + w / 2}" y="{y + 27}" text-anchor="middle" fill="{col}" '
            f'font-size="{size}" font-weight="700" {F}>{t}</text>')


ORDER_OK = _s(560, 200, "0 0 560 200", f"""
  <text x="0" y="20" fill="{BLUE}" font-size="14" font-weight="700" {F}>이 순서</text>
  {_칩(0, 36, 150, "내가 먼저 쓴다", BLUE, BLUE_BG)}
  <text x="162" y="63" fill="{SUB}" font-size="20" {F}>→</text>
  {_칩(184, 36, 150, "AI 가 고쳐 준다", BLUE, BLUE_BG)}
  <text x="346" y="63" fill="{SUB}" font-size="20" {F}>→</text>
  {_칩(368, 36, 190, "내 구멍이 드러난다", BLUE, BLUE_BG)}
  <text x="0" y="128" fill="{HOT}" font-size="14" font-weight="700" {F}>바꾸면</text>
  {_칩(0, 144, 150, "AI 에게 묻는다", HOT, HOT_BG)}
  <text x="162" y="171" fill="{SUB}" font-size="20" {F}>→</text>
  {_칩(184, 144, 150, "답을 읽는다", HOT, HOT_BG)}
  <text x="346" y="171" fill="{SUB}" font-size="20" {F}>→</text>
  {_칩(368, 144, 190, "읽고 끝난다", HOT, HOT_BG)}
""")


# ─────────────────────────────────────────────────────────────────────
# 6. 모르는 것 파고들기 — 내려갔다 올라온다
# ─────────────────────────────────────────────────────────────────────
def _말(x, y, w, t, col, bg):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="40" rx="10" fill="{bg}"/>'
            f'<text x="{x + 16}" y="{y + 26}" fill="{col}" font-size="14" '
            f'font-weight="700" {F}>{t}</text>')


DIG = _s(560, 400, "0 0 560 400", f"""
  {_말(0, 0, 330, "이게 무슨 소리지?", HOT, HOT_BG)}
  {_말(40, 56, 340, "그럼 이 말은 뭔데?", HOT, HOT_BG)}
  {_말(80, 112, 330, "이건 또 뭘 뜻하지?", HOT, HOT_BG)}
  <text x="120" y="186" fill="{SUB}" font-size="15" {F}>… 바닥</text>
  {_말(80, 204, 300, "아, 이거구나", BLUE, BLUE_BG)}
  {_말(40, 260, 340, "그래서 그렇게 되는구나", BLUE, BLUE_BG)}
  {_말(0, 316, 360, "카드에 내 문장으로 한 줄", BLUE, BLUE_BG)}
  <path d="M-14 20 L-14 330" stroke="{LINE}" stroke-width="2"
        stroke-dasharray="4 4"/>
  <text x="480" y="30" fill="{HOT}" font-size="13" font-weight="700" {F}>↓ 내려간다</text>
  <text x="480" y="340" fill="{BLUE}" font-size="13" font-weight="700" {F}>↑ 올라온다</text>
""")


# ─────────────────────────────────────────────────────────────────────
# 7. 정의는 외우지 않는다 — 의미가 같으면 정답 (코딩 용어로)
# ─────────────────────────────────────────────────────────────────────
# **한 번에 건너뛰지 않는다.** 어려운 정의에서 곧장 「상자」로 가면 마술처럼 보인다.
# 한 칸씩 쉬워지는 것을 보여 줘야 학생이 그 과정을 따라 할 수 있다.
def _내림(y, 꼬리표, 색, 배경, 줄들, 크기=14, 끝말=""):
    본문 = "".join(
        f'<text x="20" y="{y + 52 + i * 22}" fill="{INK}" font-size="{크기}" {F}>{t}</text>'
        for i, t in enumerate(줄들))
    높이 = 40 + len(줄들) * 22 + (26 if 끝말 else 0)   # 끝말이 테두리에 걸리지 않게
    꼬리 = (f'<text x="20" y="{y + 52 + len(줄들) * 22 + 4}" fill="{색}" '
            f'font-size="12" font-weight="700" {F}>{끝말}</text>' if 끝말 else "")
    return f"""
  <rect x="0" y="{y}" width="560" height="{높이}" rx="10" fill="{배경}"
        stroke="{색}" stroke-width="1.5"/>
  <text x="20" y="{y + 26}" fill="{색}" font-size="12" font-weight="700" {F}>{꼬리표}</text>
  {본문}{꼬리}"""


def _화살(y):
    return f"""
  <path d="M280 {y} L280 {y + 22}" stroke="{SUB}" stroke-width="2"/>
  <path d="M273 {y + 15} L280 {y + 22} L287 {y + 15}" stroke="{SUB}"
        stroke-width="2" fill="none"/>
  <text x="298" y="{y + 18}" fill="{SUB}" font-size="12" {F}>한 겹만 벗긴다</text>"""


# **뜻을 깎아서 쉬워지는 게 아니다.** 모르는 낱말을 만나면 그 낱말을 다시 파고들고,
# 바닥에 닿은 다음 이해한 것을 엮어 올라온다. 앞 장(모르는 자리는 끝까지 파고듭니다)과
# 같은 동작을 **정의를 대할 때도 똑같이** 한다는 것을 보여 준다.
def _단(x, y, w, 낱말, 뜻, 색=SUB, 배경=BG):
    return f"""
  <rect x="{x}" y="{y}" width="{w}" height="52" rx="8" fill="{배경}"
        stroke="{색}" stroke-width="1.5"/>
  <text x="{x + 14}" y="{y + 22}" fill="{색}" font-size="14" font-weight="700" {F}>{낱말}</text>
  <text x="{x + 14}" y="{y + 42}" fill="{INK}" font-size="13" {F}>{뜻}</text>"""


DEF_CMP = _s(560, 470, "0 0 560 470", f"""
  <text x="0" y="14" fill="{LINE}" font-size="12" font-weight="700" {F}>교과서 정의</text>
  <text x="0" y="38" fill="{INK}" font-size="13" {F}>“매개변수로 인자를 전달받아 정해진 연산을</text>
  <text x="0" y="58" fill="{INK}" font-size="13" {F}>수행하고 반환값을 산출하는 서브루틴”</text>

  <text x="440" y="86" fill="{HOT}" font-size="12" font-weight="700" {F}>↓ 내려간다</text>

  {_단(0, 74, 420, "매개변수?", "값을 받아 두는 자리 — 그런데 「인자」는 또 뭐지?", HOT, HOT_BG)}
  {_단(40, 140, 420, "인자?", "그 자리에 실제로 넣는 값. 3 을 넣으면 3 이 인자", HOT, HOT_BG)}
  {_단(80, 206, 420, "반환값?", "일을 마치고 밖으로 내주는 결과", HOT, HOT_BG)}
  <text x="120" y="284" fill="{SUB}" font-size="13" {F}>… 바닥</text>

  <text x="0" y="304" fill="{BLUE}" font-size="12" font-weight="700" {F}>↑ 엮으며 올라온다</text>

  {_단(40, 314, 480,
      "받아 두는 자리에 값을 넣으면",
      "정해진 계산을 하고 결과를 내준다", BLUE, BLUE_BG)}
  {_단(0, 380, 520,
      "“값을 넣으면 정해진 계산을 해서 답을 돌려주는 상자”",
      "— 매개변수 · 인자 · 연산 · 반환값이 다 들어 있다", BLUE, BLUE_BG)}

  <text x="0" y="462" fill="{BLUE}" font-size="14" font-weight="700" {F}>
    쉬워졌지만 뜻은 하나도 안 빠졌다</text>
""")


# ─────────────────────────────────────────────────────────────────────
# 8. 자가 점검 두 가지
# ─────────────────────────────────────────────────────────────────────
SELFTEST = _s(560, 380, "0 0 560 380", f"""
  <!-- 시험 1 — 빈 페이지에 써 보기 -->
  <rect x="0" y="20" width="560" height="150" rx="14" fill="{BG}"
        stroke="{LINE}" stroke-width="2"/>
  <circle cx="52" cy="95" r="24" fill="{BLUE_BG}" stroke="{BLUE}" stroke-width="2"/>
  <text x="52" y="103" text-anchor="middle" fill="{BLUE}" font-size="20"
        font-weight="700" {F}>1</text>
  <text x="96" y="80" fill="{INK}" font-size="20" font-weight="700" {F}>
    빈 페이지에 써 내려갈 수 있나</text>
  <text x="96" y="112" fill="{SUB}" font-size="14" {F}>
    카드도 강의자료도 덮고, 처음부터 내 문장으로</text>
  <rect x="96" y="128" width="300" height="8" rx="4" fill="{LINE}"/>
  <rect x="96" y="142" width="220" height="8" rx="4" fill="{LINE}"/>

  <!-- 시험 2 — 남에게 설명하기 -->
  <rect x="0" y="196" width="560" height="150" rx="14" fill="{BG}"
        stroke="{LINE}" stroke-width="2"/>
  <circle cx="52" cy="271" r="24" fill="{BLUE_BG}" stroke="{BLUE}" stroke-width="2"/>
  <text x="52" y="279" text-anchor="middle" fill="{BLUE}" font-size="20"
        font-weight="700" {F}>2</text>
  <text x="96" y="256" fill="{INK}" font-size="20" font-weight="700" {F}>
    남에게 설명할 수 있나</text>
  <text x="96" y="288" fill="{SUB}" font-size="14" {F}>
    말이 막히지 않고 끝까지</text>
  <rect x="96" y="304" width="180" height="26" rx="13" fill="{PAPER}"/>
  <text x="112" y="322" fill="{SUB}" font-size="13" {F}>“그러니까 이건…”</text>
  <rect x="292" y="304" width="150" height="26" rx="13" fill="{HOT_BG}"/>
  <text x="308" y="322" fill="{HOT}" font-size="13" font-weight="700" {F}>
    “어… 그게…”</text>
""")


# ─────────────────────────────────────────────────────────────────────
# 9. 노션에는 기능이 더 많다 — 필요할 때 찾아 쓰면 된다
# ─────────────────────────────────────────────────────────────────────
MORE = _s(560, 380, "0 0 560 380", f"""
  <circle cx="280" cy="150" r="128" fill="{PAPER}"/>
  <circle cx="280" cy="150" r="76" fill="{BLUE_BG}" stroke="{BLUE}"
          stroke-width="2"/>
  <text x="280" y="142" text-anchor="middle" fill="{BLUE}" font-size="17"
        font-weight="700" {F}>오늘 만든</text>
  <text x="280" y="166" text-anchor="middle" fill="{BLUE}" font-size="17"
        font-weight="700" {F}>기본기</text>

  <text x="120" y="56" fill="{SUB}" font-size="14" {F}>템플릿 갤러리</text>
  <text x="368" y="56" fill="{SUB}" font-size="14" {F}>AI 에이전트</text>
  <text x="76" y="150" fill="{SUB}" font-size="14" {F}>자동화</text>
  <text x="424" y="150" fill="{SUB}" font-size="14" {F}>수식 · 관계형</text>
  <text x="120" y="252" fill="{SUB}" font-size="14" {F}>캘린더 뷰</text>
  <text x="382" y="252" fill="{SUB}" font-size="14" {F}>웹 클리퍼</text>

  <text x="280" y="330" text-anchor="middle" fill="{INK}" font-size="17"
        font-weight="700" {F}>바깥 것은 필요해질 때 찾아 쓰면 됩니다.</text>
  <text x="280" y="360" text-anchor="middle" fill="{SUB}" font-size="15" {F}>
    쓰려면 가운데가 있어야 하고, 그건 오늘 만들었습니다.</text>
""")
