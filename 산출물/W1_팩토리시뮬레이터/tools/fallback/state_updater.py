"""폴백 경로 — 상태 갱신 스크립트.

교안 3절 명시 대안:
    "일정이 빠듯해서 시뮬레이터를 다 못 만들면, Supabase에 상태 테이블을 두고
     상태를 갱신하는 스크립트로 대신합니다. 2D 공장 화면 대신 대시보드가
     갱신되는 걸로 시연하는 식입니다."

이 스크립트는 API 서버(FastAPI)도 2D 뷰(Konva)도 없이,
같은 엔진으로 상태를 만들어 Supabase 에 계속 써 넣기만 한다.

쓰는 상황은 두 가지다.
  1) 강의장 네트워크가 우리 API 서버 포트를 막았을 때
     → 학생은 Supabase PostgREST 를 직접 폴링한다(web/fallback/index.html).
  2) 시뮬레이터 제작이 일정상 미완일 때 (교안이 상정한 상황)

실행:
    python tools/fallback/state_updater.py
    python tools/fallback/state_updater.py --tenants S01,S02 --tick 2
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fallback")


async def main() -> None:
    ap = argparse.ArgumentParser(description="폴백 상태 갱신 스크립트")
    ap.add_argument("--tenants", default=None, help="쉼표 구분. 비우면 TENANT_MODE 전체")
    ap.add_argument("--tick", type=float, default=None, help="갱신 주기(초)")
    ap.add_argument("--flush", type=float, default=None, help="적재 주기(초)")
    args = ap.parse_args()

    # 설정 객체가 만들어지기 전에 환경변수를 덮어써야 반영된다
    if args.tenants:
        os.environ["TENANT_FILTER"] = args.tenants
    if args.tick:
        os.environ["SIM_TICK_SECONDS"] = str(args.tick)
    if args.flush:
        os.environ["SIM_FLUSH_SECONDS"] = str(args.flush)

    from server.app import db
    from server.app.config import get_settings
    from server.app.sim.runner import runner

    s = get_settings()
    log.info("폴백 상태 갱신 시작 — %s", s.masked())
    log.info("API 서버와 2D 뷰 없이 Supabase 만 갱신합니다.")

    await db.init_pool()
    await runner.start()
    log.info("대상 네임스페이스 %d개. 중단하려면 Ctrl+C.", len(runner.tenants))

    try:
        while True:
            await asyncio.sleep(30)
            st = runner.stats
            log.info(
                "tick %s · 적재 %s행 · 마지막 적재 %sms · 지연 %s회 · DB오류 %s회",
                f"{st['ticks']:,}", f"{st['rows_written']:,}",
                st["last_flush_ms"], st["tick_overruns"], st["db_errors"],
            )
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("중단 요청")
    finally:
        await runner.stop()
        await db.close_pool()
        log.info("종료")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
