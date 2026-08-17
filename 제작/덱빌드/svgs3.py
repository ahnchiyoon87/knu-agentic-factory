# -*- coding: utf-8 -*-
"""3일차 전용 삽화 — 기준판 v2"""
from svgs import _s, _i, N, N2, O, G

# ── 환각 — 매끄러운 말풍선, 안은 비어 있다
HALLU = _s(520, 400, "0 0 520 400", f"""
<path d="M60 60h380a20 20 0 0 1 20 20v160a20 20 0 0 1-20 20H210l-70 60v-60H60a20 20 0 0 1-20-20V80a20 20 0 0 1 20-20z"
      stroke="{N}" stroke-width="9" stroke-linejoin="round"/>
<g fill="{G}" opacity=".45">
  <rect x="86" y="112" width="240" height="14" rx="7"/>
  <rect x="86" y="150" width="320" height="14" rx="7"/>
  <rect x="86" y="188" width="180" height="14" rx="7"/>
</g>
<path d="M330 176l64 64M394 176l-64 64" stroke="{O}" stroke-width="10" stroke-linecap="round"/>
<text class="lbl-o" x="500" y="330" text-anchor="end">지어낸 값</text>
""")

# ── 다음 낱말을 확률로 고른다 — 환각의 정체
#    전에는 이 장에도 앞 장과 같은 말풍선 그림을 붙여 뒀다. 연속 두 장이 같은 그림이었고,
#    무엇보다 「확률로 고른다」는 이 장의 설명을 그리지 않았다.
NEXTWORD = _s(520, 400, "0 0 520 400", f"""
<rect x="20" y="150" width="196" height="66" rx="10" stroke="{N}" stroke-width="7"/>
<text x="118" y="192" font-size="24" font-weight="700" fill="{N}" text-anchor="middle">EQ-03 온도는</text>
<path d="M224 183h36M260 183l-13-9M260 183l-13 9" stroke="{G}" stroke-width="4" stroke-linecap="round"/>
<rect x="278" y="78" width="222" height="56" rx="9" stroke="{O}" stroke-width="6"
      fill="{O}" fill-opacity=".1"/>
<text x="298" y="114" font-size="24" font-weight="700" fill="{O}">62.4℃</text>
<text x="482" y="114" font-size="22" font-weight="700" fill="{O}" text-anchor="end">0.41</text>
<rect x="278" y="150" width="222" height="56" rx="9" stroke="{G}" stroke-width="4"/>
<text x="298" y="186" font-size="24" fill="{G}">정상입니다</text>
<text x="482" y="186" font-size="22" fill="{G}" text-anchor="end">0.22</text>
<rect x="278" y="222" width="222" height="56" rx="9" stroke="{G}" stroke-width="4"/>
<text x="298" y="258" font-size="24" fill="{G}">조금 높음</text>
<text x="482" y="258" font-size="22" fill="{G}" text-anchor="end">0.14</text>
<text x="260" y="338" font-size="24" font-weight="700" fill="{N}" text-anchor="middle">가장 그럴듯한 것을 고른다</text>
""")

# ── 눈이 없다 — 뇌만 있고 감각기관 없음
NOEYE = _s(520, 400, "0 0 520 400", f"""
<path d="M160 120c0-46 40-78 90-78s90 32 90 78c22 14 34 36 34 62 0 30-20 56-50 66 0 38-34 66-74 66s-74-28-74-66c-30-10-50-36-50-66 0-26 12-48 34-62z"
      stroke="{N}" stroke-width="9" stroke-linejoin="round"/>
<path d="M196 210h108M250 156v108" stroke="{N2}" stroke-width="6" stroke-linecap="round"/>
<g stroke="{G}" stroke-width="6" stroke-dasharray="10 9">
<circle cx="418" cy="96" r="34"/><circle cx="418" cy="210" r="34"/><circle cx="418" cy="324" r="34"/></g>
<g stroke="{O}" stroke-width="7" stroke-linecap="round">
<path d="M396 74l44 44M396 188l44 44M396 302l44 44"/></g>
<text class="lbl-g" x="466" y="102">눈</text>
<text class="lbl-g" x="466" y="216">손</text>
<text class="lbl-g" x="466" y="330">심장</text>
""")

