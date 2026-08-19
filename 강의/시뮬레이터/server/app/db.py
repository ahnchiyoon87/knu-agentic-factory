"""Postgres 접근 계층 — DB 는 compose 안의 db 컨테이너다.

적재는 asyncpg 의 copy_records_to_table 로 한다 — 배치 INSERT 가
행 단위 INSERT 보다 훨씬 유리하다.
"""

from __future__ import annotations

import asyncio

import asyncpg

from .config import get_settings

_pool: asyncpg.Pool | None = None


class DB못붙음(RuntimeError):
    """DB 에 못 닿았다. 사람이 읽을 수 있는 말로 세우기 위한 것."""


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        s = get_settings()
        try:
            _pool = await asyncio.wait_for(
                asyncpg.create_pool(
                    dsn=s.database_url,
                    min_size=s.db_pool_min,
                    max_size=s.db_pool_max,
                    command_timeout=30,
                    # Supabase 트랜잭션 풀러(6543)를 쓰면 준비된 구문 캐시를 꺼야 한다
                    statement_cache_size=0,
                ),
                # 강의장에서 30초 넘게 기다리게 하지 않는다. 막힌 건 빨리 알아야 한다.
                timeout=25,
            )
        except Exception as exc:                                   # noqa: BLE001
            # 여기서 역추적을 그대로 뱉으면 강사가 무엇을 해야 할지 알 수 없다.
            raise DB못붙음(_안내(exc, s.database_url)) from None
    return _pool


def _안내(exc: Exception, dsn: str) -> str:
    호스트 = "(주소 확인 불가)"
    try:
        호스트 = dsn.split("@", 1)[1].split("/", 1)[0]
    except Exception:                                              # noqa: BLE001
        pass
    까닭 = type(exc).__name__
    시간초과 = isinstance(exc, (asyncio.TimeoutError, OSError))
    줄 = [
        "",
        "=" * 66,
        "  데이터베이스에 닿지 못해 서버를 켤 수 없습니다.",
        "=" * 66,
        f"  주소   {호스트}",
        f"  까닭   {까닭}",
        "",
    ]
    if 시간초과:
        줄 += [
            "  DB 컨테이너가 아직 안 떴거나 죽었습니다.",
            "",
            "  바로 해 볼 것 — 공장 폴더에서",
            "    docker compose up -d",
            "  그래도 안 되면 데이터를 지우고 처음부터 —",
            "    docker compose down -v && docker compose up -d",
            "",
        ]
    else:
        줄 += [
            "  docker compose down -v 로 초기화한 뒤 다시 켜 보세요.",
            "",
        ]
    줄 += ["  그래도 안 되면 손 드세요.", "=" * 66, ""]
    return "\n".join(줄)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB 풀이 아직 초기화되지 않았습니다.")
    return _pool


# ---------------------------------------------------------------- 적재
SENSOR_COLS = (
    "equipment_id", "timestamp", "temperature", "vibration", "rpm", "run_state", "tenant_id",
)
ROBOT_COLS = (
    "robot_id", "timestamp", "pos_x", "pos_y", "battery", "payload_state", "status", "tenant_id",
)


async def insert_readings(sensor_rows: list[tuple], robot_rows: list[tuple]) -> None:
    if not sensor_rows and not robot_rows:
        return
    async with pool().acquire() as con:
        async with con.transaction():
            if sensor_rows:
                await con.copy_records_to_table(
                    "sensor_readings", records=sensor_rows, columns=list(SENSOR_COLS)
                )
            if robot_rows:
                await con.copy_records_to_table(
                    "robot_readings", records=robot_rows, columns=list(ROBOT_COLS)
                )


async def upsert_current_state(equipment_rows: list[tuple], robot_rows: list[tuple]) -> None:
    """equipment / robot 테이블의 '현재 상태'를 갱신한다.

    학생이 시뮬레이터 API 대신 Supabase 를 직접 1~2초 폴링하는 경로
    (equipment_latest / robot_latest 뷰)가 이 갱신에 의존한다.
    """
    async with pool().acquire() as con:
        async with con.transaction():
            if equipment_rows:
                await con.executemany(
                    """
                    update equipment
                       set temperature = $3, vibration = $4, rpm = $5,
                           run_state = $6, target_rpm = $7, sensor_online = $8,
                           updated_at = $9
                     where tenant_id = $1 and equipment_id = $2
                    """,
                    equipment_rows,
                )
            if robot_rows:
                await con.executemany(
                    """
                    update robot
                       set pos_x = $3, pos_y = $4, battery = $5, payload_state = $6,
                           status = $7, target_node = $8, updated_at = $9
                     where tenant_id = $1 and robot_id = $2
                    """,
                    robot_rows,
                )


