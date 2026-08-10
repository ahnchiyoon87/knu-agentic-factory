# -*- coding: utf-8 -*-
"""노션 자산화 80분 덱 생성기
  조작 슬라이드 = 목업 없이 큰 글씨 한 장 = 한 동작
  체크포인트 슬라이드 = 큰 노션 목업 하나 ("지금 화면이 이래야 합니다")
"""
import pathlib, re

HERE = pathlib.Path(__file__).parent
OUT = HERE / "노션덱_80분.html"

# ══════════════════════════════════════════ 노션 목업 빌더
DOTS = ('<div class="dt" style="background:#F6605C"></div>'
        '<div class="dt" style="background:#F7BD4F"></div>'
        '<div class="dt" style="background:#3FC14A"></div>')

def sidebar(sel="page", card=False, extra=""):
    rows = ['<div class="ws"><div class="av">김</div>내 노션</div>',
            '<div class="r"><span class="ic">🔍</span>검색</div>',
            '<div class="r"><span class="ic">🏠</span>홈</div>',
            '<div class="cp">개인 페이지</div>']
    ic = "📊" if sel != "plain" else "📄"
    rows.append(f'<div class="r on"><span class="ic">{ic}</span>경남대 특강 — Day 2</div>')
    if card:
        rows.append('<div class="r ind"><span class="ic">📁</span>개념 카드</div>')
    rows.append('<div class="cp">기타</div><div class="r"><span class="ic">＋</span>새 페이지</div>')
    return '<div class="sd">' + "".join(rows) + extra + '</div>'

def db_table(cols, rows, add=True):
    th = "".join(f'<th style="width:{w}">{c}</th>' for c, w in cols)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
    if add:
        body += f'<tr><td class="addr" colspan="{len(cols)}">＋ 새로 만들기</td></tr>'
    return f'<table class="db"><tr>{th}</tr>{body}</table>'

CARDS = [
    ("📉", "#FFF3F1", "드리프트는 왜 안 잡혔나", "c-r", "설명못함"),
    ("📊", "#FFFAEE", "z-score의 3은 어디서 온 숫자인가", "c-y", "대충앎"),
    ("⚖️", "#F2F9F2", "오탐과 미탐 중 뭘 줄이나", "c-g", "설명가능"),
    ("🕳", "#F3F6FB", "센서가 끊기면 계산이 어떻게 되나", "c-r", "설명못함"),
    ("🪟", "#FAF4FB", "윈도 60은 무슨 근거인가", "c-y", "대충앎"),
]

def gallery(items):
    out = ""
    for em, bg, ti, cc, cl in items:
        out += (f'<div class="gcd"><div class="pv" style="background:{bg}">{em}</div>'
                f'<div class="bo"><div class="ti">{ti}</div>'
                f'<div class="mt"><span class="chip {cc}">{cl}</span></div></div></div>')
    return f'<div class="gal">{out}</div>'

def window(inner, url="notion.so/경남대-특강-Day2", h=452, sd=None, cls=""):
    sd = sidebar() if sd is None else sd
    return (f'<div class="win {cls}"><div class="cr">{DOTS}'
            f'<div class="ur">🔒 {url}</div></div>'
            f'<div class="nt" style="height:{h}px">{sd}'
            f'<div class="mn">{inner}</div></div></div>')

def page(cover=True, icon="📊", title="경남대 특강 — Day 2", sub="이상 감지 · 2026-08-11",
         div=True, h1="개념 카드", body="", cov_h=120, ic_sz=46, tt_sz=29, ph=False):
    s = f'<div class="cvr" style="height:{cov_h}px"></div>' if cover else ""
    s += '<div class="pd">'
    if icon:
        s += f'<div class="pic" style="font-size:{ic_sz}px;margin-top:-{int(ic_sz*.6)}px">{icon}</div>'
    cl = "ptt ph" if ph else "ptt"
    s += f'<div class="{cl}" style="font-size:{tt_sz}px">{title}</div>'
    if sub:
        s += f'<div class="nbx nmu">{sub}</div>'
    if div:
        s += '<div class="nhr"></div>'
    if h1:
        s += f'<div class="nh1">{h1}</div>'
    s += body + "</div>"
    return s

def dbhead(view="표", views=("표",), right=True):
    tabs = "".join(f'<div class="vt">{v}</div>' if v == view else f"<div>{v}</div>" for v in views)
    r = ('<div class="rt"><span>필터</span><span>정렬</span>'
         '<span class="nbtn">새로 만들기 ▾</span></div>') if right else ""
    return f'<div class="dbh">{tabs}<div>＋</div>{r}</div>'