# ── ReAct 루프
REACT = _s(520, 420, "0 0 520 420", f"""
<g stroke-width="10" fill="none" stroke-linecap="round">
  <path d="M260 60a150 150 0 0 1 130 226" stroke="{N}"/>
  <path d="M370 306a150 150 0 0 1-260-40" stroke="{O}"/>
  <path d="M104 246A150 150 0 0 1 240 62" stroke="{N2}"/>
</g>
<path d="M256 44l22 16-22 16" stroke="{N}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
<text x="404" y="152" font-size="26" font-weight="700" fill="{N}">생각</text>
<text x="230" y="398" font-size="26" font-weight="700" fill="{O}" text-anchor="middle">행동</text>
<text x="76" y="140" font-size="26" font-weight="700" fill="{N2}" text-anchor="end">관찰</text>
""")

# ── 한 몸에 다 시키면 — 지시가 길어진다
OVERLOAD = _s(540, 400, "0 0 540 400", f"""
<circle cx="150" cy="200" r="82" stroke="{N}" stroke-width="9"/>
<path d="M124 178h52M124 200h52M124 222h30" stroke="{N2}" stroke-width="6" stroke-linecap="round"/>
<g fill="{G}" opacity=".5">""" +
"".join(f'<rect x="270" y="{88+i*38}" width="{240 - i*14}" height="14" rx="7"/>' for i in range(6)) +
f"""</g>
<path d="M270 320h150" stroke="{O}" stroke-width="6" stroke-dasharray="12 10" stroke-linecap="round"/>
<text class="lbl-o" x="270" y="372">뒤쪽은 흘린다</text>
""")

# ── 표준이 없으면 M×N 으로 얽힌다 (에이전트 4 × 도구 5 = 이음매 20)
#    OVERLOAD(뒤쪽은 흘린다)를 쓰면 「긴 지시가 뒤를 흘린다」는 딴 얘기가 붙는다.
MXN = _s(540, 400, "0 0 540 400", f"""
""" + "".join(
    f'<rect x="40" y="{54 + i * 84}" width="92" height="56" rx="10" '
    f'stroke="{N}" stroke-width="7"/>' for i in range(4)) + "".join(
    f'<rect x="408" y="{40 + i * 66}" width="92" height="46" rx="8" '
    f'stroke="{O}" stroke-width="7"/>' for i in range(5)) + f"""
<g stroke="{G}" stroke-width="2.5" opacity=".75">""" + "".join(
    f'<path d="M132 {82 + a * 84}L408 {63 + t * 66}"/>'
    for a in range(4) for t in range(5)) + f"""</g>

<text x="40" y="392" font-size="32" font-weight="700" fill="{G}">에이전트 4</text>
<text x="500" y="392" font-size="32" font-weight="700" fill="{O}" text-anchor="end">도구 5</text>
""")
# ↑ 이 삽화는 **나란히 비교형(cmp)** 의 반 칸에 들어가 실제로는 절반 크기로 그려진다.
#   공용 라벨 크기(lbl-*)를 그대로 쓰면 슬라이드에서 12px 언저리가 되어 뒷자리에서 안 읽힌다.

# ── 셋으로 쪼갠다 + 총괄
SPLIT3 = _s(540, 420, "0 0 540 420", f"""
<circle cx="270" cy="76" r="48" stroke="{N}" stroke-width="9"/>
<path d="M246 76h48M270 52v48" stroke="{N2}" stroke-width="6" stroke-linecap="round"/>
<path d="M270 124v40M270 164H96v40M270 164h174v40M270 164v40" stroke="{G}" stroke-width="4"/>
<g stroke="{N}" stroke-width="8">
  <rect x="36" y="204" width="120" height="92" rx="10"/>
  <rect x="210" y="204" width="120" height="92" rx="10"/>
  <rect x="384" y="204" width="120" height="92" rx="10"/>
</g>
<text class="lbl" x="96" y="258" text-anchor="middle">감지</text>
<text class="lbl" x="270" y="258" text-anchor="middle">진단</text>
<text class="lbl-o" x="444" y="258" text-anchor="middle">조치</text>
<text class="lbl-g" x="270" y="352" text-anchor="middle">총괄이 나누고 담당이 처리한다</text>
""")

# ── MCP — 도구를 꽂는다
PLUG = _s(520, 400, "0 0 520 400", f"""
<rect x="40" y="120" width="180" height="160" rx="16" stroke="{N}" stroke-width="9"/>
<path d="M86 200h88" stroke="{N2}" stroke-width="6" stroke-linecap="round"/>
<path d="M220 168h70M220 232h70" stroke="{N}" stroke-width="9" stroke-linecap="round"/>
<g stroke="{O}" stroke-width="9" stroke-linejoin="round">
  <path d="M290 140h130v120H290z"/>
  <path d="M290 168h-24M290 232h-24"/>
</g>
<path d="M330 176h50M330 208h34" stroke="{O}" stroke-width="6" stroke-linecap="round"/>
<text x="40" y="336" font-size="32" font-weight="700" fill="{G}">에이전트</text>
<text x="290" y="336" font-size="32" font-weight="700" fill="{O}">내 도구</text>
""")