# ---------------------------------------------------------------- 부트스트랩
async def bootstrap_entities(tenant_ids: list[str], layout: dict) -> None:
    """테넌트별 설비 6대 · 로봇 2대 행을 layout.json 기준으로 생성(멱등)."""
    if not tenant_ids:
        return
    eq_rows = [
        (t, e["equipment_id"], e["display_name"], float(e["pos_x"]), float(e["pos_y"]),
         float(e["nominal_rpm"]))
        for t in tenant_ids
        for e in layout["equipment"]
    ]
    nodes = layout["nodes"]
    rb_rows = [
        (t, r["robot_id"], r["display_name"],
         float(nodes[r["home_node"]]["x"]), float(nodes[r["home_node"]]["y"]))
        for t in tenant_ids
        for r in layout["robots"]
    ]
    async with pool().acquire() as con:
        async with con.transaction():
            await con.executemany(
                """
                insert into equipment (tenant_id, equipment_id, display_name,
                                       pos_x, pos_y, target_rpm)
                values ($1, $2, $3, $4, $5, $6)
                on conflict (tenant_id, equipment_id) do update
                   set display_name = excluded.display_name,
                       pos_x = excluded.pos_x,
                       pos_y = excluded.pos_y
                """,
                eq_rows,
            )
            await con.executemany(
                """
                insert into robot (tenant_id, robot_id, display_name, pos_x, pos_y)
                values ($1, $2, $3, $4, $5)
                on conflict (tenant_id, robot_id) do update
                   set display_name = excluded.display_name
                """,
                rb_rows,
            )


async def list_tenants(mode: str, tenant_filter: list[str]) -> list[dict]:
    where, args = ["active"], []
    if tenant_filter:
        args.append(tenant_filter)
        where.append(f"tenant_id = any(${len(args)})")
    elif mode:
        args.append(mode)
        where.append(f"tenant_type = ${len(args)}")
    sql = (
        "select tenant_id, tenant_type, display_name, access_key, control_unlocked "
        f"from tenant where {' and '.join(where)} order by tenant_id"
    )
    async with pool().acquire() as con:
        return [dict(r) for r in await con.fetch(sql, *args)]


# ---------------------------------------------------------------- 알람
async def insert_alarms(rows: list[tuple]) -> list[int]:
    """(tenant_id, equipment_id, rule_code, severity, message, value, threshold, raised_at)"""
    if not rows:
        return []
    async with pool().acquire() as con:
        recs = await con.fetch(
            """
            insert into alarm (tenant_id, equipment_id, rule_code, severity,
                               message, value, threshold, raised_at)
            select * from unnest($1::text[], $2::text[], $3::text[], $4::text[],
                                 $5::text[], $6::real[], $7::real[], $8::timestamptz[])
            returning id
            """,
            *[list(col) for col in zip(*rows)],
        )
        return [r["id"] for r in recs]


async def clear_stale_alarms(tenant_ids: list[str]) -> int:
    """서버 재기동 시 남아 있는 OPEN/ACKED 알람을 정리한다.

    엔진 상태는 프로세스 메모리에 있어 재기동하면 공장이 정상 상태로 초기화된다.
    그런데 DB 의 알람은 남으므로, 정리하지 않으면 존재하지 않는 이상에 대한
    알람이 학생 대시보드에 영원히 떠 있게 된다(실제로 재기동 후 재현됨).
    """
    if not tenant_ids:
        return 0
    async with pool().acquire() as con:
        res = await con.execute(
            "update alarm set state='CLEARED', cleared_at=now() "
            "where tenant_id = any($1::text[]) and state in ('OPEN','ACKED')",
            tenant_ids,
        )
    return int(res.rsplit(" ", 1)[-1]) if res else 0


async def clear_alarms(ids: list[int]) -> None:
    if not ids:
        return
    async with pool().acquire() as con:
        await con.execute(
            "update alarm set state='CLEARED', cleared_at=now() "
            "where id = any($1::bigint[]) and state <> 'CLEARED'",
            ids,
        )


# ---------------------------------------------------------------- 보존정책
async def prune(retain_hours: float) -> dict:
    async with pool().acquire() as con:
        row = await con.fetchrow("select * from prune_readings($1::numeric)", retain_hours)
        return dict(row) if row else {}