def card_panel(inner, ihd="비어 있음", src="비어 있음", title="제목 없음", ph=True):
    cl = "ptt ph" if ph else "ptt"
    return ('<div class="mn" style="background:rgba(15,15,15,.06)">'
            '<div class="cpanel">'
            '<div class="cbar">⤢ &nbsp; ⋯ &nbsp; ✕</div><div style="padding:0 30px">'
            f'<div class="{cl}" style="font-size:21px;margin-top:12px">{title}</div>'
            f'<div class="prow"><span>⌄ 이해도</span><span>{ihd}</span></div>'
            f'<div class="prow"><span>≡ 출처</span><span>{src}</span></div>'
            '<div class="nhr"></div>' + inner + '</div></div></div>')

def card_window(inner, url="notion.so/경남대-특강-Day2", h=452, **kw):
    return (f'<div class="win"><div class="cr">{DOTS}<div class="ur">🔒 {url}</div></div>'
            f'<div class="nt" style="height:{h}px">' + sidebar(card=True).replace('class="sd"', 'class="sd" style="opacity:.45"')
            + card_panel(inner, **kw) + '</div></div>')

# ══════════════════════════════════════════ 슬라이드 조립
S = []

def cover_slide():
    S.append('<section class="s cv"><div class="ring"></div><div class="bd">'
             '<div class="eb">경남대 피지컬AI 사관학교 · 8월 특강 Day 2</div>'
             '<h1>노션으로 자산화하기</h1>'
             '<p>80분 · 오늘 배울 것을 담을 그릇을 먼저 만듭니다</p></div></section>')

def sl(label, sub, body, cls=""):
    S.append(f'<section class="s {cls}"><div class="hd"><div class="l">{label}'
             f'<i>{sub}</i></div><div class="r"></div></div>'
             f'<div class="bd">{body}</div>'
             '<div class="ft"><div>노션으로 자산화하기</div><div></div></div></section>')

def act(label, sub, num, text, note=""):
    """조작 슬라이드 — 목업 없음"""
    n = f'<div class="actn">{num}</div>' if num else ""
    nt = f'<div class="actsub">{note}</div>' if note else ""
    sl(label, sub, f'<div class="cen">{n}<div class="acttx">{text}</div>{nt}</div>')

def chk(cap, mock, label="체크포인트", sub="지금 화면이 이래야 합니다"):
    """체크포인트 슬라이드 — 큰 목업"""
    sl(label, sub, f'<div class="cap">{cap}</div>{mock}')

def big(label, sub, text, note=""):
    nt = f'<div class="actsub" style="max-width:900px">{note}</div>' if note else ""
    sl(label, sub, f'<div class="cen"><div class="big">{text}</div>{nt}</div>')

# ─────────────────────────── 도입
cover_slide()

sl("시작", "오늘 1교시의 흐름",
   '<div class="mid"><h1 class="t">오늘 1교시는 <em>세 도막</em>입니다</h1>'
   '<div class="li3">'
   '<div class="c"><div class="k">지금 · 80분</div><div class="h">그릇을 만든다</div>'
   '<div class="p">노션에 빈 껍데기를 만듭니다. 내용은 한 글자도 안 씁니다.</div></div>'
   '<div class="c"><div class="k">오후 · 130분</div><div class="h">수업을 듣는다</div>'
   '<div class="p">공장을 보고, 고장을 보고, 코드를 짭니다. 필기는 노션에.</div></div>'
   '<div class="c"><div class="k">끝 · 20분</div><div class="h">채운다</div>'
   '<div class="p">오늘 안 풀린 것을 카드로 만듭니다.</div></div></div>'
   '<div class="nb1"><b>4일이 쌓이면</b> 링크 하나로 보여줄 수 있는 페이지가 됩니다.</div></div>')

chk("80분 뒤 — 여러분 화면",
    window(page(cover=True, cov_h=110, ic_sz=44, tt_sz=28,
                body=dbhead("갤러리", ("갤러리", "표")) + gallery(CARDS[:3])),
           h=452),
    label="미리 보기", sub="완성본")

big("전제", "오해하면 안 되는 것",
    '지금 만드는 건 <span>빈 껍데기</span>입니다',
    '80분 동안 <b style="color:#1a1a1a">내용은 한 글자도 안 씁니다.</b><br>오후 수업이 내용입니다.')

act("준비", "시작 전", "", '<kbd>notion.so</kbd> 로그인',
    '안 되어 있으면 지금 가입 — 무료 요금제로 충분합니다')
