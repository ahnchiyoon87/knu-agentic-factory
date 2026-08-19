"""1초 주기 러너.

교안 3절: 상태값이 1초 주기로 변동하며 Supabase 에 스트리밍 적재된다.

- tick 은 매 1초 (SIM_TICK_SECONDS)
- 적재는 배치 (SIM_FLUSH_SECONDS 마다 모아서 copy) — 리서치 확정안 4
- 보존정책 정리는 RETENTION_SWEEP_SECONDS 마다

가상 시계
    배속 N 을 주면 가상 샘플 간격 60초(7일치 CSV 격자)를 고정한 채
    실제로는 60/N 초마다 한 샘플을 내보낸다. x60 이면 실제 tick 이 정확히 1초라
    교안의 "1초 주기 변동"이 그대로 유지되고, 3~4분 만에 가상 4시간이 흐른다.
    기울기를 건드리지 않으므로 샘플당 상승폭이 7일치 CSV 와 같다.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from .. import db
from ..config import get_layout, get_profile, get_settings
from .engine import SimEngine

log = logging.getLogger("sim.runner")
UTC = timezone.utc


class Runner:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.engine = SimEngine(get_layout(), get_profile())
        self.tenants: dict[str, dict] = {}
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

        # ---- 가상 시계 -------------------------------------------------------
        # 배속 1 이면 가상 시각 = 실제 시각, 1초 간격 샘플(기본 운전).
        # 배속 N(>1) 이면 가상 샘플 간격을 60초(= 7일치 CSV 격자)로 고정하고
        # 그 샘플을 실제로는 60/N 초마다 내보낸다.
        #   x60  → 실제 1.00초마다 1분치   (교안의 "1초 주기 변동"이 그대로 유지된다)
        #   x80  → 실제 0.75초마다 1분치
        #   x120 → 실제 0.50초마다 1분치
        # 기울기를 건드리지 않으므로 샘플당 상승폭이 7일치 CSV 와 같다(0.5℃/h → 0.00833℃/샘플).
        clock = get_profile().get("clock", {})
        self.virtual_sample_seconds: float = float(clock.get("virtual_sample_seconds", 60.0))
        # 기본 배속. 환경변수가 있으면 그쪽이 우선한다(리허설·부하시험용).
        # 기본이 60 인 이유는 sim_profile.json 의 clock._why_default_60 에 적어 뒀다.
        # 요약 — 강사가 켜야 하는 스위치를 없애기 위해서다. x60 은 실제 tick 이 1.00초라
        # 교안 3절의 '1초 주기 변동'이 그대로 유지되고 적재량도 x1 과 같다.
        self.time_scale: float = float(
            os.environ.get("SIM_TIME_SCALE") or clock.get("default_time_scale", 60.0)
        )
        self.virtual_now: datetime = datetime.now(UTC)

        # 관측 지표 (부하 테스트·운영 점검용)
        self.stats = {
            "ticks": 0,
            "flushes": 0,
            "rows_written": 0,
            "last_flush_ms": 0.0,
            "last_tick_ms": 0.0,
            "tick_overruns": 0,
            "db_errors": 0,
            "last_error": None,
            "started_at": None,
            "time_scale": 1.0,
            "virtual_time": None,
        }

        self._sensor_buf: list[tuple] = []
        self._robot_buf: list[tuple] = []

    # ------------------------------------------------------------ 기동/정지
    async def start(self) -> None:
        rows = await db.list_tenants(self.settings.tenant_mode, self.settings.tenant_filter)
        if not rows:
            raise RuntimeError(
                "시뮬레이션 대상 테넌트가 없습니다. db/migrations/003_seed_tenants.sql 을 실행했는지 확인하세요."
            )
        self.tenants = {r["tenant_id"]: r for r in rows}
        await db.bootstrap_entities(list(self.tenants), get_layout())
        for tid in self.tenants:
            self.engine.ensure_tenant(tid)

        # 재기동 시 공장은 정상 상태로 초기화되므로, 이전 프로세스가 남긴
        # OPEN 알람은 실재하지 않는 이상을 가리킨다. 먼저 정리한다.
        stale = await db.clear_stale_alarms(list(self.tenants))
        if stale:
            log.info("재기동 전 알람 %d건 정리(CLEARED)", stale)

        await self._load_injections()

        self.virtual_now = datetime.now(UTC)
        self.engine.set_virtual_step(self.virtual_step_seconds)

        self.stats["started_at"] = datetime.now(UTC).isoformat()
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="sim-runner")
        log.info("러너 기동 — 테넌트 %d개, 배속 x%g, 실제 tick %.2fs, flush %.1fs",
                 len(self.tenants), self.time_scale, self.real_tick_seconds,
                 self.settings.flush_seconds)

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    # ------------------------------------------------------------- 가상 시계
    @property
    def real_tick_seconds(self) -> float:
        """실제 tick 주기. 배속 1 이면 교안 사양 그대로 1초."""
        if self.time_scale <= 1.0:
            return self.settings.tick_seconds
        return self.virtual_sample_seconds / self.time_scale

    @property
    def virtual_step_seconds(self) -> float:
        """한 tick 이 밀어내는 가상 시간(초) = 가상 샘플 간격."""
        if self.time_scale <= 1.0:
            return self.settings.tick_seconds
        return self.virtual_sample_seconds

    def set_time_scale(self, scale: float) -> dict:
        """운전 중 배속 변경. 가상 시각은 끊기지 않고 이후 속도만 바뀐다."""
        scale = max(1.0, min(240.0, float(scale)))
        self.time_scale = scale
        self.engine.set_virtual_step(self.virtual_step_seconds)
        log.info(
            "배속 x%g — 실제 %.2f초마다 가상 %.0f초 진행 (샘플당 드리프트 %.5f℃ @0.5℃/h)",
            scale, self.real_tick_seconds, self.virtual_step_seconds,
            0.5 * self.virtual_step_seconds / 3600,
        )
        return self.clock_info()

    def clock_info(self) -> dict:
        return {
            "time_scale": self.time_scale,
            "virtual_time": self.virtual_now.isoformat(),
            "real_time": datetime.now(UTC).isoformat(),
            "real_tick_seconds": round(self.real_tick_seconds, 3),
            "virtual_step_seconds": self.virtual_step_seconds,
        }

    # ---------------------------------------------------------------- 메인 루프
    async def _loop(self) -> None:
        s = self.settings
        loop = asyncio.get_running_loop()
        next_at = loop.time()
        last_flush = loop.time()
        last_sweep = loop.time()
        prev_real = loop.time()

        while not self._stop.is_set():
            tick = self.real_tick_seconds          # 배속을 바꾸면 다음 주기부터 반영
            next_at += tick
            t0 = loop.time()

            dt_real = max(0.001, t0 - prev_real)
            prev_real = t0

            # 공장의 시계를 밀어낸다. 배속 1 이면 실제 경과와 같다.
            dt_virtual = self.virtual_step_seconds if self.time_scale > 1.0 else dt_real
            self.virtual_now += timedelta(seconds=dt_virtual)
            now = self.virtual_now

            try:
                self.engine.tick(now, dt_virtual, dt_real)
                self._collect(now)
                self.stats["ticks"] += 1
                self.stats["time_scale"] = self.time_scale
                self.stats["virtual_time"] = now.isoformat()
            except Exception as exc:                     # noqa: BLE001
                self.stats["last_error"] = f"tick: {exc}"
                log.exception("tick 실패")

            self.stats["last_tick_ms"] = round((loop.time() - t0) * 1000, 2)

            if loop.time() - last_flush >= s.flush_seconds:
                last_flush = loop.time()
                await self._flush(now)

            if loop.time() - last_sweep >= s.retention_sweep_seconds:
                last_sweep = loop.time()
                await self._sweep()

            delay = next_at - loop.time()
            if delay < 0:
                # 한 주기 안에 일을 못 끝냈다 — 리허설에서 이 값이 늘면
                # 리서치 판단기준대로 tick/flush 주기를 늦춘다.
                self.stats["tick_overruns"] += 1
                next_at = loop.time()
                delay = 0
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

    # ------------------------------------------------------------- 버퍼 적재
    def _collect(self, now: datetime) -> None:
        for f in self.engine.factories.values():
            s_rows, r_rows = f.readings(now)
            self._sensor_buf.extend(s_rows)
            self._robot_buf.extend(r_rows)

    async def _flush(self, now: datetime) -> None:
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        sensor, robot = self._sensor_buf, self._robot_buf
        self._sensor_buf, self._robot_buf = [], []

        # 현재상태 테이블의 updated_at 은 운영용이므로 실제 시각을 쓴다.
        # (가상 시각을 넣으면 "몇 초 전 갱신" 표시가 미래로 튄다)
        real_now = datetime.now(UTC)
        eq_rows, rb_rows = [], []
        for f in self.engine.factories.values():
            for e in f.equipment.values():
                eq_rows.append((f.tenant_id, e.equipment_id, e.temperature, e.vibration,
                                e.observed_rpm, e.run_state, e.target_rpm,
                                e.sensor_online, real_now))
            for r in f.robots.values():
                rb_rows.append((f.tenant_id, r.robot_id, r.pos_x, r.pos_y, r.battery,
                                r.payload_state, r.status, r.target_node, real_now))

        try:
            await db.insert_readings(sensor, robot)
            await db.upsert_current_state(eq_rows, rb_rows)
            await self._persist_alarms()
            await self._expire_injections(now)
            self.stats["flushes"] += 1
            self.stats["rows_written"] += len(sensor) + len(robot)
        except Exception as exc:                          # noqa: BLE001
            self.stats["db_errors"] += 1
            self.stats["last_error"] = f"flush: {exc}"
            log.exception("적재 실패 — 이번 배치는 버린다(시뮬레이션은 계속)")

        self.stats["last_flush_ms"] = round((loop.time() - t0) * 1000, 2)

    async def _persist_alarms(self) -> None:
        new_rows, new_objs = [], []
        cleared_ids = []
        for f in self.engine.factories.values():
            while f.new_alarms:
                a = f.new_alarms.pop(0)
                new_objs.append(a)
                new_rows.append((f.tenant_id, a.key[0], a.key[1], a.severity,
                                 a.message, a.value, a.threshold, a.raised_at))
            while f.cleared_alarms:
                c = f.cleared_alarms.pop(0)
                if c.db_id is not None:
                    cleared_ids.append(c.db_id)

        if new_rows:
            ids = await db.insert_alarms(new_rows)
            for obj, db_id in zip(new_objs, ids):
                obj.db_id = db_id
        if cleared_ids:
            await db.clear_alarms(cleared_ids)

    async def _expire_injections(self, now: datetime) -> None:
        """끝난 주입에 실제로 「끝났다」 표시를 한다.

        `is_live()` 가 종료시각을 보므로 물리는 이미 멈춘다. 문제는 표시다.
        이걸 안 하면 DB 의 「진행 중인 주입」에 이미 끝난 것이 계속 남고,
        무엇보다 「제어는 열렸는데 주입이 없습니다」 경고가 영원히 안 뜬다.
        학생이 감지할 대상이 사라진 바로 그 순간에 경고가 침묵하는 셈이다.
        """
        done = self.engine.expire_injections(now)
        if not done:
            return
        try:
            async with db.pool().acquire() as con:
                await con.execute(
                    "update anomaly_injection set active=false where id = any($1::bigint[])",
                    done,
                )
            log.info("주입 %d건 종료 — %s", len(done), ", ".join(str(i) for i in done))
        except Exception as exc:                          # noqa: BLE001
            self.stats["db_errors"] += 1
            self.stats["last_error"] = f"expire: {exc}"
            log.exception("주입 종료 표시 실패")

    async def _sweep(self) -> None:
        try:
            res = await db.prune(self.settings.retention_hours)
            if res.get("sensor_deleted") or res.get("robot_deleted"):
                log.info("보존정책 정리 — 센서 %s행 / 로봇 %s행 삭제 (최근 %.1f시간 유지)",
                         res.get("sensor_deleted"), res.get("robot_deleted"),
                         self.settings.retention_hours)
        except Exception as exc:                          # noqa: BLE001
            self.stats["db_errors"] += 1
            self.stats["last_error"] = f"prune: {exc}"
            log.exception("보존정책 정리 실패")

    # ------------------------------------------------------------- 이상 주입
    async def _load_injections(self) -> None:
        """재기동 시 이전 주입을 정리한다.

        복원하지 않고 끄는 이유 — 엔진 상태가 메모리라 재기동하면 공장이 정상
        상태(62℃)로 초기화된다. 그런데 주입만 복원하면 경과 시간이 이미 4시간이라
        온도가 +2℃ 만큼 툭 튀어 오른다. 게다가 주입 시각은 가상 시계 기준인데
        재기동하면 가상 시계도 실제 시각으로 되돌아가므로 기준이 어긋난다.
        강사가 다시 주입하는 편이 예측 가능하다.
        """
        async with db.pool().acquire() as con:
            n = await con.fetchval(
                "with x as (update anomaly_injection set active=false "
                "           where active returning 1) select count(*) from x"
            )
        if n:
            log.info("재기동 전 이상 주입 %d건 정리(비활성화). 필요하면 다시 주입하세요.", n)


runner = Runner()
