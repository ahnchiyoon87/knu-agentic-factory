# -*- coding: utf-8 -*-
"""기준판 v2 삽화 — 남색 #12305A / 주황 #D4541E / 회색 #6B7280
   선 굵기 7~12, 라벨은 낱말만. 본문에 있는 말을 되풀이하지 않는다."""

F = 'font-family="Malgun Gothic, sans-serif"'
N, N2, O, G = "#12305A", "#1E4E8C", "#D4541E", "#6B7280"


def _s(w, h, vb, inner):
    return f'<svg width="{w}" height="{h}" viewBox="{vb}" fill="none" {F}>{inner}</svg>'


# ── 표지 동심원
RINGS = ('<svg class="rings" width="760" height="760" viewBox="0 0 760 760" fill="none" '
         'stroke="#fff" stroke-width="2">' +
         "".join(f'<circle cx="380" cy="380" r="{r}"/>' for r in (110, 180, 250, 320, 375)) +
         "</svg>")

# ── 61.0 vs 61.6 — 눈으로는 구별이 안 된다 (같은 모양으로 그린다)
def _trace(color, y0, dy):
    pts = [(40, 0), (86, -8), (132, 4), (178, -10), (224, 2), (270, -6), (316, 6), (362, -4)]
    d = "M" + " L".join(f"{x} {y0 + p + dy}" for x, p in pts)
    return (f'<path d="M24 {y0+44}h360" stroke="{G}" stroke-width="2"/>'
            f'<path d="{d}" stroke="{color}" stroke-width="7" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')

TRACE_A = _s(400, 200, "0 0 400 200", _trace(N, 110, 0))
TRACE_B = _s(400, 200, "0 0 400 200", _trace(N, 110, -6) +
             f'<path d="M24 154h360" stroke="{O}" stroke-width="2" stroke-dasharray="7 7"/>')

# ── 밤 공장 — 창 하나만 켜짐
NIGHT = _s(560, 430, "0 0 560 430", f"""
<circle cx="80" cy="52" r="24" stroke="{G}" stroke-width="4"/>
<path d="M80 38v14l10 6" stroke="{G}" stroke-width="4" stroke-linecap="round"/>
<text class="lbl-g" x="114" y="62">새벽 3시</text>""" + """""" + f"""
<g stroke="{N}" stroke-width="9" stroke-linejoin="round" stroke-linecap="round">
  <path d="M40 330V150l90 50V150l90 50V150l90 50v180z"/>
  <path d="M310 330V110h150v220z"/>
  <path d="M355 110l30-40 30 40"/>
</g>
<rect x="70" y="230" width="42" height="42" fill="{N}" opacity=".12"/>
<rect x="160" y="230" width="42" height="42" fill="{N}" opacity=".12"/>
<rect x="250" y="230" width="42" height="42" fill="{O}" opacity=".85"/>
<rect x="345" y="180" width="46" height="46" fill="{N}" opacity=".12"/>
<rect x="415" y="180" width="46" height="46" fill="{N}" opacity=".12"/>
<path d="M271 292v34" stroke="{O}" stroke-width="2"/>
<text class="lbl-o" x="271" y="356" text-anchor="middle">EQ-03</text>
""")

# ── 폐기 부품 더미
SCRAP = _s(520, 400, "0 0 520 400", f"""
<g stroke="{N}" stroke-width="8" stroke-linejoin="round">
  <path d="M120 300h280l-26 74H146z"/>
  <circle cx="200" cy="212" r="46"/><circle cx="300" cy="196" r="60"/><circle cx="376" cy="240" r="36"/>
</g>
<path d="M170 182l60 60M230 182l-60 60" stroke="{O}" stroke-width="7" stroke-linecap="round"/>
<path d="M262 158l76 76M338 158l-76 76" stroke="{O}" stroke-width="7" stroke-linecap="round"/>
<path d="M354 218l44 44M398 218l-44 44" stroke="{O}" stroke-width="7" stroke-linecap="round"/>
<path d="M400 344h40" stroke="{G}" stroke-width="2"/>
<text class="lbl-g" x="448" y="352">하루치</text>
""")

# ── 물음표 (구간 표지용)
QMARK = _s(440, 400, "0 0 440 400", f"""
<circle cx="220" cy="200" r="150" stroke="{N}" stroke-width="10"/>
<path d="M172 152c0-28 22-46 50-46s48 18 48 44c0 30-34 34-42 60"
      stroke="{O}" stroke-width="16" stroke-linecap="round"/>
<circle cx="226" cy="278" r="11" fill="{O}"/>
""")

