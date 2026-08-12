"""권한 점검 — publishable(anon) 키로 쓰기가 막혔는지 실제로 호출해 본다.

db/always/900_grants.sql 적용 뒤 반드시 한 번 돌린다 (migrate.py up 이 자동으로 건다).
Supabase 는 public 스키마 새 테이블에 anon 쓰기 권한까지 기본 부여하므로,
마이그레이션을 하나 추가할 때마다 다시 뚫릴 수 있다.

    python tools/check_grants.py
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
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.app.config import get_settings  # noqa: E402

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'통과' if ok else '실패'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    s = get_settings()
    if not s.supabase_url or not s.supabase_publishable_key:
        print("SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY 가 .env 에 없습니다.")
        print("이 점검은 학생 브라우저가 쓰는 공개 키 경로를 보는 것이라 두 값이 필요합니다.")
        return 2

    base = s.supabase_url.rstrip("/") + "/rest/v1/"
    hdr = {
        "apikey": s.supabase_publishable_key,
        "Authorization": "Bearer " + s.supabase_publishable_key,
        "Content-Type": "application/json",
    }

    def rest(path: str, method: str = "GET", body: dict | None = None) -> tuple[int, str]:
        req = urllib.request.Request(
            base + path, method=method,
            data=json.dumps(body).encode() if body else None, headers=hdr,
        )
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read().decode()[:100]
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                return e.code, json.loads(raw).get("message", raw)[:80]
            except Exception:                              # noqa: BLE001
                return e.code, raw[:80]
        except Exception as exc:                           # noqa: BLE001
            return -1, f"{type(exc).__name__}: {exc}"

    print("=" * 70)
    print(f"권한 점검 — {s.supabase_url}")
    print("  publishable(anon) 키로 호출합니다. 학생 브라우저와 같은 조건입니다.")
    print("=" * 70)

    print("\n1. 읽기는 되어야 한다 (폴백 대시보드·직접 폴링 경로)")
    for label, path in [
        ("tenant_public", "tenant_public?select=tenant_id&limit=1"),
        ("equipment_latest", "equipment_latest?select=equipment_id,temperature&limit=1"),
        ("robot_latest", "robot_latest?select=robot_id,battery&limit=1"),
        ("sensor_readings", "sensor_readings?select=equipment_id&limit=1"),
        ("alarm", "alarm?select=id&limit=1"),
    ]:
        code, msg = rest(path)
        check(f"{label} 읽기", code == 200, f"HTTP {code}" + (f" · {msg}" if code != 200 else ""))

    print("\n2. access_key 는 감춰져야 한다")
    code, msg = rest("tenant?select=access_key&limit=1")
    check("tenant 테이블 직접 조회 차단", code in (401, 403), f"HTTP {code} · {msg}")

    print("\n3. 쓰기는 전부 막혀야 한다")
    writes = [
        ("alarm INSERT", "alarm", "POST",
         {"tenant_id": "__grantcheck__", "equipment_id": "EQ-01",
          "rule_code": "GRANT_CHECK", "severity": "INFO", "message": "권한 점검"}),
        ("equipment UPDATE", "equipment?equipment_id=eq.EQ-01", "PATCH",
         {"run_state": "GRANTCHECK"}),
        ("equipment_latest 뷰 UPDATE", "equipment_latest?equipment_id=eq.EQ-01", "PATCH",
         {"run_state": "GRANTCHECK"}),
        ("tenant_public 뷰 UPDATE", "tenant_public?tenant_id=eq.S01", "PATCH",
         {"display_name": "GRANTCHECK"}),
        ("sensor_readings DELETE", "sensor_readings?equipment_id=eq.__none__", "DELETE", None),
        ("control_command INSERT", "control_command", "POST",
         {"tenant_id": "__grantcheck__", "command": "stop_equipment"}),
        ("anomaly_injection INSERT", "anomaly_injection", "POST",
         {"tenant_id": "__grantcheck__", "equipment_id": "EQ-01", "kind": "temp_drift"}),
    ]
    for label, path, method, body in writes:
        code, msg = rest(path, method, body)
        check(f"{label} 차단", code in (401, 403), f"HTTP {code} · {msg}")

    print("\n" + "=" * 70)
    if failures:
        print(f"실패 {len(failures)}건: " + ", ".join(failures))
        print("→ python tools/migrate.py up 을 다시 돌리세요 "
              "(db/always/900_grants.sql 이 매번 재적용됩니다).")
        print("   마이그레이션을 새로 추가했다면 그 뒤에 004 를 다시 적용해야 할 수 있습니다.")
        return 1
    print("전 항목 통과 — 공개 키로는 읽기만 됩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
