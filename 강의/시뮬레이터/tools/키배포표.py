"""키 배포표 — **예비 수단**. 인쇄용 쪽지를 뽑는다.

평소에는 쓰지 않는다. 학생이 `uv run 내번호.py` 로 각자 번호를 직접 받기 때문이다.
이 스크립트는 **배정이 통째로 막혔을 때만** 쓴다 —
학생 PC 에서 파이썬이 안 돌거나, 네트워크가 막혀 서버에 못 붙는 경우.

    uv run tools/키배포표.py                          # 배포표.html 생성 (LAN 주소 자동 감지)
    uv run tools/키배포표.py --base http://10.0.0.5:8000   # 학생이 접속할 주소를 직접 지정

생성된 배포표.html 을 인쇄해 점선대로 잘라 나눠 준다.
**진짜 키가 들어 있으므로 커밋되지 않는다**(.gitignore).
접속 정보는 .env 에서 읽는다. 서버가 떠 있어야 한다.
"""

from __future__ import annotations

# ── 한글 윈도우(cp949)에서 출력이 깨져 죽는 것을 막는다 ──────────────────
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────────────────

import argparse
import html
import os
import socket
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def _env() -> tuple[str, str]:
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    base = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("INSTRUCTOR_TOKEN", "")
    if not token:
        sys.exit("INSTRUCTOR_TOKEN 을 못 찾았습니다 (.env 확인)")
    return base, token


def lan_ip() -> str:
    """학생 컴퓨터에서 접속 가능한 이 컴퓨터의 주소 — 실제 전송 없이 라우팅만 조회."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


# 쪽지에 적히는 네 줄은 **학생 가이드가 요구하는 것과 이름까지 같아야** 한다.
#   가이드가 "쪽지의 내 번호" 라고 하는데 쪽지에 그 라벨이 없으면,
#   39명이 주소에서 번호를 눈으로 뽑아 옮겨 적는다. 거기가 오타 지점이다.
CARD = """
<div class="card {cls}">
  <div class="head"><span class="id">{tid}</span><span class="name">{name}</span></div>
  <table>
    <tr><th>① 공장 보기 주소<br><small>(2일차 · 크롬에 붙여넣기)</small></th>
        <td class="mono">{view}</td></tr>
    <tr><th>② 내 번호<br><small>(3일차 · tenant)</small></th>
        <td class="mono key">{tid}</td></tr>
    <tr><th>③ 서버 주소<br><small>(3일차 · base_url / shared_api)</small></th>
        <td class="mono">{server}</td></tr>
    <tr><th>④ 접속 키<br><small>(3일차 · access_key)</small></th>
        <td class="mono key">{key}</td></tr>
  </table>
  <div class="note">{note}</div>
</div>"""


def build(rows: list[dict], student_base: str) -> str:
    cards = []
    for r in sorted(rows, key=lambda r: (r["tenant_type"] != "individual", r["tenant_id"])):
        team = r["tenant_type"] == "team"
        cards.append(CARD.format(
            cls="team" if team else "",
            tid=r["tenant_id"],
            name=html.escape(r.get("display_name") or ""),
            view=f"{student_base}/view?tenant={r['tenant_id']}",
            server=student_base,
            key=html.escape(r["access_key"]),
            note="" if team
                 else "키는 본인 것만 사용 — 남에게 보여주지 마세요",
        ))
    n_ind = sum(1 for r in rows if r["tenant_type"] == "individual")
    n_team = len(rows) - n_ind
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>키 배포표 — 학생 {n_ind}명</title>
<style>
body{{font-family:'Malgun Gothic',sans-serif;margin:0;padding:10mm;color:#111}}
.tips{{font-size:12px;color:#555;margin:0 0 8mm}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:6mm}}
.card{{border:1.5px dashed #999;border-radius:8px;padding:5mm;page-break-inside:avoid}}
.card.team{{background:#f3f3f3}}
.head{{display:flex;align-items:baseline;gap:8px;margin-bottom:3mm}}
.id{{font-size:20px;font-weight:800}}
.name{{font-size:12px;color:#666}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;color:#444;font-weight:700;padding:2px 8px 2px 0;white-space:nowrap;vertical-align:top}}
th small{{font-weight:400;color:#888}}
.mono{{font-family:Consolas,monospace;font-size:12px;word-break:break-all}}
.key{{font-weight:700}}
.note{{font-size:10.5px;color:#777;margin-top:2mm}}
@media print{{.tips{{display:none}}}}
</style></head><body>
<p class="tips">인쇄 → 점선대로 잘라 자리에 배치. 학생 쪽지 {n_ind}장.
학생 안내: 2일차는 ① 만 씁니다(크롬 주소창에 붙여넣기 → 내 공장이 뜸).
3일차에 ②③④ 를 실습 코드의 config.json 에 그대로 옮겨 적습니다.</p>
<div class="grid">{''.join(cards)}</div>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description="키 배포표 생성")
    ap.add_argument("--base", help="학생이 접속할 서버 주소 (예: http://10.0.0.5:8000). 생략하면 LAN 주소 자동 감지")
    args = ap.parse_args()

    api_base, token = _env()
    r = httpx.get(f"{api_base}/api/instructor/tenants",
                  headers={"X-Instructor-Token": token}, timeout=30)
    r.raise_for_status()
    rows = [t for t in r.json()["tenants"] if t.get("active", True)]

    # 이번 특강은 개인 단위다. 팀 쪽지는 만들지 않는다.

    rows = [r for r in rows if r["tenant_type"] == "individual"]
    if not rows:
        sys.exit("테넌트가 없습니다 — 서버가 정상 기동됐는지 확인하세요")

    student_base = (args.base or f"http://{lan_ip()}:8000").rstrip("/")
    out = ROOT / "배포표.html"
    out.write_text(build(rows, student_base), encoding="utf-8")
    ind = sum(1 for t in rows if t["tenant_type"] == "individual")
    print(f"생성: {out}")
    print(f"  쪽지 {len(rows)}장 · 학생 접속 주소 {student_base}")
    if "127.0.0.1" in student_base:
        print("  ⚠ 주소가 127.0.0.1 — 학생 컴퓨터에서는 안 열립니다. 강의장에서 --base 로 실제 주소를 지정하세요.")


if __name__ == "__main__":
    main()
