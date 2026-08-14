# -*- coding: utf-8 -*-
"""기준판 v2 레이아웃 8종 렌더러 — 1600×900
   .head(h1+sub) / .body(flex:1) / .foot  세로 flex. 겹침 구조적 차단.
"""
import pathlib

HERE = pathlib.Path(__file__).parent
LOG = []   # 슬라이드 기록 — 원고·설명란을 같은 데이터에서 뽑기 위함


def _head(h1, sub):
    s = f'<div class="sub">{sub}</div>' if sub else ""
    return f'<div class="head"><h1>{h1}</h1>{s}</div>'


def _foot(t):
    return f'<div class="foot">{t}</div>' if t else ""


def cover(eyebrow, h1, sub, tail1, tail2, rings):
    LOG.append(dict(t="cover", n=1, eyebrow=eyebrow, h1=h1, sub=sub, tail=[tail1, tail2]))
    return ('<section class="s cover">'
            f'<div class="head"><div class="eyebrow">{eyebrow}</div><h1>{h1}</h1>'
            f'<div class="bar"></div><div class="sub">{sub}</div></div>'
            f'<div class="tail"><div>{tail1}</div><div>{tail2}</div></div>{rings}</section>')


def sect(h1, sub, art, word, wsub, ps, foot=""):
    LOG.append(dict(t="sect", n=2, h1=h1, sub=sub, art=art, word=word, wsub=wsub, ps=ps, foot=foot))
    p = "".join(f"<p>{x}</p>" for x in ps)
    return (f'<section class="s sect">{_head(h1, sub)}<div class="body">'
            f'<div class="art">{art}</div>'
            f'<div class="txt"><div class="word">{word}</div>'
            f'<div class="wsub">{wsub}</div>{p}</div></div>{_foot(foot)}</section>')


def pic(h1, sub, art, ps, foot=""):
    LOG.append(dict(t="pic", n=3, h1=h1, sub=sub, art=art, ps=ps, foot=foot))
    p = "".join(f"<p>{x}</p>" for x in ps)
    return (f'<section class="s pic">{_head(h1, sub)}<div class="body">'
            f'<div class="art">{art}</div><div class="txt">{p}</div></div>{_foot(foot)}</section>')


def shot(h1, sub, img, ps, foot=""):
    """화면이 주인공 — 실제 노션 화면을 크게 놓고 오른쪽에 짧은 글.
       화면은 손으로 그리지 않는다. 강의자가 캡처한 것을 그대로 쓴다."""
    LOG.append(dict(t="shot", n=9, h1=h1, sub=sub, ps=ps, foot=foot))
    p = "".join(f"<p>{x}</p>" for x in ps)
    return (f'<section class="s shot">{_head(h1, sub)}<div class="body">'
            f'<div class="art">{img}</div><div class="txt">{p}</div>'
            f'</div>{_foot(foot)}</section>')


def shotfull(h1, sub, img, foot=""):
    """화면 하나만 — 완성본처럼 화면 자체가 할 말을 다 하는 장."""
    LOG.append(dict(t="shotfull", n=10, h1=h1, sub=sub, foot=foot))
    return (f'<section class="s shotfull">{_head(h1, sub)}'
            f'<div class="body">{img}</div>{_foot(foot)}</section>')


def step(h1, sub, rows, img, foot="", 넣을것=None, 넣을것제목="여기에 넣을 내용"):
    """왼쪽에 번호 붙은 조작 순서, 오른쪽에 그 조작이 일어나는 실제 화면.
       화면에는 누를 자리를 붉게 표시한다 (shotkit.화면).

    왼쪽 번호와 화면 뱃지는 **1:1 이어야 한다.** 화면에 없는 번호가 있으면
    학생이 「②는 어디?」 하고 찾다가 흐름이 끊긴다. 여기서 막는다.
    """
    import re as _re
    # 뱃지는 <b>, <b class="오른쪽">, <b class="안쪽"> 셋 중 하나로 나온다.
    # 예전 정규식은 class="left|right" 만 찾아 **아무것도 못 잡고 있었다** — 검사가
    # 통과한 게 아니라 검사가 안 돌고 있었던 것이다.
    뱃지 = set(_re.findall(r"<b\b[^>]*>(\d+)</b>", img))
    번호 = {no for no, _, _ in rows}
    # 화면에 **안 찍힌 조작**은 상자를 안 붙인다 (번호만 왼쪽에 둔다) — 그건 정상이다.
    # 반대로 왼쪽에 없는 번호가 화면에 있으면 학생이 「②는 어디?」 하고 찾다 끊긴다.
    남는뱃지 = 뱃지 - 번호
    if 남는뱃지:
        raise SystemExit(
            f"「{h1}」 — 화면에만 있는 번호가 있습니다: {sorted(남는뱃지)}\n"
            f"    왼쪽 {sorted(번호)}   화면 {sorted(뱃지)}\n"
            f"  화면 상자의 번호는 반드시 왼쪽 설명에도 있어야 합니다.")
    LOG.append(dict(t="step", n=11, h1=h1, sub=sub, rows=rows, foot=foot))
    r = "".join(f'<div class="srow"><div class="sno">{no}</div>'
                f'<div class="st"><strong>{st}</strong>'
                + (f"<span>{sp}</span>" if sp else "") + "</div></div>"
                for no, st, sp in rows)
    # 입력할 내용은 조작 설명과 갈라서 **회색 글자로** 보여 준다 — 그대로 옮겨 치면 된다
    입력 = ""
    if 넣을것:
        줄 = "".join(f"<div>{t}</div>" for t in 넣을것)
        # 넣을것제목="" 이면 라벨 없이 회색 줄만 — 한 줄짜리라 라벨이 군더더기인 장이 있다
        머리 = f"<b>{넣을것제목}</b>" if 넣을것제목 else ""
        입력 = f'<div class="typein">{머리}{줄}</div>'
    return (f'<section class="s step">{_head(h1, sub)}<div class="body">'
            f'<div class="txt">{r}{입력}</div><div class="art">{img}</div>'
            f'</div>{_foot(foot)}</section>')