# ── 센서는 있었다 — 계기 + 기록선
SENSOR = _s(540, 400, "0 0 540 400", f"""
<g stroke="{N}" stroke-width="9" stroke-linecap="round">
  <rect x="40" y="90" width="180" height="140" rx="14"/>
  <path d="M76 160h40M136 160h48"/><path d="M76 196h108"/>
</g>
<path d="M220 160h70" stroke="{N2}" stroke-width="5" stroke-dasharray="12 10"/>
<g stroke="{N}" stroke-width="7">
  <path d="M300 250h210"/><path d="M300 250V90"/>
</g>
<path d="M312 226l30-8 26 10 28-12 30 6 28-14 30 8 26-10"
      stroke="{O}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M180 262v40" stroke="{G}" stroke-width="2"/>
<text class="lbl-g" x="30" y="330">1분마다 기록</text>
""")

# ── 24시간 원 (16시간 무인) — 기준판 3번 그대로
CLOCK16 = _s(560, 480, "0 0 560 480", f"""
<path d="M250 230 L250 60 A170 170 0 1 1 102 315 Z" fill="{N}" opacity=".13"/>
<circle cx="250" cy="230" r="170" stroke="{N}" stroke-width="10"/>
<path d="M250 230 L250 116" stroke="{N}" stroke-width="10" stroke-linecap="round"/>
<path d="M250 230 L336 272" stroke="{O}" stroke-width="10" stroke-linecap="round"/>
<circle cx="250" cy="230" r="12" fill="{N}"/>
<path d="M336 108 L392 74" stroke="{G}" stroke-width="2"/>
<text class="lbl-g" x="400" y="76">근무 8시간</text>
<path d="M148 336 L112 396" stroke="{N}" stroke-width="2"/>
<text class="lbl" x="16" y="440">무인으로 도는 16시간</text>
""")

# ── 숫자 쏟아짐 — 설비 6대
FLOOD = _s(560, 420, "0 0 560 420", f"""
<g stroke="{N}" stroke-width="6" fill="none">""" +
"".join(f'<rect x="{40+ i%3*170}" y="{40 + i//3*120}" width="120" height="80" rx="8"/>'
        for i in range(6)) + f"""</g>
<g stroke="{O}" stroke-width="3" stroke-linecap="round" opacity=".8">""" +
"".join(f'<path d="M{72+ i%3*170 + (i//3)*0} {124 + i//3*120}v{34 if i%2 else 26}"/>'
        f'<path d="M{100+ i%3*170} {124 + i//3*120}v{22 if i%2 else 34}"/>'
        f'<path d="M{128+ i%3*170} {124 + i//3*120}v{30}"/>' for i in range(6)) + f"""</g>
<path d="M40 330h480" stroke="{G}" stroke-width="2"/>
<text class="lbl-o" x="280" y="374" text-anchor="middle">쉬지 않고 흐른다</text>
""")
# ↑ 전에는 「1분마다 24개」였다. 24개는 사람이 볼 수 있는 양이라 이 장의 근거가 못 된다
#   (미국 잡숍 조사 업체당 CNC 중앙값 16대 — 우리 6대와 같은 급이다).
#   이 그림이 말할 것은 개수가 아니라 **여섯 줄기가 쉬지 않고 흐른다**는 것이다.

# ── 고정 임계선 (구간 표지용) — **선을 넘으면 울린다**는 아이디어를 그린다.
#    전에는 선 아래로 지나가는 곡선에 「넘지 않는다」를 달아 뒀는데, 그건 **다음 장의 반전**이다.
#    「이 방법이 답 같다」고 제안하는 장에서 그림이 먼저 답을 부정하고 있었다 (절대 규칙 4).
LINE80 = _s(460, 360, "0 0 460 360", f"""
<path d="M20 120h420" stroke="{N2}" stroke-width="6" stroke-dasharray="18 12"/>
<path d="M20 300C150 298 262 258 320 120C350 62 390 54 440 44"
      stroke="{O}" stroke-width="8" stroke-linecap="round"/>
<circle cx="320" cy="120" r="14" fill="{O}"/>
<path d="M320 146v146" stroke="{G}" stroke-width="2"/>
<text class="lbl-o" x="320" y="330" text-anchor="middle">여기서 울린다</text>
""")