act("준비", "시작 전", "", '왼쪽 위 <kbd>»</kbd> 로 사이드바 펼치기',
    '막히면 손만 드세요. 앞에 나올 일은 없습니다')

# ─────────────────────────── 01 페이지 · 아이콘 · 커버
act("기능 01", "페이지", "01-1", '사이드바 맨 아래 <kbd>＋ 새 페이지</kbd>')
act("기능 01", "페이지", "01-2", '제목에 <kbd>경남대 특강 — Day 2</kbd>',
    '「비어 있는 페이지」를 고르세요. 템플릿은 쓰지 않습니다')
act("기능 02", "아이콘", "02-1", '제목 위 <kbd>아이콘 추가</kbd>')
act("기능 02", "아이콘", "02-2", '검색 <kbd>chart</kbd> → <em>📊</em> 선택',
    '사이드바에도 같이 붙습니다')
act("기능 03", "커버", "03-1", '<kbd>커버 추가</kbd>')
act("기능 03", "커버", "03-2", '커버 위에서 <kbd>커버 변경</kbd>',
    '「색상 및 그라데이션」에서 고르면 가장 깔끔합니다')
act("기능 03", "커버", "03-3", '<kbd>위치 변경</kbd> 으로 보이는 구간 조정')

chk("페이지 · <b>아이콘</b> · <b>커버</b>",
    window(page(cov_h=150, ic_sz=52, tt_sz=32, sub="", div=False, h1="",
                body='<div class="nbx nmu" style="margin-top:16px">키보드로 입력을 시작하거나 '
                     '<span class="slk">/</span> 를 눌러 명령어를 사용하세요</div>')))

# ─────────────────────────── 04 슬래시
sl("기능 04", "슬래시 명령",
   '<div class="mid"><h1 class="t">노션의 모든 것은 <em>/</em> 로 꺼냅니다</h1>'
   '<div class="sb">빈 줄에서 <kbd>/</kbd> 를 치고 앞 글자만 입력하면 목록이 좁혀집니다.</div>'
   '<div class="g2">'
   '<div class="it"><b>/제</b>목1<span>큰 제목</span></div>'
   '<div class="it"><b>/구</b>분선<span>가로줄</span></div>'
   '<div class="it"><b>/표</b><span>데이터베이스</span></div>'
   '<div class="it"><b>/코</b>드<span>코드 블록</span></div>'
   '<div class="it"><b>/토</b>글<span>접었다 펴기</span></div>'
   '<div class="it"><b>/할</b> 일<span>체크박스</span></div></div>'
   '<div class="nb1">지금부터 나오는 조작은 <b>거의 전부 이 한 글자</b>로 시작합니다.</div></div>')

# ─────────────────────────── 05 골격
act("기능 05", "골격", "05-1", '<kbd>이상 감지 · 2026-08-11</kbd> 한 줄 입력')
act("기능 05", "골격", "05-2", '<kbd>/구분선</kbd>')
act("기능 05", "골격", "05-3", '<kbd>/제목1</kbd> → <kbd>개념 카드</kbd>')

chk("골격 — 부제 · <b>구분선</b> · <b>제목1</b>",
    window(page(cov_h=130, ic_sz=48, tt_sz=30,
                body='<div class="nbx nmu" style="margin-top:10px">'
                     '<span class="slk">/</span></div>')))

# ─────────────────────────── 06 데이터베이스
act("기능 06", "데이터베이스", "06-1", '「개념 카드」 아래에서 <kbd>/표</kbd>')
act("기능 06", "데이터베이스", "06-2", '<em>표 보기</em> 선택',
    '맨 아래 「표」(단순 표 블록)가 아니라 <b>위쪽 데이터베이스</b> 항목입니다')
act("기능 06", "데이터베이스", "06-3", '<em>＋ 새 데이터베이스</em>')
act("기능 06", "데이터베이스", "06-4", '표 이름 <kbd>개념 카드</kbd>')
act("기능 06", "데이터베이스", "06-5", '「태그」 열 클릭 → <em>속성 삭제</em>',
    '기본으로 딸려 나오는 열입니다. 우리는 다른 두 개를 씁니다')

chk("빈 표 — 「태그」 열 <b>삭제됨</b>",
    window(page(cov_h=110, ic_sz=42, tt_sz=27,
                body=dbhead() + db_table([("Aa 이름", "100%")], [["&nbsp;"], ["&nbsp;"], ["&nbsp;"]])),
           sd=sidebar(card=True)))

