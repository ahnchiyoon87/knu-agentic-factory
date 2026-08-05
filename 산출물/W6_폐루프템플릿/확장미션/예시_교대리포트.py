"""확장 미션 D — 교대 리포트 (최소 형태 예시)

이 파일을 `agents/shift_report.py` 로 복사하고, `agents/__init__.py` 에 등록하면
매 회차 끝에 불립니다.

    from . import shift_report
    EXTRA = [shift_report]

읽기만 합니다. 설비를 움직이지 않으므로 승인 관문이 필요 없습니다.
여기서 시작해 우리 팀이 원하는 모양으로 키우십시오.
"""

from __future__ import annotations

from collections import Counter

ROLE = "교대 리포트"


def run(ctx, record: dict) -> dict:
    """그 회차에 무슨 일이 있었는지 한 장으로 정리한다."""
    cases = record.get("cases", [])

    by_equipment = Counter(c["finding"]["equipment_id"] for c in cases)
    executed, denied, failed = [], [], []
    for c in cases:
        for a in c.get("actions", []):
            {"EXECUTED": executed, "DENIED": denied, "FAILED": failed}.get(
                a.get("status"), []
            ).append(f"{a['command']}({a['target']})")

    report = {
        "회차": record["round"],
        "시각": record["at"],
        "이상_설비": dict(by_equipment),
        "실행된_조치": executed,
        "거부된_조치": denied,
        "실패한_조치": failed,
        "요약": [c["diagnosis"].get("summary", "") for c in cases],
    }

    ctx.log(f"  이상 {len(cases)}건 · 실행 {len(executed)} · "
            f"거부 {len(denied)} · 실패 {len(failed)}")
    for line in report["요약"]:
        if line:
            ctx.log(f"  · {line}")

    return report