# ── 기준판 8번 그래프 — 80℃ / 16℃ 남음 / 62→64
GRAPH80 = _s(720, 380, "0 0 720 380", f"""
<text x="16" y="52" font-size="26" font-weight="700" fill="{N2}">임계값 80℃</text>
<path d="M16 76H704" stroke="{N2}" stroke-width="4" stroke-dasharray="16 12"/>
<path d="M380 88v150M380 88l-9 14M380 88l9 14M380 238l-9-14M380 238l9-14"
      stroke="{G}" stroke-width="2.5" stroke-linecap="round"/>
<rect x="296" y="146" width="168" height="38" fill="#fff"/>
<text x="380" y="172" font-size="25" font-weight="700" fill="{G}" text-anchor="middle">16℃ 남음</text>
<path d="M40 300C220 296 430 282 680 250" stroke="{O}" stroke-width="7" stroke-linecap="round"/>
<text x="16" y="338" font-size="28" font-weight="700" fill="{O}">62℃</text>
<text x="628" y="228" font-size="28" font-weight="700" fill="{O}">64℃</text>
""")

# ── 공장 무대 — CNC 6 + AMR 2
STAGE = _s(520, 420, "0 0 520 420", f"""
<rect x="24" y="30" width="472" height="330" rx="14" stroke="{N}" stroke-width="7"/>
<g stroke="{N}" stroke-width="6">""" +
"".join(f'<rect x="{60+ i%3*140}" y="{70 + i//3*110}" width="96" height="66" rx="7"/>'
        for i in range(6)) + f"""</g>
<circle cx="120" cy="316" r="20" stroke="{O}" stroke-width="6"/>
<circle cx="400" cy="316" r="20" stroke="{O}" stroke-width="6"/>
<path d="M140 316h240" stroke="{O}" stroke-width="2" stroke-dasharray="8 8"/>
<text class="lbl" x="60" y="392">CNC 6</text>
<text class="lbl-o" x="392" y="392">AMR 2</text>
""")

# ── DB 행 8개 (전부 가짜)
ROWS8 = _s(540, 440, "0 0 540 440", f"""
<rect x="40" y="40" width="460" height="46" fill="{N}"/>
<g stroke="#E2E6EB" stroke-width="2">""" +
"".join(f'<path d="M40 {86+ i*38}h460"/>' for i in range(9)) + f"""</g>
<rect x="40" y="40" width="460" height="{86+8*38-40}" stroke="{N}" stroke-width="4"/>
<g fill="{G}">""" +
"".join(f'<rect x="66" y="{100+ i*38}" width="60" height="10" rx="5"/>'
        f'<rect x="170" y="{100+ i*38}" width="86" height="10" rx="5"/>'
        f'<rect x="300" y="{100+ i*38}" width="70" height="10" rx="5"/>'
        f'<rect x="410" y="{100+ i*38}" width="54" height="10" rx="5"/>' for i in range(8)) + f"""</g>
<text class="lbl-o" x="270" y="426" text-anchor="middle">행 여덟 개</text>
""")

# ── 화면 3요소
SCR_BOXES = _s(168, 168, "0 0 168 168", f"""
<g stroke="{N}" stroke-width="8">""" +
"".join(f'<rect x="{16+ i%3*50}" y="{40+ i//3*50}" width="36" height="30" rx="5"/>'
        for i in range(6)) + "</g>")
SCR_DOTS = _s(168, 168, "0 0 168 168", f"""
<circle cx="56" cy="72" r="18" stroke="{O}" stroke-width="8"/>
<circle cx="120" cy="108" r="18" stroke="{O}" stroke-width="8"/>
<path d="M74 82l28 18" stroke="{G}" stroke-width="3" stroke-dasharray="7 7"/>""")
SCR_NUM = _s(168, 168, "0 0 168 168", f"""
<g stroke="{N}" stroke-width="7" stroke-linecap="round">
<path d="M30 62h44M30 96h60M30 130h34"/></g>
<g stroke="{O}" stroke-width="7" stroke-linecap="round">
<path d="M104 56v22M124 50v34M144 62v14"/></g>""")

# ── 이상 3종
AN_DRIFT = _s(200, 150, "0 0 200 150", f"""
<path d="M14 116h172" stroke="{G}" stroke-width="2"/>
<path d="M18 104C60 100 120 84 184 56" stroke="{O}" stroke-width="8" stroke-linecap="round"/>""")
AN_SPIKE = _s(200, 150, "0 0 200 150", f"""
<path d="M14 116h172" stroke="{G}" stroke-width="2"/>
<path d="M18 96h58l16-64 16 64h74" stroke="{O}" stroke-width="8"
      stroke-linecap="round" stroke-linejoin="round"/>""")