# ─────────────────────────── 07 속성
act("기능 07", "속성 ① 이해도", "07-1", '표 오른쪽 끝 <kbd>＋</kbd>')
act("기능 07", "속성 ① 이해도", "07-2", '이름 <kbd>이해도</kbd> · 유형 <em>선택</em>')
act("기능 07", "속성 ① 이해도", "07-3", '옵션 세 개 입력',
    '칸에 치고 <kbd>Enter</kbd> 를 누르면 옵션이 만들어집니다')

sl("기능 07", "옵션 세 개",
   '<div class="cen"><div class="big">옵션은 <span>세 개</span>만</div>'
   '<div class="chips">'
   '<div><span class="chip c-r big3">설명못함</span><p>아예 모르겠다</p></div>'
   '<div><span class="chip c-y big3">대충앎</span><p>들으면 알겠는데 말은 못 함</p></div>'
   '<div><span class="chip c-g big3">설명가능</span><p>안 보고 남한테 설명 가능</p></div>'
   '</div><div class="nb1" style="margin-top:36px;max-width:780px;text-align:left">'
   '색이 다르면 <b>표만 봐도 뭘 더 봐야 하는지</b> 한눈에 보입니다.</div></div>')

act("기능 07", "속성 ① 이해도", "07-4", '옵션마다 <kbd>⋯</kbd> → 색을 서로 다르게')
act("기능 08", "속성 ② 출처", "08-1", '다시 <kbd>＋</kbd> → 이름 <kbd>출처</kbd> · 유형 <em>텍스트</em>')

big("기능 08", "여기서 멈춤", '속성은 <span>두 개</span>까지',
    '날짜 · 관계형 · 수식은 오늘 쓰지 않습니다.<br>더 붙이면 관리만 늘어나고 결국 안 씁니다.')

chk("속성 <b>이해도</b> · <b>출처</b>",
    window(page(cov_h=110, ic_sz=42, tt_sz=27,
                body=dbhead() + db_table(
                    [("Aa 이름", "52%"), ("⌄ 이해도", "24%"), ("≡ 출처", "24%")],
                    [["&nbsp;", "", ""], ["&nbsp;", "", ""]])),
           sd=sidebar(card=True)))

# ─────────────────────────── 09 행 = 페이지
big("기능 09", "구조", '표의 한 줄 = <span>페이지 한 장</span>',
    '표는 목록일 뿐입니다. 진짜 내용은 줄을 열면 나오는 페이지 안에 들어갑니다.')
act("기능 09", "카드 열기", "09-1", '첫 줄에 아무 글자나 치고 <kbd>Enter</kbd>')
act("기능 09", "카드 열기", "09-2", '줄 위 <kbd>열기</kbd> 클릭')

chk("카드 한 장 — <b>열린 화면</b>",
    card_window('<div class="nbx nmu">＋ 를 눌러 블록을 추가하거나 '
                '<span class="slk">/</span> 로 명령</div>'))

# ─────────────────────────── 10 템플릿
sl("기능 10", "템플릿 — 왜 지금 만드나",
   '<div class="mid"><h1 class="t">카드마다 <em>같은 양식</em>이 자동으로 뜨게 합니다</h1>'
   '<div class="li3" style="margin-top:36px">'
   '<div class="c"><div class="k">지금</div><div class="h">양식을 한 번 만든다</div>'
   '<div class="p">네 구획짜리 빈 양식</div></div>'
   '<div class="c"><div class="k">오후</div><div class="h">버튼만 누른다</div>'
   '<div class="p">「새로 만들기 ▾ → 개념 카드」</div></div>'
   '<div class="c"><div class="k">결과</div><div class="h">칸만 채우면 끝</div>'
   '<div class="p">양식 짤 시간에 내용을 쓴다</div></div></div>'
   '<div class="nb1">이게 없으면 40분 실습에서 <b>양식 치다가 필기를 못 합니다.</b></div></div>')

act("기능 10", "템플릿", "10-1", '<kbd>새로 만들기</kbd> 옆 <em>▾</em>')
act("기능 10", "템플릿", "10-2", '<em>＋ 새 템플릿</em>')
act("기능 10", "템플릿", "10-3", '템플릿 이름 <kbd>개념 카드</kbd>')
act("기능 11", "제목2 · 이모지", "11-1", '<kbd>/제목2</kbd> 로 네 줄 만들기',
    '이모지는 붙여 넣으세요')

