"""자리 배정 — 학생이 자기 공장을 자동으로 하나 갖는다.

왜 만들었는가
  39명에게 각자 다른 번호와 접속 키를 줘야 한다.
  종이 쪽지로 주면 잃어버리는 학생이 나오고, 이틀째에 다시 뽑아 줘야 한다.

어떻게 하는가 — **학생 PC 가 자기 번호표를 만든다**
  1. 학생이 `uv run 내번호.py` 를 치면, 그 PC 가 **무작위 번호표**를 하나 만들어
     실습 폴더의 `.내번호` 파일에 적는다. 아무 의미 없는 긴 문자열이다.
  2. 그 번호표를 서버에 보내면, 서버가 **아직 안 나간 공장 하나**를 붙여 주고
     장부에 적는다.
  3. 다음부터는 파일에 있는 번호표를 다시 보내므로 **항상 같은 공장**이 나온다.

  MAC 주소나 컴퓨터 이름을 쓰지 않는 이유 —
  MAC 은 못 읽으면 매번 다른 임의값이 나와 번호가 계속 새로 나간다.
  실습실 복제 PC 는 컴퓨터 이름이 같을 수 있다.
  학생 PC 가 자기가 만든 무작위 번호표는 그런 실패가 없다.

무엇을 못 하는가 (정직하게)
  · 저장소를 지우고 다시 받으면 번호표가 사라져 새 공장을 받는다
    → 강사가 `배정풀기` 로 옛 번호를 풀어 준다. 이틀에 한두 명 있을까 말까다.
  · 한 PC 를 둘이 쓰면 같은 공장을 본다 → 강사가 수동 배정한다.

배정 장부는 파일에 남는다. 서버를 다시 켜도 어제 배정이 그대로다.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import ROOT
from ..sim.runner import runner

router = APIRouter(prefix="/api/v1", tags=["claim"])
UTC = timezone.utc

# 배정 장부 — 서버를 다시 켜도 살아 있어야 하므로 파일에 남긴다.
장부경로 = ROOT / "배정장부.json"
_lock = threading.Lock()
번호표꼴 = re.compile(r"^[A-Za-z0-9_-]{16,80}$")


def _장부읽기() -> dict:
    if not 장부경로.is_file():
        return {}
    try:
        d = json.loads(장부경로.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:                                              # noqa: BLE001
        # 장부가 깨졌다고 수업을 멈출 수는 없다. 원본은 남기고 새로 시작한다.
        장부경로.replace(장부경로.with_name("배정장부.깨짐.json"))
        return {}


def _장부쓰기(d: dict) -> None:
    """임시 파일에 먼저 쓰고 통째로 바꿔친다 — 쓰다가 죽어도 장부가 안 깨진다."""
    임시 = 장부경로.with_suffix(".tmp")
    임시.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    임시.replace(장부경로)


def _개인공장() -> list[str]:
    """개인 네임스페이스만, 번호 순으로."""
    return sorted(t["tenant_id"] for t in runner.tenants.values()
                  if t["tenant_type"] == "individual")


class ClaimReq(BaseModel):
    번호표: str = Field(..., description="학생 PC 가 만든 무작위 번호표")
    표시: str | None = Field(None, max_length=60, description="사람이 알아볼 이름(선택)")
    되찾을_번호: str | None = Field(
        None, max_length=10,
        description="자리를 옮겼을 때. 학생이 기억하는 번호(예: S07)를 주면 그 공장을 다시 붙인다")


@router.post("/claim", summary="내 공장 받기 — 자동 배정, 또는 번호로 되찾기")
async def claim(req: ClaimReq) -> dict:
    표 = req.번호표.strip()
    if not 번호표꼴.match(표):
        raise HTTPException(400, "번호표 형식이 맞지 않습니다. 내번호.py 를 다시 실행하세요.")

    # 자물쇠 안에서만 장부를 만진다 — 39명이 같은 순간에 눌러도 겹치지 않는다
    with _lock:
        장부 = _장부읽기()

        # ── 자리를 옮겼다: 학생이 기억하는 번호로 되찾는다 ──────────────────
        #    학생이 기억할 것은 「S07」 다섯 글자뿐이다. 그것만 있으면
        #    다른 노트북에서도, 저장소를 다시 받아도 자기 공장으로 돌아온다.
        되찾을 = (req.되찾을_번호 or "").strip().upper()
        if 되찾을:
            if 되찾을 not in runner.tenants:
                raise HTTPException(404, f"{되찾을} 이라는 번호는 없습니다. "
                                         "대문자 S 와 두 자리 숫자입니다 (예: S07).")
            # 그 번호를 쓰던 옛 번호표를 끊고, 지금 PC 에 붙인다
            옛표 = [k for k, v in 장부.items() if v.get("tenant_id") == 되찾을]
            for k in 옛표:
                장부.pop(k, None)
            장부[표] = {"tenant_id": 되찾을, "at": datetime.now(UTC).isoformat(),
                        "label": (req.표시 or "")[:60], "되찾음": True}
            _장부쓰기(장부)
            return _응답(runner.tenants[되찾을], 새로받음=False,
                        받은시각=장부[표]["at"], 되찾음=True)

        # ── 이미 받은 적이 있으면 그대로 돌려준다 (몇 번을 불러도 같다) ────────
        기존 = 장부.get(표)
        if 기존 and 기존.get("tenant_id") in runner.tenants:
            t = runner.tenants[기존["tenant_id"]]
            return _응답(t, 새로받음=False, 받은시각=기존.get("at"))

        # ── 처음이다: 아직 안 나간 번호 중 가장 작은 것을 준다 ────────────────
        쓰는중 = {v.get("tenant_id") for v in 장부.values()}
        남은것 = [tid for tid in _개인공장() if tid not in 쓰는중]
        if not 남은것:
            raise HTTPException(
                status_code=409,
                detail=("남은 공장이 없습니다. 자리를 옮기신 거라면 "
                        "`uv run 내번호.py S07` 처럼 원래 번호를 붙여 다시 실행하세요. "
                        "처음이라면 손 드세요 — 강사가 풀어 줍니다."),
            )

        tid = 남은것[0]
        장부[표] = {"tenant_id": tid, "at": datetime.now(UTC).isoformat(),
                    "label": (req.표시 or "")[:60]}
        _장부쓰기(장부)
        return _응답(runner.tenants[tid], 새로받음=True, 받은시각=장부[표]["at"])


def _응답(t: dict, 새로받음: bool, 받은시각: str | None,
         되찾음: bool = False) -> dict:
    return {
        "tenant_id": t["tenant_id"],
        "display_name": t.get("display_name") or "",
        "access_key": t["access_key"],
        "새로_받음": 새로받음,
        "되찾음": 되찾음,
        "받은_시각": 받은시각,
    }


@router.get("/claim/status", summary="배정 현황 — 강사가 본다")
async def 현황() -> dict:
    """경로를 영문으로 둔다 — 한글 경로는 curl·스크립트에서 인코딩 없이는 404 가 난다."""
    with _lock:
        장부 = _장부읽기()
    쓰는중 = {v["tenant_id"]: k for k, v in 장부.items() if v.get("tenant_id")}
    전체 = _개인공장()
    학생 = {tid: 표 for tid, 표 in 쓰는중.items() if tid in 전체}
    남은것 = [t for t in 전체 if t not in 학생]
    return {
        "전체": len(전체),
        "배정됨": len(학생),
        "남음": len(남은것),
        "안_나간_번호": 남은것,
        "배정": [
            {"tenant_id": tid, "번호표": 표[:10] + "…",
             "표시": 장부[표].get("label") or "", "받은_시각": 장부[표].get("at")}
            for tid, 표 in sorted(학생.items())
        ],
        # 강사 공장(S00)처럼 학생 자리가 아닌 것. 세지는 않고 보여만 준다.
        "학생자리_아닌_것": sorted(t for t in 쓰는중 if t not in 전체),
    }