AN_MISS = _s(200, 150, "0 0 200 150", f"""
<path d="M14 116h172" stroke="{G}" stroke-width="2"/>
<path d="M18 88l24-14 22 12" stroke="{O}" stroke-width="8" stroke-linecap="round"/>
<path d="M136 82l22 10 26-12" stroke="{O}" stroke-width="8" stroke-linecap="round"/>
<path d="M76 92h50" stroke="{G}" stroke-width="4" stroke-dasharray="8 9"/>""")

# ── 자 세 가지 아이콘
RULER = _s(76, 76, "0 0 76 76", f"""
<g stroke="{N}" stroke-width="5" stroke-linecap="round">
<rect x="8" y="26" width="60" height="24" rx="4"/>
<path d="M20 26v10M32 26v14M44 26v10M56 26v14"/></g>""")
WAVE = _s(76, 76, "0 0 76 76", f"""
<g stroke="{N}" stroke-width="5" stroke-linecap="round" fill="none">
<path d="M8 46c8-18 14 10 22-6s14 12 22-4 10 8 16 2"/>
<path d="M8 60h60" stroke="{G}" stroke-width="2"/></g>""")
WINDOW = _s(76, 76, "0 0 76 76", f"""
<g stroke="{N}" stroke-width="5" fill="none">
<path d="M6 56h64" stroke="{G}" stroke-width="2"/>
<rect x="24" y="14" width="30" height="42" rx="4" stroke="{O}"/>
<path d="M10 40l12-8 12 10 12-16 12 12 8-6" stroke="{N}" stroke-linecap="round"/></g>""")

# ── 이동평균이 따라간다
FOLLOW = _s(560, 380, "0 0 560 380", f"""
<path d="M30 330h500" stroke="{G}" stroke-width="2"/>
<path d="M40 280l40-16 40 8 40-24 40 6 40-22 40 4 40-26 40 8 40-24 40 6 40-20"
      stroke="{O}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M40 296C160 272 320 236 520 196" stroke="{N2}" stroke-width="6"
      stroke-dasharray="14 10" stroke-linecap="round"/>
<text class="lbl-o" x="40" y="120">지금 값</text>
<text class="lbl" x="330" y="150" fill="{N2}">최근 평균</text>
""")

# ── 회전수를 낮추면 온도가 따라 내려간다 (「온도는 회전수의 함수」)
#    FOLLOW(지금 값 / 최근 평균)를 쓰면 제목과 그림이 겉돈다 — 그래서 따로 그린다.
RPMTEMP = _s(560, 400, "0 0 560 400", f"""
<path d="M120 30v330" stroke="{G}" stroke-width="2"/>
<path d="M120 360h420" stroke="{G}" stroke-width="2"/>

<path d="M130 96h170l0 74h230" stroke="{N}" stroke-width="8"
      stroke-linecap="round" stroke-linejoin="round"/>
<text class="lbl" x="112" y="86" text-anchor="end" fill="{N}">회전수</text>

<path d="M130 250h210C380 250 392 300 420 306l110 6" stroke="{O}" stroke-width="8"
      stroke-linecap="round" stroke-linejoin="round"/>
<text class="lbl-o" x="112" y="242" text-anchor="end">온도</text>

<path d="M300 186v46M300 232l-9-12M300 232l9-12" stroke="{G}" stroke-width="3"
      stroke-linecap="round" stroke-linejoin="round"/>
<text class="lbl-g" x="316" y="222">따라온다</text>
""")

# ── 설비마다 평소 온도가 다르다 — 선 하나로는 못 덮는다
#    전에는 **똑같은 물결 여섯 개**를 나란히 쌓았다. 그러면 「제각각」이 아니라 「여러 개」로 읽힌다.
#    흔들리는 모양을 줄마다 다르게 두고, 맨 위·맨 아래에 실제 값을 붙여 폭이 보이게 한다.
_평소들 = (
    (62,  "l52-7 52 9 52-11 52 7 52-9 52 8"),
    (108, "l52 6 52-8 52 5 52-9 52 7 52-5"),
    (178, "l52-5 52 7 52-6 52 9 52-7 52 6"),
    (226, "l52 8 52-6 52 9 52-5 52 8 52-7"),
    (292, "l52-6 52 5 52-8 52 6 52-5 52 7"),
    (336, "l52 5 52-7 52 6 52-8 52 5 52-6"),
)
BASELINES = _s(560, 400, "0 0 560 400", f"""
<path d="M60 366h460" stroke="{G}" stroke-width="2"/>
""" + "".join(
    f'<path d="M80 {y}{d}" stroke="{N}" stroke-width="6" '
    f'stroke-linecap="round" stroke-linejoin="round"/>' for y, d in _평소들) + f"""
<text x="62" y="56" font-size="25" font-weight="700" fill="{N}" text-anchor="end">74℃</text>
<text x="62" y="344" font-size="25" font-weight="700" fill="{N}" text-anchor="end">56℃</text>
<path d="M60 142h460" stroke="{O}" stroke-width="5" stroke-dasharray="14 10"
      stroke-linecap="round"/>
<text class="lbl-o" x="520" y="126" text-anchor="end">경고선 하나</text>
""")