sl("기능 11", "네 구획 — 이대로 칩니다",
   '<div class="mid"><h1 class="t sm">이 네 줄을 그대로 칩니다</h1>'
   '<div class="four">'
   '<div class="fq"><span class="fe">🗣</span><b>안 보고 설명하면</b>'
   '<i>화면 덮고 내 문장으로</i></div>'
   '<div class="fq"><span class="fe">❓</span><b>이게 없으면 뭐가 안 되나</b>'
   '<i>쓸모를 한 줄로</i></div>'
   '<div class="fq"><span class="fe">💻</span><b>코드로는</b>'
   '<i>코드 블록 한 덩어리</i></div>'
   '<div class="fq"><span class="fe">▸</span><b>수업 화면 / 내 필기</b>'
   '<i>토글로 만듭니다 — 접어 둡니다</i></div>'
   '</div></div>')

chk("템플릿 — <b>네 구획</b>",
    card_window('<div class="nh2" style="margin-top:6px">🗣 안 보고 설명하면</div>'
                '<div class="nh2">❓ 이게 없으면 뭐가 안 되나</div>'
                '<div class="nh2">💻 코드로는</div>'
                '<div class="ntog" style="margin-top:12px"><span class="ar">▸</span>'
                '<span style="font-weight:700">수업 화면 / 내 필기</span></div>',
                title="개념 카드", ph=False))

# ─────────────────────────── 규칙 두 개
sl("규칙", "이 양식이 이 순서인 이유",
   '<div class="mid"><h1 class="t">규칙은 <em>두 개</em>뿐입니다</h1>'
   '<div class="two">'
   '<div><div class="h">화면을 덮고 쓴다</div>'
   '<p>보면서 쓰면 옮겨 적기입니다.<br>덮고 쓰면 <b>내 머리를 한 번 통과</b>합니다.<br>'
   '안 써지면 그게 모르는 겁니다.</p></div>'
   '<div><div class="h">원문은 토글에 접는다</div>'
   '<p>펼쳐 두면 그냥 붙여넣기입니다.<br>접어 두면 <b>문제집</b>이 됩니다.<br>'
   '다시 볼 때 먼저 답해 보고 폅니다.</p></div></div>'
   '<div class="nb1">이 둘만 지키면 카드가 <b>나중에 다시 쓸 수 있는 물건</b>이 됩니다.</div></div>')

# ─────────────────────────── 12 코드
act("기능 12", "코드 블록", "12-1", '「💻 코드로는」 아래에서 <kbd>/코드</kbd>')
act("기능 12", "코드 블록", "12-2", '왼쪽 위에서 언어 <em>Python</em> 선택',
    '오른쪽 위 <kbd>복사</kbd> 버튼이 자동으로 생깁니다')

# ─────────────────────────── 13 이미지
act("기능 13", "이미지", "13-1", '화면 캡처 후 카드에서 <kbd>Ctrl</kbd>+<kbd>V</kbd>',
    '윈도우 캡처는 <kbd>Win</kbd>+<kbd>Shift</kbd>+<kbd>S</kbd>')
act("기능 13", "이미지", "13-2", '이미지 아래를 눌러 <em>캡션</em> 달기',
    '무슨 화면인지 한 줄. 나중에 이게 없으면 못 알아봅니다')

chk("카드 본문 — <b>코드</b> + <b>이미지</b>",
    card_window('<div class="nh2" style="margin-top:4px">🗣 안 보고 설명하면</div>'
                '<div class="nbx nmu">여기에 내 문장으로 씁니다</div>'
                '<div class="nh2">💻 코드로는</div>'
                '<div class="ncode">roll = s.rolling(window=60)\n'
                'z = (s - roll.mean()) / roll.std()</div>'
                '<div class="nimg"><i>EQ-03 온도 그래프</i><div class="dot-red"></div></div>'
                '<div class="nbx nmu" style="font-size:11px">↑ 5일차 EQ-03 — 표시가 안 뜬 구간</div>',
                title="드리프트는 왜 안 잡혔나", ph=False,
                ihd='<span class="chip c-r">설명못함</span>', src="Day2 · 이상감지"))

# ─────────────────────────── 14 토글
act("기능 14", "토글", "14-1", '<kbd>/토글</kbd> → 제목에 <kbd>수업 화면 / 내 필기</kbd>')
act("기능 14", "토글", "14-2", '<em>▸</em> 를 펼치고 그 안에 원문을 넣는다',
    '토글 안에 넣으려면 안쪽 빈 줄에서 입력합니다')
act("기능 14", "토글", "14-3", '다 넣었으면 <em>다시 접는다</em>',
    '접혀 있어야 문제집이 됩니다')

