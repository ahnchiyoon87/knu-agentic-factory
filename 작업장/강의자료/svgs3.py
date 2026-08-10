# -*- coding: utf-8 -*-
"""2일차 전용 삽화 — 기준판 v2"""
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
<text class="lbl-o" x="446" y="330">지어낸 값</text>
""")

# ── 눈이 없다 — 뇌만 있고 감각기관 없음
NOEYE = _s(520, 400, "0 0 520 400", f"""
<path d="M160 120c0-46 40-78 90-78s90 32 90 78c22 14 34 36 34 62 0 30-20 56-50 66 0 38-34 66-74 66s-74-28-74-66c-30-10-50-36-50-66 0-26 12-48 34-62z"
      stroke="{N}" stroke-width="9" stroke-linejoin="round"/>
<path d="M196 210h108M250 156v108" stroke="{N2}" stroke-width="6" stroke-linecap="round"/>
<circle cx="418" cy="120" r="34" stroke="{G}" stroke-width="6" stroke-dasharray="10 9"/>
<path d="M396 98l44 44" stroke="{O}" stroke-width="7" stroke-linecap="round"/>
<circle cx="418" cy="300" r="34" stroke="{G}" stroke-width="6" stroke-dasharray="10 9"/>
<path d="M396 278l44 44" stroke="{O}" stroke-width="7" stroke-linecap="round"/>
<text class="lbl-g" x="466" y="126">눈</text>
<text class="lbl-g" x="466" y="306">손</text>
""")

# ── ReAct 루프
REACT = _s(520, 420, "0 0 520 420", f"""
<g stroke="{N}" stroke-width="10" fill="none" stroke-linecap="round">
  <path d="M260 60a150 150 0 0 1 130 226"/>
  <path d="M370 306a150 150 0 0 1-260-40" stroke="{O}"/>
  <path d="M104 246A150 150 0 0 1 240 62"/>
</g>
<path d="M256 44l22 16-22 16" stroke="{N}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
<text class="lbl" x="260" y="196" text-anchor="middle">생각</text>
<text class="lbl-o" x="392" y="352">행동</text>
<text class="lbl-g" x="46" y="216">관찰</text>
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
<text class="lbl-g" x="40" y="330">에이전트</text>
<text class="lbl-o" x="300" y="330">내 도구</text>
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