# ── 기준이 값을 따라 올라간다 — 그래서 거리가 끝내 안 벌어진다
#    전에는 이 장에 「인지·행동·판단?」 고리를 붙여 뒀는데, 그건 3일차 폐루프 그림이고
#    「판단?」은 **바로 다음 장의 주제**였다. 이 장의 주장은 그게 아니라 미탐의 원리다.
DRIFTCHASE = _s(560, 400, "0 0 560 400", f"""
<path d="M40 356h480" stroke="{G}" stroke-width="2"/>
<path d="M60 300C160 288 260 250 360 200C420 170 470 152 508 142"
      stroke="{N}" stroke-width="7" stroke-linecap="round"/>
<path d="M60 336C160 324 260 286 360 236C420 206 470 188 508 178"
      stroke="{O}" stroke-width="5" stroke-dasharray="12 9" stroke-linecap="round"/>
<text x="508" y="122" font-size="24" font-weight="700" fill="{N}" text-anchor="end">지금 값</text>
<text x="508" y="228" font-size="24" font-weight="700" fill="{O}" text-anchor="end">기준</text>
<g stroke="{G}" stroke-width="2.5" stroke-linecap="round">
<path d="M180 286v30M180 316l-6-9M180 316l6-9M180 286l-6 9M180 286l6 9"/>
<path d="M420 186v30M420 216l-6-9M420 216l6-9M420 186l-6 9M420 186l6 9"/></g>
<text x="280" y="390" font-size="24" font-weight="700" fill="{G}" text-anchor="middle">거리가 안 벌어진다</text>
""")

# ── 규칙은 숫자만 읽는다 — 사람이 쓴 메모는 못 읽는다
#    4장·22장이 이미 물음표를 쓰고 있어 세 번째로 또 쓰면 「또 그 그림」이 된다.
MEMO = _s(560, 400, "0 0 560 400", f"""
<rect x="40" y="92" width="200" height="212" rx="10" stroke="{N}" stroke-width="6"/>
<g stroke="{N}" stroke-width="7" stroke-linecap="round">
<path d="M74 140h58M162 140h44M74 184h58M162 184h44M74 228h58M162 228h44M74 272h58M162 272h44"/></g>
<text x="140" y="72" font-size="25" font-weight="700" fill="{N}" text-anchor="middle">숫자</text>
<text x="140" y="344" font-size="23" fill="{G}" text-anchor="middle">규칙이 읽는다</text>
<rect x="320" y="92" width="200" height="212" rx="10" stroke="{O}" stroke-width="6"/>
<g stroke="{O}" stroke-width="6" stroke-linecap="round">
<path d="M352 146c14-11 26 11 40 0s26 11 40 0 26 11 40 0"/>
<path d="M352 202c14-11 26 11 40 0s26 11 40 0"/>
<path d="M352 258c14-11 26 11 40 0s26 11 40 0 26 11 40 0"/></g>
<text x="420" y="72" font-size="25" font-weight="700" fill="{O}" text-anchor="middle">사람이 쓴 메모</text>
<text x="420" y="344" font-size="23" fill="{G}" text-anchor="middle">규칙이 못 읽는다</text>
""")