# ── 전부 자동과 전부 승인 사이 어디에 선을 긋나
#    전에는 앞 장(승인 관문)과 **같은 그림**을 연속으로 썼다. 이 장의 주장은 관문이 아니라
#    「양 끝이 다 틀렸고 우리는 가운데 어딘가에 선을 그었다」는 것이다.
SPECTRUM = _s(520, 400, "0 0 520 400", f"""
<path d="M40 200h440" stroke="{G}" stroke-width="6" stroke-linecap="round"/>
<circle cx="40" cy="200" r="12" fill="{G}"/><circle cx="480" cy="200" r="12" fill="{G}"/>
<text x="20" y="152" font-size="25" font-weight="700" fill="{G}">전부 자동</text>
<text x="500" y="152" font-size="25" font-weight="700" fill="{G}" text-anchor="end">전부 승인</text>
<text x="20" y="256" font-size="22" fill="{G}">오판 한 번에</text>
<text x="20" y="286" font-size="22" fill="{G}">라인이 선다</text>
<text x="500" y="256" font-size="22" fill="{G}" text-anchor="end">무인 운전이</text>
<text x="500" y="286" font-size="22" fill="{G}" text-anchor="end">성립 안 된다</text>
<path d="M300 166v18" stroke="{O}" stroke-width="4"/>
<circle cx="300" cy="200" r="18" fill="{O}"/>
<text x="300" y="152" font-size="26" font-weight="700" fill="{O}" text-anchor="middle">우리가 그은 선</text>
""")

# ── 잠겨 있던 통로 넷이 열린다
#    전에는 이 장에도 MCP 연결 그림(PLUG)을 붙여 뒀다 — 덱에서 세 번째였고,
#    「지금 열렸다」는 이 장의 사건을 그리지 않았다.
UNLOCK4 = _s(520, 400, "0 0 520 400", f"""
<path d="M242 62v-12a15 15 0 0 1 30 0" stroke="{O}" stroke-width="6" fill="none" stroke-linecap="round"/>
<rect x="230" y="62" width="48" height="38" rx="7" stroke="{O}" stroke-width="6"/>
<rect x="30" y="132" width="146" height="196" rx="12" stroke="{N}" stroke-width="8"/>
<path d="M60 176h86M60 212h86M60 248h60" stroke="{N2}" stroke-width="6" stroke-linecap="round"/>
<text x="103" y="372" font-size="25" font-weight="700" fill="{N}" text-anchor="middle">내 코드</text>
<rect x="344" y="132" width="146" height="196" rx="12" stroke="{N}" stroke-width="8"/>
<g stroke="{N2}" stroke-width="6">
<rect x="368" y="164" width="44" height="34" rx="5"/><rect x="422" y="164" width="44" height="34" rx="5"/>
<rect x="368" y="220" width="44" height="34" rx="5"/><rect x="422" y="220" width="44" height="34" rx="5"/></g>
<text x="417" y="372" font-size="25" font-weight="700" fill="{N}" text-anchor="middle">공장</text>
<g stroke="{O}" stroke-width="6" stroke-linecap="round">
<path d="M184 158h140M324 158l-13-9M324 158l-13 9"/>
<path d="M184 202h140M324 202l-13-9M324 202l-13 9"/>
<path d="M184 246h140M324 246l-13-9M324 246l-13 9"/>
<path d="M184 290h140M324 290l-13-9M324 290l-13 9"/></g>
""")

