"""공장과 이야기하는 창구 — 여기는 이미 되어 있습니다. 고치지 않아도 됩니다.

읽기 4개, 제어 4개. 제어 4개가 어제까지 잠겨 있던 그 통로입니다.

    읽기   state / readings / maintenance / alarms          키가 필요 없다
    제어   set_equipment_speed / stop_equipment
           dispatch_robot / ack_alarm                       X-Access-Key 가 필요하다

경로에 내 네임스페이스가 들어갑니다. 키가 맞아도 다른 사람 공장은 건드릴 수 없습니다 —
경로가 곧 대상이기 때문입니다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


class ControlLocked(RuntimeError):
    """제어 API 가 아직 잠겨 있습니다(403). 열 차례가 되면 제어열기.py 로 엽니다."""


class FactoryAPI:
    """공장 창구.

    값은 config.json 에서 옵니다. 다만 **환경변수가 있으면 그쪽이 우선**입니다 —
    제어 MCP 서버를 자식 프로세스로 띄울 때 같은 접속 정보를 물려주기 위한 통로입니다.
    """

    def __init__(self, base_url: str | None = None, tenant: str | None = None,
                 access_key: str | None = None, timeout: float = 20.0):
        env = os.environ
        self.base = (base_url or env.get("W6_BASE_URL") or CFG["base_url"]).rstrip("/")
        self.tenant = tenant or env.get("W6_TENANT") or CFG["tenant"]
        self.key = access_key or env.get("W6_ACCESS_KEY") or CFG["access_key"]
        self._설정확인()
        self.client = httpx.Client(timeout=timeout)

    def _설정확인(self) -> None:
        """네트워크를 부르기 전에 config.json 부터 본다.

        안 채운 채로 부르면 30초를 기다렸다가 "닿지 못했습니다" 만 나온다.
        학생은 주소가 틀린 줄 알고 엉뚱한 데를 고친다. 그 전에 여기서 세운다.

        키는 HTTP 헤더에 실리는데 헤더는 ASCII 만 받는다 — 한글 예시가 그대로면
        `UnicodeEncodeError` 로 죽으므로 그것도 여기서 잡는다.
        """
        빈칸 = []
        if not str(self.base).strip():
            빈칸.append('"base_url"    ← 내 공장 주소 (http://localhost:8000)')
        if not str(self.tenant).strip():
            빈칸.append('"tenant"      ← 공장 번호 (S01)')
        if not str(self.key).strip():
            빈칸.append('"access_key"  ← 접속 키 (local-lab-key)')
        if 빈칸:
            raise ValueError(
                "config.json 이 비어 있습니다 —\n    "
                + "\n    ".join(빈칸)
                + "\n\n    이 값들은 실습 저장소에 미리 채워져 옵니다. 지웠거나 고쳤으면\n"
                "    실습 저장소를 다시 내려받으세요. 안 되면 손 드세요."
            )
        try:
            self.key.encode("ascii")
        except (UnicodeEncodeError, AttributeError):
            raise ValueError(
                f'config.json 의 access_key 가 이상합니다 (현재: {self.key!r}).\n'
                "    원래 값은 local-lab-key 입니다 — 실습 저장소를 다시 내려받으세요."
            ) from None

    # ------------------------------------------------------------------ 읽기
    def _get(self, path: str, **params) -> dict:
        url = f"{self.base}/api/v1/{self.tenant}{path}"
        query = {k: v for k, v in params.items() if v is not None}
        # 강의장에서는 연결이 가끔 끊깁니다(39명이 같은 서버를 봅니다). 한 번은 다시 걸어 본다.
        for attempt in (1, 2):
            try:
                r = self.client.get(url, params=query)
                r.raise_for_status()
                return r.json()
            except (httpx.TransportError, httpx.RemoteProtocolError):
                if attempt == 2:
                    raise
        raise RuntimeError("unreachable")

    def state(self) -> dict:
        """설비 6대 + 로봇 2대 + 알람 + 시계 + 제어 통로 상태를 한 번에."""
        return self._get("/state")

    def readings(self, equipment_id: str, minutes: int = 12, limit: int = 5000) -> list[dict]:
        """센서 이력. 오래된 것부터 정렬해서 돌려준다.

        주의 — 시뮬레이터는 최근 1시간만 보관한다.
        배속이 걸려 있으면 실제 1분이 공장 시간 여러 시간에 해당한다.
        """
        out = self._get("/readings", equipment_id=equipment_id, minutes=minutes, limit=limit)
        return sorted(out["readings"], key=lambda r: r["timestamp"])

    def maintenance(self, equipment_id: str | None = None, limit: int = 20) -> list[dict]:
        """정비 이력. 진단의 재료다 — 미완 작업지시와 note 가 원인 추정의 실마리다."""
        return self._get("/maintenance", equipment_id=equipment_id, limit=limit)["maintenance"]

    def alarms(self, state: str = "OPEN") -> list[dict]:
        return self._get("/alarms", state=state)["alarms"]

    # ------------------------------------------------------------------ 제어
    def _post(self, path: str, body: dict) -> dict:
        r = self.client.post(f"{self.base}/api/v1/{self.tenant}/control{path}",
                             json=body, headers={"X-Access-Key": self.key})
        if r.status_code == 403:
            raise ControlLocked(r.json().get("detail", "제어 API 가 잠겨 있습니다."))
        if r.status_code == 401:
            raise PermissionError("X-Access-Key 가 없거나 이 네임스페이스의 키와 다릅니다.")
        r.raise_for_status()
        return r.json()

    def set_equipment_speed(self, equipment_id: str, rpm: float,
                            issued_by: str = "actuator") -> dict:
        return self._post(f"/set_equipment_speed/{equipment_id}",
                          {"rpm": rpm, "issued_by": issued_by})

    def stop_equipment(self, equipment_id: str, reason: str | None = None,
                       issued_by: str = "actuator") -> dict:
        return self._post(f"/stop_equipment/{equipment_id}",
                          {"reason": reason, "issued_by": issued_by})

    def dispatch_robot(self, robot_id: str, target: str,
                       issued_by: str = "actuator") -> dict:
        return self._post(f"/dispatch_robot/{robot_id}",
                          {"target": target, "issued_by": issued_by})

    def ack_alarm(self, alarm_id: int, note: str | None = None,
                  issued_by: str = "actuator") -> dict:
        return self._post(f"/ack_alarm/{alarm_id}", {"note": note, "issued_by": issued_by})

    # ------------------------------------------------------------------ 점검
    def preflight(self) -> dict:
        """폐루프를 돌리기 전에 막힐 곳을 미리 본다. 「동작 보장 최소 경로」 1단계."""
        out: dict = {"base_url": self.base, "tenant": self.tenant}
        s = self.state()
        out["연결"] = "ok"
        out["설비"] = len(s["equipment"])
        out["로봇"] = len(s["robots"])
        out["배속"] = s.get("clock", {}).get("time_scale")
        out["제어_개방"] = s.get("control", {}).get("unlocked")

        # 배속이 1이면 4시간짜리 드리프트가 실제로 4시간 걸린다.
        # 학생은 "감지 이상 없음"만 보고 자기 코드가 틀린 줄 안다.
        # 사람 기억에 맡기지 않고 여기서 세운다.
        out["배속_경고"] = (float(out["배속"] or 1) < 2)
        return out

    def close(self) -> None:
        self.client.close()