# ── 내가 짠 것과 AI가 짠 것을 **같은 데이터에** 돌려 판정한다
#    전에는 이 장에도 「채울 곳 셋」 그림을 붙여 뒀다 — 바로 다음 장과 같은 그림이라
#    두 번 나오고, 무엇보다 「판정한다」는 이 장의 주장을 그리지 않았다.
JUDGE = _s(560, 400, "0 0 560 400", f"""
<rect x="40" y="76" width="210" height="150" rx="10" stroke="{N}" stroke-width="6"/>
<g stroke="{G}" stroke-width="8" stroke-linecap="round">
<path d="M72 118h120M72 151h150M72 184h100"/></g>
<text x="145" y="56" font-size="25" font-weight="700" fill="{N}" text-anchor="middle">내가 짠 것</text>
<rect x="310" y="76" width="210" height="150" rx="10" stroke="{O}" stroke-width="6"/>
<g stroke="{G}" stroke-width="8" stroke-linecap="round">
<path d="M342 118h150M342 151h110M342 184h140"/></g>
<text x="415" y="56" font-size="25" font-weight="700" fill="{O}" text-anchor="middle">AI가 짠 것</text>
<g stroke="{G}" stroke-width="3" stroke-linecap="round">
<path d="M145 238v44M145 282l-9-14M145 282l9-14"/>
<path d="M415 238v44M415 282l-9-14M415 282l9-14"/></g>
<rect x="40" y="296" width="480" height="58" rx="9" fill="{N}" fill-opacity=".08"
      stroke="{N}" stroke-width="3"/>
<text x="280" y="334" font-size="26" font-weight="700" fill="{N}" text-anchor="middle">같은 7일치에 돌린다</text>
""")

# ── 지금 값은 창에 넣지 않는다
#    전에는 이 장에 작은 창 아이콘을 360px 로 늘려 붙여 뒀는데, 선이 상자를 뚫고 나가 조잡했고
#    무엇보다 **제목을 그리지 않았다.** 창은 앞의 W개만 감싸고 지금 값은 그 밖에 있다는 것,
#    그리고 그 거리가 z 라는 것을 한 장면으로 그린다.
NOWOUT = _s(560, 400, "0 0 560 400", f"""
<path d="M40 340h480" stroke="{G}" stroke-width="2"/>
<rect x="46" y="214" width="250" height="80" rx="10" stroke="{O}" stroke-width="5"
      fill="{O}" fill-opacity=".07"/>
<text class="lbl-o" x="171" y="200" text-anchor="middle">창 — 앞의 W개</text>
<g fill="{N}">
<circle cx="80" cy="266" r="9"/><circle cx="124" cy="248" r="9"/>
<circle cx="168" cy="272" r="9"/><circle cx="212" cy="252" r="9"/>
<circle cx="256" cy="258" r="9"/>
</g>
<path d="M46 258h424" stroke="{N2}" stroke-width="3" stroke-dasharray="10 8"/>
<text x="484" y="266" font-size="26" font-weight="700" fill="{N2}">μ</text>
<circle cx="400" cy="96" r="13" fill="{O}"/>
<text class="lbl-o" x="400" y="66" text-anchor="middle">지금 값</text>
<path d="M400 116v134M400 116l-9 14M400 116l9 14M400 250l-9-14M400 250l9-14"
      stroke="{G}" stroke-width="2.5" stroke-linecap="round"/>
<text x="418" y="192" font-size="26" font-weight="700" fill="{G}">z</text>
""")

# ── 창이 미끄러진다 (윈도)
SLIDE = _s(700, 360, "0 0 700 360", f"""
<path d="M30 300h640" stroke="{G}" stroke-width="2"/>
<path d="M40 250l46-18 46 10 46-26 46 8 46-24 46 6 46-28 46 10 46-26 46 8 46-22 46 6"
      stroke="{N}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
<rect x="330" y="120" width="240" height="180" rx="8" stroke="{O}" stroke-width="6" fill="{O}" fill-opacity=".07"/>
<text class="lbl-o" x="450" y="106" text-anchor="middle">최근 W개</text>
<path d="M600 210h56M656 210l-14-10M656 210l-14 10" stroke="{G}" stroke-width="3" stroke-linecap="round"/>
""")

# ── 오탐 / 미탐
FP = _s(400, 200, "0 0 400 200", f"""
<path d="M60 150h280" stroke="{G}" stroke-width="2"/>
<path d="M70 130l40-8 40 6 40-10 40 8 40-6 40 10 40-8"
      stroke="{N}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
<g stroke="{O}" stroke-width="5" stroke-linecap="round">
<path d="M126 60v24M206 46v38M286 62v22"/></g>
<circle cx="126" cy="44" r="7" fill="{O}"/><circle cx="206" cy="30" r="7" fill="{O}"/>
<circle cx="286" cy="46" r="7" fill="{O}"/>""")
FN = _s(400, 200, "0 0 400 200", f"""
<path d="M60 150h280" stroke="{G}" stroke-width="2"/>
<path d="M70 132C140 128 230 108 340 78" stroke="{O}" stroke-width="7" stroke-linecap="round"/>
<circle cx="230" cy="104" r="26" stroke="{G}" stroke-width="4" stroke-dasharray="8 8"/>
<path d="M256 78l30-30" stroke="{G}" stroke-width="3"/>
<text class="lbl-g" x="292" y="42">놓침</text>""")