# ── 리포트는 나왔는데 설비로 가는 길이 끊겨 있다
#    전에는 이 장에 「39개 화면」 그림을 붙여 뒀는데, 그건 다 같이 결과를 보는 장의 그림이다.
#    이 장은 8장의 「손이 없다」가 실제로 드러나는 자리다.
NOHAND = _s(520, 400, "0 0 520 400", f"""
<rect x="30" y="90" width="162" height="200" rx="12" stroke="{N}" stroke-width="8"/>
<path d="M62 142h98M62 182h98M62 222h64" stroke="{N2}" stroke-width="6" stroke-linecap="round"/>
<text x="111" y="336" font-size="25" font-weight="700" fill="{N}" text-anchor="middle">진단 리포트</text>
<g stroke="{G}" stroke-width="5" stroke-linecap="round">
<path d="M208 190h40"/><path d="M300 190h40"/></g>
<path d="M256 164l36 52M292 164l-36 52" stroke="{O}" stroke-width="9" stroke-linecap="round"/>
<rect x="352" y="118" width="140" height="144" rx="12" stroke="{N}" stroke-width="8"/>
<g stroke="{N2}" stroke-width="6">
<rect x="378" y="146" width="40" height="32" rx="5"/><rect x="428" y="146" width="40" height="32" rx="5"/>
<rect x="378" y="200" width="40" height="32" rx="5"/><rect x="428" y="200" width="40" height="32" rx="5"/></g>
<text x="422" y="336" font-size="25" font-weight="700" fill="{N}" text-anchor="middle">공장은 그대로</text>
""")

# ── 값이 두 군데서 온다 — 7일치 CSV 와 강사 서버
#    전에는 이 장에도 MCP 연결 그림(PLUG)을 붙여 뒀는데, 그건 네 장 앞에서 이미 쓴 그림이고
#    「어디서 가져오는가」라는 이 장의 제목을 그리지 않았다.
TWOSRC = _s(520, 400, "0 0 520 400", f"""
<rect x="30" y="56" width="150" height="112" rx="10" stroke="{N}" stroke-width="7"/>
<path d="M60 98h90M60 126h70" stroke="{N2}" stroke-width="6" stroke-linecap="round"/>
<text x="105" y="196" font-size="25" font-weight="700" fill="{N}" text-anchor="middle">7일치 CSV</text>
<g stroke="{O}" stroke-width="7" fill="none">
<ellipse cx="105" cy="254" rx="72" ry="22"/>
<path d="M33 254v54c0 12 32 22 72 22s72-10 72-22v-54"/></g>
<text x="105" y="374" font-size="25" font-weight="700" fill="{O}" text-anchor="middle">강사 서버</text>
<g stroke="{G}" stroke-width="4" stroke-linecap="round">
<path d="M196 176h92M288 176l-14-10M288 176l-14 10"/>
<path d="M196 250h92M288 250l-14-10M288 250l-14 10"/></g>
<rect x="304" y="140" width="180" height="146" rx="12" stroke="{N}" stroke-width="8"/>
<path d="M338 190h112M338 224h78" stroke="{N2}" stroke-width="6" stroke-linecap="round"/>
<text x="394" y="326" font-size="25" font-weight="700" fill="{N}" text-anchor="middle">내 도구</text>
""")

# ── 도구 두 개
TOOL2 = _s(520, 380, "0 0 520 380", f"""
<g stroke="{N}" stroke-width="9" stroke-linejoin="round">
  <rect x="40" y="80" width="190" height="150" rx="14"/>
  <rect x="290" y="80" width="190" height="150" rx="14"/>
</g>
<path d="M78 190l30-40 26 28 24-46 32 58" stroke="{O}" stroke-width="7"
      stroke-linecap="round" stroke-linejoin="round"/>
<g fill="{G}" opacity=".5">
  <rect x="326" y="126" width="110" height="12" rx="6"/>
  <rect x="326" y="158" width="80" height="12" rx="6"/>
  <rect x="326" y="190" width="120" height="12" rx="6"/>
</g>
<text class="lbl" x="40" y="278">detect_anomaly</text>
<text class="lbl" x="290" y="278">query_equipment</text>
""")

# ── 되돌릴 수 있는가
UNDO = _s(400, 210, "0 0 400 210", f"""
<path d="M60 130a90 90 0 1 1 26 62" stroke="{N}" stroke-width="10" fill="none" stroke-linecap="round"/>
<path d="M60 92v42h42" stroke="{N}" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
""")
NOUNDO = _s(400, 210, "0 0 400 210", f"""
<path d="M60 130a90 90 0 1 1 26 62" stroke="{G}" stroke-width="10" fill="none"
      stroke-linecap="round" stroke-dasharray="14 12"/>
<path d="M60 92v42h42" stroke="{G}" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M118 60l112 112M230 60L118 172" stroke="{O}" stroke-width="12" stroke-linecap="round"/>
""")