chk("토글 — <b>접힘</b>", card_window(
    '<div class="nh2" style="margin-top:4px">🗣 안 보고 설명하면</div>'
    '<div class="nbx nmu">여기에 내 문장으로 씁니다</div>'
    '<div class="ntog" style="margin-top:14px"><span class="ar">▸</span>'
    '<span style="font-weight:700">수업 화면 / 내 필기</span></div>',
    title="드리프트는 왜 안 잡혔나", ph=False,
    ihd='<span class="chip c-r">설명못함</span>', src="Day2 · 이상감지"),
    sub="접었을 때 — 답이 안 보인다")

chk("토글 — <b>펼침</b>", card_window(
    '<div class="nh2" style="margin-top:4px">🗣 안 보고 설명하면</div>'
    '<div class="nbx nmu">여기에 내 문장으로 씁니다</div>'
    '<div class="ntog" style="margin-top:14px"><span class="ar">▾</span>'
    '<span style="font-weight:700">수업 화면 / 내 필기</span></div>'
    '<div class="togin">'
    '<div class="nbx">이동 윈도 z-score — 최근 N개의 평균·표준편차로 판정</div>'
    '<div class="ncode" style="margin-top:6px">z = (x - mu) / sigma   # 창 안에서만</div>'
    '<div class="nbx nmu" style="font-size:11px;margin-top:6px">내 필기 : 창이 같이 올라가면? ← 여기 못 따라감</div>'
    '</div>',
    title="드리프트는 왜 안 잡혔나", ph=False,
    ihd='<span class="chip c-r">설명못함</span>', src="Day2 · 이상감지"),
    sub="펼쳤을 때 — 원문이 나온다")

# ─────────────────────────── 15 체크박스
act("기능 15", "체크박스", "15-1", '카드 맨 아래에서 <kbd>/할 일</kbd>')
act("기능 15", "체크박스", "15-2", '<kbd>다음에 할 일</kbd> 을 한 줄씩',
    '다음에 열었을 때 뭘 해야 하는지 나에게 남기는 메모')

chk("체크박스 — <b>다음에 할 일</b>", card_window(
    '<div class="nh2" style="margin-top:4px">💻 코드로는</div>'
    '<div class="ncode">roll = s.rolling(window=60)</div>'
    '<div class="ntog" style="margin-top:12px"><span class="ar">▸</span>'
    '<span style="font-weight:700">수업 화면 / 내 필기</span></div>'
    '<div class="nh2">✅ 다음에 할 일</div>'
    '<div class="ntodo"><span class="ck on"></span><span class="strike">윈도 60으로 다시 돌려보기</span></div>'
    '<div class="ntodo"><span class="ck"></span><span>창이 같이 올라가는 경우 확인</span></div>'
    '<div class="ntodo"><span class="ck"></span><span>표준편차 0이면 어떻게 되는지</span></div>',
    title="드리프트는 왜 안 잡혔나", ph=False,
    ihd='<span class="chip c-r">설명못함</span>', src="Day2 · 이상감지"))

# ─────────────────────────── 16 갤러리
act("기능 16", "갤러리 뷰", "16-1", '표 위 <kbd>＋</kbd> → <em>갤러리</em>')
act("기능 16", "갤러리 뷰", "16-2", '<kbd>⋯</kbd> → 레이아웃 → <em>카드 미리보기 : 페이지 콘텐츠</em>',
    '카드 안 첫 이미지가 표지로 올라옵니다')
act("기능 16", "갤러리 뷰", "16-3", '<em>속성</em> 에서 「이해도」만 켜기')

chk("갤러리 뷰",
    window(page(cov_h=110, ic_sz=42, tt_sz=27,
                body=dbhead("갤러리", ("갤러리", "표")) + gallery(CARDS[:3])),
           sd=sidebar(card=True)))

# ─────────────────────────── 17 필터
act("기능 17", "필터", "17-1", '<kbd>＋</kbd> 로 뷰 하나 더 → 이름 <kbd>안 끝난 것</kbd>')
act("기능 17", "필터", "17-2", '<kbd>필터</kbd> → 이해도 → <em>설명가능 아님</em>')

chk("필터 뷰 — <b>안 끝난 것만</b>",
    window(page(cov_h=110, ic_sz=42, tt_sz=27,
                body=dbhead("안 끝난 것", ("갤러리", "표", "안 끝난 것"))
                     + gallery([CARDS[0], CARDS[1], CARDS[3]])),
           sd=sidebar(card=True)))

# ─────────────────────────── 18 공유
act("기능 18", "공유", "18-1", '오른쪽 위 <kbd>공유</kbd>')
act("기능 18", "공유", "18-2", '<em>웹에 게시</em> 켜기 → <kbd>링크 복사</kbd>',
    '검색 엔진 노출은 꺼 두어도 됩니다')