# ── 잡았다 — 이상 구간(오르는 곡선) 위에서 알람이 울린 그림
#    「잡은 쪽」 자리에 FN(놓침)을 쓰면 그림이 정반대를 말한다.
HIT = _s(400, 200, "0 0 400 200", f"""
<path d="M60 150h280" stroke="{G}" stroke-width="2"/>
<path d="M70 132C140 128 230 108 340 78" stroke="{N}" stroke-width="7" stroke-linecap="round"/>
<g stroke="{O}" stroke-width="5" stroke-linecap="round">
<path d="M212 60v52M272 48v46M332 40v34"/></g>
<circle cx="212" cy="46" r="7" fill="{O}"/><circle cx="272" cy="34" r="7" fill="{O}"/>
<circle cx="332" cy="26" r="7" fill="{O}"/>""")

# ── 저울 (맞바꿈)
SCALE = _s(460, 400, "0 0 460 400", f"""
<g stroke="{N}" stroke-width="9" stroke-linecap="round">
  <path d="M230 60v230"/><path d="M150 340h160"/><path d="M230 290h0"/>
  <path d="M70 96h320"/>
</g>
<path d="M70 96l-42 84h84z" stroke="{O}" stroke-width="7" stroke-linejoin="round"/>
<path d="M390 96l-42 84h84z" stroke="{N2}" stroke-width="7" stroke-linejoin="round"/>
<path d="M180 340h100v22H180z" stroke="{N}" stroke-width="7"/>
<text class="lbl-o" x="70" y="222" text-anchor="middle">오탐</text>
<text class="lbl" x="390" y="222" text-anchor="middle" fill="{N2}">미탐</text>
""")

# ── 직접 짠다 — 손과 코드
BYHAND = _s(520, 380, "0 0 520 380", f"""
<rect x="40" y="40" width="440" height="240" rx="12" stroke="{N}" stroke-width="8"/>
<path d="M40 96h440" stroke="{N}" stroke-width="6"/>
<g fill="{G}">
<rect x="76" y="126" width="150" height="12" rx="6"/>
<rect x="76" y="182" width="196" height="12" rx="6"/>
<rect x="76" y="238" width="164" height="12" rx="6"/></g>
<g stroke="{O}" stroke-width="7" fill="none">
<rect x="286" y="118" width="62" height="28" rx="6"/>
<rect x="356" y="118" width="62" height="28" rx="6"/>
<rect x="286" y="174" width="62" height="28" rx="6"/>
<rect x="356" y="174" width="62" height="28" rx="6"/>
<rect x="286" y="230" width="62" height="28" rx="6"/></g>
<text class="lbl-o" x="286" y="330">함수 셋 · 빈칸 다섯</text>
""")

# ── TODO 아이콘 3
T1 = _s(76, 76, "0 0 76 76", f"""
<g stroke="{N}" stroke-width="5" fill="none" stroke-linecap="round">
<rect x="12" y="20" width="52" height="36" rx="5"/><path d="M12 38h52M38 20v36"/></g>""")
T2 = _s(76, 76, "0 0 76 76", f"""
<g stroke="{N}" stroke-width="5" fill="none" stroke-linecap="round">
<path d="M10 54h56"/><path d="M10 30h56" stroke="{O}" stroke-dasharray="7 6"/>
<path d="M26 54V40M44 54V18M60 54V44"/></g>""")
T3 = _s(76, 76, "0 0 76 76", f"""
<g stroke="{N}" stroke-width="5" fill="none" stroke-linecap="round">
<path d="M10 48h18M48 48h18"/><path d="M30 48h16" stroke="{O}" stroke-dasharray="6 6"/>
<circle cx="38" cy="26" r="8" stroke="{O}"/></g>""")

# ── 다 같이 실행 — 화면 여러 개
ALLRUN = _s(540, 380, "0 0 540 380", f"""
<g stroke="{N}" stroke-width="6" fill="none">""" +
"".join(f'<rect x="{40+ i%4*126}" y="{60+ i//4*130}" width="104" height="80" rx="8"/>'
        for i in range(8)) + f"""</g>
<g fill="{O}">""" +
"".join(f'<rect x="{58+ i%4*126}" y="{158+ i//4*130}" width="{40+ (i*7)%36}" height="9" rx="4"/>'
        for i in range(8)) + f"""</g>
<text class="lbl-o" x="270" y="356" text-anchor="middle">모두의 화면</text>
""")