# ── 승인 관문
GATE = _s(520, 400, "0 0 520 400", f"""
<path d="M40 300h140" stroke="{N}" stroke-width="10" stroke-linecap="round"/>
<path d="M340 300h140" stroke="{N}" stroke-width="10" stroke-linecap="round"/>
<g stroke="{N}" stroke-width="10">
  <path d="M180 300V110M340 300V110"/>
</g>
<path d="M180 150h160" stroke="{O}" stroke-width="12" stroke-linecap="round"/>
<circle cx="260" cy="222" r="46" stroke="{N2}" stroke-width="9"/>
<path d="M260 196v30l20 12" stroke="{N2}" stroke-width="7" stroke-linecap="round"/>
<text class="lbl-o" x="260" y="106" text-anchor="middle">사람</text>
<text class="lbl-g" x="40" y="356">에이전트</text>
<text class="lbl-g" x="392" y="356">설비</text>
""")

# ── 닫힌 고리
CLOSED = _s(460, 400, "0 0 460 400", f"""
<g stroke="{N}" stroke-width="12" fill="none" stroke-linecap="round">
  <path d="M230 62a138 138 0 1 1-.1 0"/>
</g>
<path d="M226 44l24 18-24 18" stroke="{O}" stroke-width="11" fill="none"
      stroke-linecap="round" stroke-linejoin="round"/>
<text class="lbl" x="230" y="30" text-anchor="middle">인지</text>
<text class="lbl" x="392" y="212">판단</text>
<text class="lbl-o" x="230" y="386" text-anchor="middle">행동</text>
<text class="lbl-g" x="24" y="212">확인</text>
""")

# ── 전부 소프트웨어 — 화면 안의 공장
SOFTONLY = _s(540, 400, "0 0 540 400", f"""
<rect x="40" y="50" width="460" height="270" rx="14" stroke="{N}" stroke-width="9"/>
<path d="M40 104h460" stroke="{N}" stroke-width="7"/>
<g stroke="{N2}" stroke-width="6">""" +
"".join(f'<rect x="{80+i%3*140}" y="{140+i//3*80}" width="96" height="56" rx="7"/>' for i in range(6)) +
f"""</g>
<path d="M210 320v40h120v-40" stroke="{N}" stroke-width="9" fill="none"/>
<path d="M170 366h200" stroke="{N}" stroke-width="9" stroke-linecap="round"/>
<text class="lbl-o" x="270" y="86" text-anchor="middle">화면 안</text>
""")

# ── 아이콘
ICO_BRAIN = _i('<path d="M24 20c-9 0-15 6-15 14 0 4 2 8 5 10-2 3-3 6-3 9 0 8 6 14 14 14h6V20z"/>'
               '<path d="M52 20c9 0 15 6 15 14 0 4-2 8-5 10 2 3 3 6 3 9 0 8-6 14-14 14h-6V20z"/>'
               '<path d="M38 14v50"/>')
ICO_TOOLS = _i('<path d="M16 60l26-26"/><path d="M40 20a12 12 0 1 0 14 14l10 10-8 8-10-10a12 12 0 0 0-6-22z"/>')
ICO_LOOP2 = _i('<path d="M62 38a24 24 0 1 1-8-18"/><path d="M56 8v14H42"/>')
ICO_AUTO = _i('<circle cx="38" cy="38" r="24"/><path d="M38 22v16l12 8"/><path d="M38 8v6M38 62v6M8 38h6M62 38h6"/>')
ICO_FIND = _i('<circle cx="32" cy="32" r="20"/><path d="M46 46l18 18"/>')
ICO_DIAG = _i('<path d="M20 12h36v52H20z"/><path d="M28 30h20M28 42h14"/><circle cx="52" cy="52" r="8" stroke="'+O+'"/>')
ICO_ACT = _i('<path d="M22 12l32 26-32 26z"/>')
ICO_ORCH = _i('<circle cx="38" cy="18" r="9"/><path d="M38 27v14M38 41H14v12M38 41h24v12M38 41v12"/>')
ICO_STOP = _i('<circle cx="38" cy="38" r="26"/><path d="M28 28h20v20H28z"/>')
ICO_ROBOT = _i('<rect x="16" y="26" width="44" height="32" rx="6"/><path d="M38 16v10"/>'
               '<circle cx="28" cy="42" r="4"/><circle cx="48" cy="42" r="4"/><path d="M24 58v8M52 58v8"/>')
ICO_WAIT = _i('<path d="M22 12h32M22 64h32"/><path d="M26 12c0 16 12 20 12 26s-12 10-12 26"/>'
              '<path d="M50 12c0 16-12 20-12 26s12 10 12 26"/>')
ICO_REPORT = _i('<path d="M18 10h30l12 12v44H18z"/><path d="M48 10v12h12"/><path d="M26 38h24M26 50h16"/>')