big("기능 18", "이게 뭐가 되나", '이 주소가 <span>포트폴리오</span>입니다',
    '4일치가 쌓이면 링크 하나로 보여줄 수 있습니다.<br>마지막 날 이 주소를 제출하면 수료입니다.')

# ─────────────────────────── 전환
chk("여기까지가 <b>빈 껍데기</b>입니다",
    window(page(cov_h=130, ic_sz=48, tt_sz=30,
                body=dbhead("갤러리", ("갤러리", "표", "안 끝난 것"))
                     + '<div class="gal">'
                       '<div class="gcd" style="border-style:dashed;box-shadow:none">'
                       '<div class="pv" style="color:#C8C7C3">＋</div>'
                       '<div class="bo"><div class="ti nmu">새로 만들기</div></div></div>'
                       '</div>'),
           sd=sidebar(card=True)),
    label="완성", sub="내용은 아직 비어 있습니다")

sl("정리", "80분 동안 만든 것",
   '<div class="mid"><h1 class="t sm">만든 것 — <em>따로 배운 게 아니라</em> 만들다 보니 쓴 것들</h1>'
   '<div class="g2" style="margin-top:22px">'
   + "".join(f'<div class="it"><b>{i:02d}</b>{n}<span>{d}</span></div>' for i, (n, d) in enumerate([
        ("페이지", "그릇"), ("아이콘", "표지"), ("커버", "표지"), ("슬래시 명령", "모든 조작"),
        ("제목·구분선", "골격"), ("데이터베이스", "카드 목록"), ("속성 이해도", "색 태그"),
        ("속성 출처", "어디서 나왔나"), ("행=페이지", "카드"), ("템플릿", "양식"),
        ("제목2·이모지", "구획"), ("코드 블록", "코드"), ("이미지", "화면"),
        ("토글", "접어두기"), ("체크박스", "다음 할 일"), ("갤러리 뷰", "보기 좋게"),
        ("필터", "남은 것만"), ("공유", "주소"),
     ], 1)) +
   '</div></div>')

big("전환", "이제 수업으로", '이제 <span>수업 들어갑니다</span>',
    '필기는 노션에 하세요. 다 못 적어도 됩니다.<br>안 풀린 것만 <b style="color:#1a1a1a">제목으로 남겨</b> 두면 마지막 20분에 채웁니다.')

sl("전환", "언제 카드를 만드나",
   '<div class="mid"><h1 class="t sm">이 세 순간에만 카드를 만듭니다</h1>'
   '<div class="li3" style="margin-top:34px">'
   '<div class="c"><div class="k">순간 1</div><div class="h">못 알아들었을 때</div>'
   '<div class="p">그 말을 그대로 카드 제목으로. 물음표째로 적어 둡니다.</div></div>'
   '<div class="c"><div class="k">순간 2</div><div class="h">코드가 안 돌 때</div>'
   '<div class="p">에러 메시지를 코드 블록에 그대로 붙입니다.</div></div>'
   '<div class="c"><div class="k">순간 3</div><div class="h">화면이 이상할 때</div>'
   '<div class="p">캡처해서 붙입니다. 나중에 이게 제일 도움 됩니다.</div></div></div>'
   '<div class="nb1">수업 중에는 <b>제목만</b> 만들어도 충분합니다. 내용은 마지막 20분에.</div></div>')

# ─────────────────────────── 마무리 20분
S.append(SEP := '<section class="s cv"><div class="ring"></div><div class="bd">'
         '<div class="eb">Day 2 마무리 · 20분</div><h1>오늘 걸로 채웁니다</h1>'
         '<p>수업이 끝났습니다. 아까 만든 껍데기를 지금 채웁니다.</p></div></section>')

act("마무리", "20분 · 1단계", "1", '안 풀린 것 <em>2~3개</em>만 고른다',
    '많이 만들면 하나도 안 채워집니다')
act("마무리", "20분 · 2단계", "2", '<kbd>새로 만들기 ▾</kbd> → <em>개념 카드</em>',
    '아까 만든 템플릿이 그대로 뜹니다')
act("마무리", "20분 · 3단계", "3", '<em>화면을 덮고</em> 🗣 칸을 쓴다',
    '안 써지면 그게 모르는 겁니다. 그대로 두세요')
act("마무리", "20분 · 4단계", "4", '원문·필기는 <em>토글에 접는다</em>')
act("마무리", "20분 · 5단계", "5", '오늘 화면 <em>캡처해서 붙인다</em>')
act("마무리", "20분 · 6단계", "6", '이해도 태그를 <em>솔직하게</em> 찍는다',
    '전부 「설명가능」이면 이 표는 아무 쓸모가 없습니다')

