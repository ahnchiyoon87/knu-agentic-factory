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
    # 제목·각주와 겹친다 (2일차 「폐루프는 일곱 걸음」에서 실제로 깨졌다).
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
