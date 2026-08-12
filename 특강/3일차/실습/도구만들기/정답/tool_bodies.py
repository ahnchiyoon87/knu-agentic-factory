"""3일차 오전 참고 답안.

`mcp_server.py` 의 두 자리(★)에 들어갈 **본문만** 담았습니다.
템플릿 전체를 복사해 두면 원본과 어긋나므로 본문만 둡니다.

학생 저장소에 같이 들어갑니다 — 시간이 다 된 학생의 `점검.py --열기` 가 이 본문을 읽습니다.
직접 열어 베끼라고 주는 것이 아니라, 막힌 자리 하나만 채우는 마지막 수단입니다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp_server import CFG, _fetch_maintenance, _fetch_readings  # noqa: E402

sys.path.insert(0, str(ROOT.parents[2] / "2일차" / "실습" / "정답"))
from detect_answer import detect  # noqa: E402  (학생은 자기 detect 를 씁니다)


# =============================================================================
# detect_anomaly 본문
# =============================================================================
def detect_anomaly(equipment_id: str, hours: int = 168, k: float | None = None) -> dict:
    rows = _fetch_readings(equipment_id, hours)
    if not rows:
        return {"equipment_id": equipment_id, "checked_hours": hours,
                "sample_count": 0, "anomaly_count": 0, "anomalies": [],
                "note": "해당 구간에 데이터가 없습니다."}

    window = int(CFG["detect"]["window"])
    kk = float(k if k is not None else CFG["detect"]["k"])

    found: list[dict] = []
    for metric in ("temperature", "vibration"):
        values = [None if r.get(metric) is None else float(r[metric]) for r in rows]
        for row, flag in zip(rows, detect(values, window=window, k=kk)):
            if flag:
                found.append({"timestamp": str(row["timestamp"]),
                              "metric": metric,
                              "value": row.get(metric)})

    found.sort(key=lambda x: x["timestamp"], reverse=True)

    # 에이전트가 읽을 결과다. 다 넣으면 길어서 못 읽는다 — 최근 것 위주로 추린다.
    LIMIT = 30
    return {
        "equipment_id": equipment_id,
        "checked_hours": hours,
        "k": kk,
        "window": window,
        "sample_count": len(rows),
        "anomaly_count": len(found),
        "anomalies": found[:LIMIT],
        "truncated": len(found) > LIMIT,
    }


# =============================================================================
# query_equipment 본문
# =============================================================================
def query_equipment(equipment_id: str, hours: int = 24) -> dict:
    rows = _fetch_readings(equipment_id, hours)

    def stat(metric: str) -> dict:
        vals = [float(r[metric]) for r in rows if r.get(metric) is not None]
        if not vals:
            return {"avg": None, "max": None}
        return {"avg": round(sum(vals) / len(vals), 2), "max": round(max(vals), 2)}

    missing = sum(1 for r in rows if r.get("temperature") is None)

    maint = _fetch_maintenance(equipment_id)
    trimmed = [{
        "work_order_no": m.get("work_order_no"),
        "issued_at": str(m.get("issued_at")),
        "status": m.get("status"),
        "action": m.get("action"),
        "note": m.get("note"),          # 원인 추정이 여기서 나온다. 빼지 말 것
    } for m in maint[:10]]

    return {
        "equipment_id": equipment_id,
        "recent": {
            "hours": hours,
            "sample_count": len(rows),
            "temperature": stat("temperature"),
            "vibration": stat("vibration"),
            "missing_count": missing,
        },
        "maintenance": trimmed,
        "open_work_orders": [m for m in trimmed if m["status"] != "DONE"],
    }