chk("20분 뒤 — <b>오늘 것이 들어간 화면</b>",
    window(page(cov_h=110, ic_sz=42, tt_sz=27,
                body=dbhead("갤러리", ("갤러리", "표", "안 끝난 것")) + gallery(CARDS[:3])),
           sd=sidebar(card=True)),
    label="완성", sub="Day 2 끝")

sl("숙제", "다음 시간까지",
   '<div class="mid"><h1 class="t">숙제는 <em>카드 두 장</em>입니다</h1>'
   '<div class="sb">오늘 제일 헷갈렸던 것 두 개. 30분이면 됩니다.</div>'
   '<div class="li3" style="margin-top:36px">'
   '<div class="c"><div class="k">Day 2</div><div class="h">오늘 · 카드 2장</div>'
   '<div class="p">이상 감지에서 안 풀린 것</div></div>'
   '<div class="c"><div class="k">Day 3</div><div class="h">내일 · 카드 2장</div>'
   '<div class="p">에이전트에서 안 풀린 것</div></div>'
   '<div class="c"><div class="k">Day 4</div><div class="h">마지막 날</div>'
   '<div class="p"><b>링크 제출 = 수료</b></div></div></div>'
   '<div class="nb1">검사하지 않습니다. <b>쌓이는 게 목적</b>입니다.</div></div>')

# ══════════════════════════════════════════ 출력
head = (HERE / "_head.txt").read_text(encoding="utf-8")
extra_css = """
<style>
.acttx{font-size:52px;font-weight:800;color:var(--navy);letter-spacing:-.032em;line-height:1.26;
  text-align:center;max-width:1020px}
.acttx em{font-style:normal;background:linear-gradient(transparent 58%,var(--wash) 58%);padding:0 4px}
.acttx kbd{font-size:44px;padding:2px 16px;border-radius:8px;border-bottom-width:3px}
.actsub{margin-top:28px;font-size:23px;color:var(--gray);text-align:center;line-height:1.55;max-width:860px}
.actsub b{color:#1a1a1a}
.actn{font-size:17px;font-weight:700;color:var(--orange);letter-spacing:.12em;margin-bottom:24px}
.slk{background:#F2F1EE;padding:1px 5px;border-radius:3px}
.cpanel{position:absolute;left:26px;right:0;top:0;bottom:0;background:#fff;border-left:1px solid var(--nb);
  box-shadow:-6px 0 18px rgba(15,15,15,.08)}
.cbar{padding:10px 30px 0;font-size:10px;color:var(--nm)}
.prow{margin-top:6px;font-size:11.5px;color:var(--nm);display:flex;gap:12px}
.prow span:first-child{width:66px}
.togin{margin-left:16px;padding-left:12px;border-left:1px solid var(--nb);margin-top:6px}
.chips{margin-top:44px;display:flex;gap:26px}
.chips>div{text-align:center}
.chips p{margin-top:14px;font-size:18px;color:var(--gray)}
.big3{font-size:24px;padding:10px 26px;border-radius:5px}
.four{margin-top:26px}
.fq{display:flex;align-items:baseline;gap:18px;padding:17px 0;border-bottom:1px solid var(--line2)}
.fq:first-child{border-top:1px solid var(--line2)}
.fe{font-size:26px;width:38px;text-align:center}
.fq b{font-size:27px;font-weight:800;color:var(--navy);letter-spacing:-.02em}
.fq i{font-style:normal;margin-left:auto;font-size:18px;color:var(--gray)}
.two{margin-top:36px;display:flex;gap:26px}
.two>div{flex:1;border-top:3px solid var(--orange);padding-top:18px}
.two .h{font-size:30px;font-weight:800;color:var(--navy);letter-spacing:-.02em}
.two p{font-size:19px;color:var(--gray);margin-top:12px;line-height:1.6}
.two p b{color:#1a1a1a}
</style>
"""
html = head.replace("</head>", extra_css + "</head>") + "\n".join(S) + """
<script>
(function(){var a=document.querySelectorAll('.s'),T=a.length;
a.forEach(function(s,i){var n=i+1;
var r=s.querySelector('.hd .r'); if(r) r.textContent=('0'+n).slice(-2);
var f=s.querySelector('.ft div:last-child'); if(f) f.textContent=n+' / '+T;});
})();
</script>
</body></html>"""
OUT.write_text(html, encoding="utf-8")
print("슬라이드:", len(S))