# ── 열린 고리 (누가 판단하나)
OPENLOOP = _s(460, 400, "0 0 460 400", f"""
<g stroke="{N}" stroke-width="11" stroke-linecap="round" fill="none">
  <path d="M230 66a134 134 0 0 1 0 268"/>
  <path d="M230 66a134 134 0 0 0-96 40"/>
</g>
<path d="M120 128a134 134 0 0 0-24 72" stroke="{G}" stroke-width="11"
      stroke-dasharray="10 18" stroke-linecap="round"/>
<circle cx="104" cy="252" r="9" fill="{O}"/>
<path d="M104 252a134 134 0 0 0 126 82" stroke="{N}" stroke-width="11" stroke-linecap="round"/>
<text class="lbl-o" x="30" y="252" text-anchor="middle">?</text>
<text class="lbl" x="230" y="42" text-anchor="middle">인지</text>
<text class="lbl" x="392" y="212">행동</text>
<text class="lbl-o" x="16" y="200">판단</text>
""")


# ═══ 레일용 아이콘 76×76 (뜻에 맞는 것만 쓴다) ═══
def _i(inner, sw=5, c=None):
    return _s(76, 76, "0 0 76 76",
              f'<g stroke="{c or N}" stroke-width="{sw}" fill="none" '
              f'stroke-linecap="round" stroke-linejoin="round">{inner}</g>')

ICO_CLOCK = _i('<circle cx="38" cy="40" r="27"/><path d="M38 24v16l11 7"/><path d="M28 8h20"/>')
ICO_EYE   = _i('<path d="M6 38s12-19 32-19 32 19 32 19-12 19-32 19S6 38 6 38z"/><circle cx="38" cy="38" r="9"/>')
ICO_GRID  = _i("".join(f'<rect x="{6+i%3*23}" y="{12+i//3*24}" width="19" height="19" rx="3"/>'
                       for i in range(6)))
ICO_PEN   = _i('<path d="M14 62l6-18L50 14l12 12-30 30z"/><path d="M46 18l12 12"/>')
ICO_SLIDE = _i('<path d="M10 24h56M10 52h56"/><circle cx="28" cy="24" r="8" stroke="'+O+'"/>'
               '<circle cx="50" cy="52" r="8" stroke="'+O+'"/>')
ICO_CMP   = _i('<rect x="8" y="16" width="24" height="44" rx="4"/>'
               '<rect x="44" y="16" width="24" height="44" rx="4" stroke="'+O+'"/>')
ICO_SCREEN= _i('<rect x="8" y="14" width="60" height="40" rx="5"/><path d="M26 66h24M38 54v12"/>')
ICO_CODE  = _i('<path d="M26 22L10 38l16 16"/><path d="M50 22l16 16-16 16"/><path d="M42 16L34 60" stroke="'+O+'"/>')
ICO_BAL   = _i('<path d="M38 14v46M22 60h32"/><path d="M12 26h52"/>'
               '<path d="M12 26l-6 16h12z" stroke="'+O+'"/><path d="M64 26l-6 16h12z"/>')
ICO_SHIELD= _i('<path d="M38 8l24 9v18c0 15-10 26-24 32C24 61 14 50 14 35V17z"/>'
               '<path d="M28 38l7 7 14-15" stroke="'+O+'"/>')
ICO_PICK  = _i('<path d="M14 20h34l14 14v22H14z"/><path d="M48 20v14h14" stroke="'+O+'"/>')
ICO_WRITE = _i('<path d="M12 58h52"/><path d="M20 46l4-12 22-22 8 8-22 22z"/>')
# 번호 하나로 내 공장을 되찾는다 — ICO_PIN 은 「그래프가 든 판」이라 이 뜻이 안 산다
ICO_KEY   = _i('<circle cx="24" cy="38" r="13"/><path d="M37 38h30"/>'
               '<path d="M55 38v12M65 38v9" stroke="'+O+'"/>')
ICO_PIN   = _i('<rect x="14" y="12" width="48" height="36" rx="4"/>'
               '<path d="M22 40l12-12 8 8 8-10 8 14" stroke="'+O+'"/><path d="M38 48v16"/>')
