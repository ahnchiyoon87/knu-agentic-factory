"""설정 로딩.

접속 정보는 전부 환경변수(.env)에서 읽는다. 코드에 URL·키를 박지 않는다.
시뮬레이션 파라미터는 config/*.json 에서 읽는다(리허설에서 파일만 고쳐 조정).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

load_dotenv(ROOT / ".env")


def _env(key: str, default: str | None = None, *, required: bool = False) -> str:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(
            f"환경변수 {key} 가 없습니다. .env.example 을 .env 로 복사해 채우세요."
        )
    return val or ""


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    return float(raw) if raw not in (None, "") else default


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    return int(raw) if raw not in (None, "") else default


def _열쇠풀기(값: str) -> str:
    """캡슐(KNU1:...)이면 푼다. 평문(sk-...)은 그대로.

    표식·양념은 제작/검증도구/배포본만들기.py 의 _캡슐() 과 같아야 한다.
    """
    if not 값.startswith("KNU1:"):
        return 값
    import base64
    from itertools import cycle
    양념 = b"K-precision-2026-knu"
    try:
        엮음 = base64.urlsafe_b64decode(값[5:].encode("ascii"))
        return bytes(a ^ b for a, b in zip(엮음, cycle(양념))).decode("utf-8")
    except Exception:                                              # noqa: BLE001
        return 값        # 깨진 캡슐 — 인증 단계에서 잡혀 사람 말로 안내된다


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    def __init__(self) -> None:
        # --- 접속 정보 (환경변수 전용) ---------------------------------------
        self.database_url: str = _env("SUPABASE_DB_URL", required=True)

        # --- 시뮬레이션 주기 --------------------------------------------------
        # 교안 3절: 상태값은 1초 주기로 변동한다. 기본 1.0 을 바꾸지 말 것.
        self.tick_seconds: float = _env_float("SIM_TICK_SECONDS", 1.0)
        # 리서치 확정안 4: 데이터 생성기는 배치 INSERT 로 쓰기 집중을 완화한다.
        self.flush_seconds: float = _env_float("SIM_FLUSH_SECONDS", 2.0)

        # --- 보존정책 --------------------------------------------------------
        # 무료 티어 500MB 에 시간당 180MB 가 쌓인다. .env 가 없어도 한도에 안 부딪히게
        # 기본을 1시간으로 둔다 (docs/부하테스트_결과.md 3절).
        self.retention_hours: float = _env_float("RETENTION_HOURS", 1.0)
        self.retention_sweep_seconds: int = _env_int("RETENTION_SWEEP_SECONDS", 180)

        # --- 대상 테넌트 ------------------------------------------------------
        # individual(S01~S39) | team(T1~T8) | both
        # 이번 특강은 **개인 단위**다. 팀은 쓰지 않는다.
        # .env 가 없거나 이 줄이 빠져도 팀이 딸려 오면 안 되므로 기본을 individual 로 둔다.
        self.tenant_mode: str = _env("TENANT_MODE", "individual")
        # 쉼표 구분 목록으로 강제 지정 가능(개발 중 1~2개만 돌릴 때)
        self.tenant_filter: list[str] = [
            t.strip() for t in _env("TENANT_FILTER", "").split(",") if t.strip()
        ]

        # --- 제어 API 개방 (교안: 3일차 최초 개방) ---------------------------
        self.control_api_enabled: bool = _env_bool("CONTROL_API_ENABLED", False)

        # ── AI 창구 열쇠 ─────────────────────────────────────────────────────
        #    .env 에는 평문(sk-...)이나 **캡슐**(KNU1:... — 배포본만들기가 심는다)이 온다.
        #    캡슐이면 여기(메모리)에서만 풀어 쓴다 — 학생이 .env 를 열어 봐도
        #    문자 덩어리뿐이고, 화면·로그 어디에도 평문을 찍지 않는다.
        #    (난독화이지 암호화가 아니다 — 진짜 방어선은 예산 상한 + 당일 삭제다)
        self.openai_api_keys: list[str] = [
            _열쇠풀기(k.strip())
            for k in _env("OPENAI_API_KEY", "").split(",") if k.strip()
        ]
        self.diagnose_enabled: bool = _env_bool("DIAGNOSE_ENABLED", True)
        self.diagnose_model: str = _env("DIAGNOSE_MODEL", "gpt-5.4-mini")
        # ── 중계문 주소 (선택) ────────────────────────────────────────────────
        #    강사의 GPU 서버에 OpenAI 호환 중계문(LiteLLM 등)을 세워 두면,
        #    진짜 sk- 키는 그 서버에만 있고 학생은 통행증 토큰만 갖는다.
        #    비워 두면 OpenAI 를 직접 부른다 (그때는 OPENAI_API_KEY 가 캡슐/평문).
        self.openai_base_url: str = _env("OPENAI_BASE_URL", "").rstrip("/")
        self.diagnose_per_min: int = _env_int("DIAGNOSE_PER_MIN", 12)
        # HITL: 승인 후에만 실행할 명령. 비우면 즉시 실행.
        # 교안 3일차 10~11장은 승인 관문을 학생 오케스트레이터(폐루프)에 두므로 기본은 비활성.
        self.hitl_commands: set[str] = {
            c.strip()
            for c in _env("HITL_REQUIRED_COMMANDS", "").split(",")
            if c.strip()
        }

        # --- 서버 -------------------------------------------------------------
        self.host: str = _env("HOST", "0.0.0.0")
        self.port: int = _env_int("PORT", 8000)
        self.db_pool_min: int = _env_int("DB_POOL_MIN", 1)
        self.db_pool_max: int = _env_int("DB_POOL_MAX", 8)

    def masked(self) -> dict:
        """기동 로그용. 비밀값은 절대 그대로 찍지 않는다."""

        def mask(v: str) -> str:
            return f"{v[:6]}…{v[-4:]}" if len(v) > 12 else ("설정됨" if v else "없음")

        return {
            "database_url": mask(self.database_url),
            "tick_seconds": self.tick_seconds,
            "flush_seconds": self.flush_seconds,
            "retention_hours": self.retention_hours,
            "tenant_mode": self.tenant_mode,
            "tenant_filter": self.tenant_filter or "(전체)",
            "control_api_enabled": self.control_api_enabled,
            "hitl_commands": sorted(self.hitl_commands) or "(없음)",
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def get_layout() -> dict:
    return json.loads((CONFIG_DIR / "layout.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def get_profile() -> dict:
    return json.loads((CONFIG_DIR / "sim_profile.json").read_text(encoding="utf-8"))
