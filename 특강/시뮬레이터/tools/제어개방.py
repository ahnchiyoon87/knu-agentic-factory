"""제어 개방·주입 — 강사가 누르는 것을 한 번으로.

교안에 없는 조작(제어 개방·배속·주입)은 교안이 알려주지 않는다.
그래서 사람 기억에 맡기지 않고 여기 한 곳에 모았다.

    python tools/제어개방.py                 준비 (제어 개방 + 배속 + 개인 키 확인)
    python tools/제어개방.py --inject S07    그 학생 공장에 드리프트 주입
    python tools/제어개방.py --inject-all --stagger 2
                                             전체에 주입  ← 수업 중 이걸 쓴다
    python tools/제어개방.py --status        지금 상태와 경고 확인
    python tools/제어개방.py --end           제어 잠금 · 주입 중단 · 배속 원복

접속 정보는 .env 에서 읽는다. 서버가 떠 있어야 한다.

※ 제어는 **2일차 오후**(슬라이드 29장 「지금 제어 권한이 열렸습니다」)에 연다. 그전까지는 잠겨 있어야 한다 —
   1일차에 열려 있으면 「어제까지는 못 움직였다」는 장면이 성립하지 않는다.
   실습은 처음부터 끝까지 **개인 단위**이고 팀(T1~T8)은 쓰지 않는다.

※ `--inject` 계열은 **온도 드리프트만** 넣는다. 스파이크·결측은 강사 콘솔
   화면(`/console`)에서 종류를 골라 넣는다.
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
import os
import time
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def _env(base_override: str | None = None) -> tuple[str, str]:
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    base = (base_override or os.environ.get("BASE_URL")
            or "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("INSTRUCTOR_TOKEN", "")
    if not token:
        sys.exit("INSTRUCTOR_TOKEN 을 못 찾았습니다 (.env 확인)")
    return base, token


def call(base: str, token: str, method: str, path: str, **kw) -> dict:
    r = httpx.request(method, f"{base}/api/instructor{path}",
                      headers={"X-Instructor-Token": token}, timeout=60, **kw)
    r.raise_for_status()
    return r.json()


def show_status(base: str, token: str) -> None:
    st = call(base, token, "GET", "/status")
    c = st["clock"]
    print(f"  배속 x{c['time_scale']:g} · 실제 tick {c['real_tick_seconds']}초 "
          f"· 공장 시각 {c['virtual_time'][11:19]}")
    print(f"  네임스페이스 {st['tenants']}개 · 진행 중 주입 {len(st['active_injections'])}건")
    for w in st["warnings"]:
        print(f"  ⚠ {w['message']}")
        print(f"     → {w['fix']}")
    if not st["warnings"]:
        print("  경고 없음")


def main() -> int:
    ap = argparse.ArgumentParser(description="제어 개방 · 주입")
    ap.add_argument("--inject", metavar="번호", help="그 공장에 온도 드리프트 주입 (예: S07)")
    ap.add_argument("--inject-all", action="store_true",
                    help="개인 공장(S01~) 전체에 주입 — 수업 중에는 이걸 쓴다")
    ap.add_argument("--equipment", default="EQ-03")
    ap.add_argument("--stagger", type=float, default=2.0, metavar="초",
                    help="--inject-all 에서 한 명씩 벌리는 간격 (기본 2초). "
                         "동시에 넣으면 감지도 동시에 몰려 진단 호출이 한꺼번에 나간다")
    ap.add_argument("--scale", type=float, default=120.0, help="시연 배속 (기본 120)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--end", action="store_true", help="제어 잠금 · 주입 중단 · 배속 원복")
    ap.add_argument("--base", metavar="주소",
                    help="서버 주소. 클라우드로 수업할 때 지정 (예: http://34.64.94.16:8000). "
                         "생략하면 .env 의 BASE_URL, 그것도 없으면 http://127.0.0.1:8000")
    args = ap.parse_args()

    base, token = _env(args.base)
    print(f"대상  {base}\n")

    if args.status:
        print("현재 상태")
        show_status(base, token)
        return 0

    if args.end:
        call(base, token, "DELETE", "/inject")
        call(base, token, "POST", "/control-lock", params={"unlocked": "false", "tenant_id": "*"})
        call(base, token, "POST", "/time-scale", params={"scale": 60})
        print("수업 전 상태로 되돌렸습니다 (제어 잠금 · 주입 중단 · 배속 60)")
        return 0

    def inject_one(tid: str) -> str:
        out = httpx.post(f"{base}/api/instructor/inject",
                         json={"tenant_id": tid, "equipment_id": args.equipment,
                               "kind": "temp_drift"},
                         headers={"X-Instructor-Token": token}, timeout=30).json()
        return out["equipment_id"]

    if args.inject:
        eq = inject_one(args.inject)
        print(f"주입  {args.inject} · {eq}")
        print("  감지까지 배속 x120 기준 약 100초, x60 기준 약 190초 걸립니다.")
        return 0

    if args.inject_all:
        people = [t["tenant_id"] for t in call(base, token, "GET", "/tenants")["tenants"]
                  if t["tenant_type"] == "individual"]
        if not people:
            print("⚠ 개인 네임스페이스가 안 떠 있습니다. TENANT_MODE 를 확인하세요.")
            return 2
        print(f"개인 공장 {len(people)}곳에 주입합니다 — {args.equipment} "
              f"· {args.stagger:g}초 간격")
        fail = []
        for i, tid in enumerate(people, 1):
            try:
                inject_one(tid)
                print(f"  [{i:>2}/{len(people)}] {tid}  주입")
            except Exception as exc:                                    # noqa: BLE001
                fail.append(tid)
                print(f"  [{i:>2}/{len(people)}] {tid}  실패 — {type(exc).__name__}")
            if args.stagger and i < len(people):
                time.sleep(args.stagger)
        print(f"\n완료 {len(people) - len(fail)} / {len(people)}")
        if fail:
            print("  실패:", " ".join(fail))
            print("  → 실패한 것만 다시:  python tools/제어개방.py --inject <번호>")
        print("\n  감지까지 배속 x120 기준 약 100초, x60 기준 약 190초 걸립니다.")
        print("  학생에게 '지금 넣었습니다. 1~3분 조용한 것이 정상입니다' 라고 말해 두십시오.")
        return 2 if fail else 0

    # ---- 기본: 제어 개방 준비 ------------------------------------------------
    print("제어 개방 준비")
    call(base, token, "POST", "/time-scale", params={"scale": args.scale})
    call(base, token, "POST", "/control-lock", params={"unlocked": "true", "tenant_id": "*"})
    print(f"  제어 API 개방(전체) · 배속 x{args.scale:g}")

    people = [t for t in call(base, token, "GET", "/tenants")["tenants"]
              if t["tenant_type"] == "individual"]
    if not people:
        print("\n  ⚠ 개인 네임스페이스가 안 떠 있습니다. TENANT_MODE 를 확인하고 재시작하세요.")
        return 2

    print(f"\n개인 공장 {len(people)}곳 준비됨 — {people[0]['tenant_id']} ~ {people[-1]['tenant_id']}")
    print(f"  base_url : {base}")
    print("  학생은 python 내번호.py 로 각자 번호를 받습니다 — 종이 쪽지는 안 씁니다.")
    print("  배정 현황 확인·회수 : python tools/자리배정.py")
    print("  실습은 처음부터 끝까지 개인 단위입니다. 팀(T1~T8)은 쓰지 않습니다.")

    print("\n확인")
    show_status(base, token)
    print("\n실습 때 — python tools/제어개방.py --inject-all --stagger 2")
    print("         (--stagger 2 를 빼면 진단이 한꺼번에 몰려 느려집니다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
