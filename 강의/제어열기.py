"""제어 열기 — 3일차 오후, 강사의 신호에 맞춰 이 한 줄이면 됩니다.

    uv run 제어열기.py

어제까지 잠겨 있던 제어 통로 넷(감속·정지·로봇·알람)을 **내 공장에** 엽니다.
화면 위의 「제어」 배지가 몇 초 안에 「개방」으로 바뀝니다.
내 공장만 열리는 것이라 남에게 아무 영향이 없습니다.
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

import json
import sys
import urllib.request


def main() -> int:
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(
                "http://localhost:8000/api/v1/S01/control-unlock", method="POST"),
            timeout=15)
        d = json.loads(r.read().decode("utf-8"))
    except Exception as exc:                                       # noqa: BLE001
        print(f"공장에 닿지 못했습니다 — {type(exc).__name__}", file=sys.stderr)
        print("  공장이 켜져 있나요?  공장 폴더에서 —  docker compose up -d",
              file=sys.stderr)
        print("  그래도 안 되면 손 드세요.", file=sys.stderr)
        return 1

    print()
    print("=" * 58)
    print("  제어가 열렸습니다")
    print("=" * 58)
    print("  " + d.get("안내", "화면을 보세요."))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
