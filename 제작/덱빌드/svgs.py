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
<text class="lbl-g" x="30" y="330">1초마다 기록</text>
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
<text class="lbl-o" x="280" y="374" text-anchor="middle">1초마다 24개</text>
""")

# ── 고정 임계선 (구간 표지용)
LINE80 = _s(460, 360, "0 0 460 360", f"""
<path d="M20 110h420" stroke="{N2}" stroke-width="6" stroke-dasharray="18 12"/>
<path d="M20 300C140 296 300 288 440 276" stroke="{O}" stroke-width="8" stroke-linecap="round"/>
<circle cx="230" cy="110" r="0"/>
<path d="M230 122v140" stroke="{G}" stroke-width="2"/>
<text class="lbl-g" x="230" y="336" text-anchor="middle">넘지 않는다</text>
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

# ── 창이 미끄러진다 (윈도)
SLIDE = _s(700, 360, "0 0 700 360", f"""
<path d="M30 300h640" stroke="{G}" stroke-width="2"/>
<path d="M40 250l46-18 46 10 46-26 46 8 46-24 46 6 46-28 46 10 46-26 46 8 46-22 46 6"
      stroke="{N}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
<rect x="330" y="120" width="240" height="180" rx="8" stroke="{O}" stroke-width="6" fill="{O}" fill-opacity=".07"/>
<path d="M330 340h240" stroke="{O}" stroke-width="2"/>
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
<rect x="76" y="130" width="150" height="12" rx="6"/>
<rect x="76" y="164" width="230" height="12" rx="6"/>
<rect x="76" y="232" width="180" height="12" rx="6"/></g>
<g fill="{O}"><rect x="100" y="198" width="120" height="12" rx="6"/></g>
<path d="M340 190c26-18 52-4 52 18 0 26-34 40-58 56" stroke="{N}" stroke-width="8" stroke-linecap="round"/>
<path d="M334 264h44" stroke="{N}" stroke-width="8" stroke-linecap="round"/>
<text class="lbl-o" x="100" y="330">TODO 3</text>
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
<text class="lbl-o" x="270" y="356" text-anchor="middle">39개 화면</text>
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
ICO_PICK  = _i('<path d="M14 20h34l14 14v22H14z"/><path d="M48 20v14h14" stroke="'+O+'"/>')
ICO_WRITE = _i('<path d="M12 58h52"/><path d="M20 46l4-12 22-22 8 8-22 22z"/>')
ICO_PIN   = _i('<rect x="14" y="12" width="48" height="36" rx="4"/>'
               '<path d="M22 40l12-12 8 8 8-10 8 14" stroke="'+O+'"/><path d="M38 48v16"/>')
