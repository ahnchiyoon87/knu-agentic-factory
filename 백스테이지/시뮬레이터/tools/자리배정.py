"""자리 배정 — 누가 어느 공장을 받았는지 보고, 필요하면 풀어 준다.

    python tools/자리배정.py                  지금 누가 뭘 받았나 (수시로 확인)
    python tools/자리배정.py --풀기 S07        S07 을 다시 안 쓰는 것으로
    python tools/자리배정.py --전부풀기         전부 초기화 (수업 전에 한 번)
    python tools/자리배정.py --base http://34.64.94.16:8000

언제 쓰나
  · 수업 시작 전 — `--전부풀기` 로 어제 배정을 지운다
  · 학생이 "번호를 못 받았다" — 그냥 이 표를 보면 남은 번호가 보인다
  · 노트북을 바꿔 와서 새 번호를 받아 버린 학생 — 옛 번호를 `--풀기`
  · 학생이 자기 번호를 잊었다 — 이 표에서 「표시」로 찾거나, 학생이
    `python 내번호.py` 를 다시 치면 화면에 다시 뜬다
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
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def _설정(이름: str, 기본: str = "") -> str:
    env = ROOT / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{이름}="):
                return line.split("=", 1)[1].strip()
    return os.environ.get(이름, 기본)


def main() -> int:
    ap = argparse.ArgumentParser(description="자리 배정 보기 · 풀기")
    ap.add_argument("--base", default=None, help="서버 주소 (생략하면 로컬)")
    ap.add_argument("--풀기", metavar="번호", help="그 번호를 다시 안 쓰는 것으로")
    ap.add_argument("--전부풀기", action="store_true", help="배정을 전부 초기화")
    ap.add_argument("--예", action="store_true",
                    help="--전부풀기 확인을 건너뛴다 (자동화용)")
    args = ap.parse_args()

    base = (args.base or _설정("BASE_URL", "http://127.0.0.1:8000")).rstrip("/")
    token = _설정("INSTRUCTOR_TOKEN")
    print(f"대상  {base}\n")

    if args.풀기 or args.전부풀기:
        대상 = "*" if args.전부풀기 else args.풀기.strip().upper()
        if args.전부풀기:
            # 2일차 아침에 이걸 누르면 39명이 어제 받은 공장을 한꺼번에 잃는다.
            # 다시 받을 수는 있지만 **다른 번호**가 나가서, 어제 보던 공장이 아니게 된다.
            # 문서 네 곳이 「1일차 아침에만」이라고 적어 뒀지만 도구에는 잠금이 없었다.
            try:
                현황 = httpx.get(f"{base}/api/v1/claim/status", timeout=20).json()
            except Exception:                                      # noqa: BLE001
                현황 = {"배정됨": 0}
            나간것 = 현황.get("배정됨", 0)
            if 나간것 and not args.예:
                print(f"⚠ 이미 {나간것}명이 번호를 받아 갔습니다.")
                print("  전부 지우면 그 학생들은 **다른 번호**를 다시 받게 됩니다 —")
                print("  어제 보던 공장이 아니게 됩니다. 2일차 아침이면 하지 마세요.")
                print("  1일차 아침이 맞다면 다시:  python tools/자리배정.py --전부풀기 --예")
                return 2
            print("배정을 전부 지웁니다. 학생은 다시 받으면 됩니다.")
        try:
            r = httpx.post(f"{base}/api/instructor/unclaim",
                           params={"tenant_id": 대상},
                           headers={"X-Instructor-Token": token}, timeout=20)
        except Exception as exc:                                   # noqa: BLE001
            print(f"서버에 닿지 못했습니다 — {type(exc).__name__}", file=sys.stderr)
            return 1
        if r.status_code != 200:
            print(f"풀지 못했습니다 — {r.json().get('detail', r.text)}", file=sys.stderr)
            return 1
        푼것 = r.json()["푼_번호"]
        print(f"  풀었습니다 — {len(푼것)}개 ({', '.join(푼것[:8])}"
              f"{' …' if len(푼것) > 8 else ''})\n")

    try:
        h = httpx.get(f"{base}/api/v1/claim/status", timeout=20).json()
    except Exception as exc:                                       # noqa: BLE001
        print(f"서버에 닿지 못했습니다 — {type(exc).__name__}", file=sys.stderr)
        return 1

    print(f"공장 {h['전체']}개 · 배정됨 {h['배정됨']} · 남음 {h['남음']}")
    if h["배정"]:
        print("-" * 62)
        for a in h["배정"]:
            시각 = (a.get("받은_시각") or "")[11:16]
            표시 = a.get("표시") or ""
            print(f"  {a['tenant_id']}   {시각}   {표시}")
    if h["남음"]:
        print("-" * 62)
        남 = h["안_나간_번호"]
        print(f"  아직 안 나간 번호 {len(남)}개 — {', '.join(남[:12])}"
              f"{' …' if len(남) > 12 else ''}")
    if h["남음"] == 0 and h["배정됨"] == h["전체"]:
        print("\n  전원이 받았습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