def rail(h1, sub, rows, foot=""):
    LOG.append(dict(t="rail", n=4, h1=h1, sub=sub, rows=rows, foot=foot))
    r = "".join(f'<div class="row"><div class="ico">{ico}</div><div class="no">{no}</div>'
                f'<div class="rt"><strong>{st}</strong><span>{sp}</span></div></div>'
                for ico, no, st, sp in rows)
    return (f'<section class="s rail">{_head(h1, sub)}'
            f'<div class="body">{r}</div>{_foot(foot)}</section>')


def cmp(h1, sub, left, right, foot=""):
    LOG.append(dict(t="cmp", n=5, h1=h1, sub=sub, left=left, right=right, foot=foot))
    def side(tag, cls, art, h3, p):
        return (f'<div class="side"><div class="tag {cls}">{tag}</div>'
                f'<div class="art">{art}</div><h3>{h3}</h3><p>{p}</p></div>')
    return (f'<section class="s cmp">{_head(h1, sub)}<div class="body">'
            + side(*left) + '<div class="rule"></div>' + side(*right)
            + f'</div>{_foot(foot)}</section>')


def tbl(h1, sub, head, rows, on=None, foot="", dense=False):
    # dense — 행이 여섯을 넘는 표만 쓴다. 기본 규격으로는 7행 표가 세로를 넘쳐
    # 제목·각주와 겹친다 (3일차 「폐루프는 일곱 걸음」에서 실제로 깨졌다).
    LOG.append(dict(t="tbl", n=6, h1=h1, sub=sub, head=head, rows=rows, on=on, foot=foot))
    th = "".join(f"<th>{h}</th>" for h in head)
    tb = ""
    for i, r in enumerate(rows):
        cls = ' class="on"' if on is not None and i == on else ""
        cells = "".join((f'<td class="k">{c}</td>' if j == 0 else f"<td>{c}</td>")
                        for j, c in enumerate(r))
        tb += f"<tr{cls}>{cells}</tr>"
    klass = "s dense" if dense else "s"
    return (f'<section class="{klass}">{_head(h1, sub)}<div class="body">'
            f'<table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table>'
            f'</div>{_foot(foot)}</section>')


def words(h1, sub, cols, foot=""):
    LOG.append(dict(t="words", n=7, h1=h1, sub=sub, cols=cols, foot=foot))
    c = "".join(f'<div class="col"><div class="art">{art}</div>'
                f'<div class="w{" hot" if hot else ""}">{w}</div>'
                f'<div class="d">{d}</div></div>' for art, w, d, hot in cols)
    return (f'<section class="s words">{_head(h1, sub)}'
            f'<div class="body">{c}</div>{_foot(foot)}</section>')


def graph(h1, sub, ps, art, foot=""):
    LOG.append(dict(t="graph", n=8, h1=h1, sub=sub, ps=ps, art=art, foot=foot))
    p = "".join(f"<p>{x}</p>" for x in ps)
    return (f'<section class="s graph">{_head(h1, sub)}<div class="body">'
            f'<div class="txt">{p}</div><div class="art">{art}</div>'
            f'</div>{_foot(foot)}</section>')


def write(slides, out, title):
    css = (HERE / "_기준판.css").read_text(encoding="utf-8")
    html = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<title>{title}</title><style>{css}\nbody{{background:#3a3a36}}\n'
            f'.s{{margin:18px auto}}\n@media print{{body{{background:#fff}}.s{{margin:0}}}}'
            f'</style></head><body>\n' + "\n".join(slides) + "\n</body></html>")
    pathlib.Path(out).write_text(html, encoding="utf-8")
    return len(slides)
