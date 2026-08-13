"""마이그레이션 실행기.

    uv run tools/migrate.py up       마이그레이션 + 권한 재적용 + 검증
    uv run tools/migrate.py status   적용 현황
    uv run tools/migrate.py reset    전체 삭제 후 재적용 (개발용, 확인 문구 필요)

빈 Supabase 프로젝트에 이 명령 하나로 복원된다.
무료 → Pro 이관도 새 프로젝트에 up 만 돌리면 된다.

up 은 세 단계다.

  1) db/migrations/*.sql   대장에 없는 것만, 한 번씩
  2) db/always/*.sql       **매번 마지막에 다시** (권한)
  3) 검증                  anon 이 SELECT 외 권한을 가졌으면 실패로 끝낸다

2단계를 둔 이유 — 뷰의 security_invoker 는 ALTER DEFAULT PRIVILEGES 로
자동화되지 않는다. 새 뷰는 소유자 권한으로 실행되고 단순 뷰는 자동 갱신
가능이라, 마이그레이션을 하나 추가할 때마다 남의 행을 고칠 수 있는 구멍이
다시 열린다. 사람이 기억해서 권한을 다시 거는 방식은 반드시 잊어버리므로
러너에 묶었다.
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

import asyncio
import hashlib
import sys
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.app.config import get_settings  # noqa: E402

MIGRATIONS = ROOT / "db" / "migrations"
ALWAYS = ROOT / "db" / "always"

LEDGER = """
create table if not exists schema_migration (
    filename    text primary key,
    checksum    text not null,
    applied_at  timestamptz not null default now()
)
"""


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(get_settings().database_url, statement_cache_size=0)


def _files() -> list[Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def _checksum(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


async def _apply_always(con: asyncpg.Connection) -> None:
    """db/always/*.sql — 대장에 기록하지 않고 매번 다시 실행한다."""
    files = sorted(ALWAYS.glob("*.sql")) if ALWAYS.exists() else []
    if not files:
        print("\n  경고: db/always/ 가 비어 있습니다. 권한 재적용이 빠졌습니다.")
        return
    print("\n[2/3] 권한 재적용 (매번)")
    for path in files:
        print(f"  실행   {path.name}")
        await con.execute(path.read_text(encoding="utf-8"))


async def _verify_grants(con: asyncpg.Connection) -> bool:
    """공개 역할이 SELECT 외의 권한을 갖고 있으면 실패로 본다."""
    print("\n[3/3] 권한 검증")
    bad = await con.fetch(
        """
        select table_name, grantee,
               string_agg(privilege_type, ',' order by privilege_type) as privs
        from information_schema.role_table_grants
        where table_schema = 'public'
          and grantee in ('anon', 'authenticated')
          and privilege_type <> 'SELECT'
        group by 1, 2 order by 1, 2
        """
    )
    leaky_view = await con.fetch(
        """
        select c.relname
        from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind = 'v'
          and c.relname <> 'tenant_public'
          and coalesce(array_to_string(c.reloptions, ','), '') not like '%security_invoker=true%'
        """
    )
    key_open = await con.fetchval(
        """
        select count(*) from information_schema.role_table_grants
        where table_schema='public' and table_name='tenant' and grantee in ('anon','authenticated')
        """
    )

    ok = True
    if bad:
        ok = False
        print("  [실패] 공개 역할에 SELECT 외 권한이 남아 있습니다:")
        for r in bad:
            print(f"          {r['table_name']} / {r['grantee']} → {r['privs']}")
    else:
        print("  [통과] 공개 역할은 SELECT 만 보유")

    if leaky_view:
        ok = False
        print("  [실패] security_invoker 가 없는 뷰 — 소유자 권한으로 실행됩니다:")
        for r in leaky_view:
            print(f"          {r['relname']}")
    else:
        print("  [통과] 모든 뷰가 security_invoker (tenant_public 제외 — 의도된 것)")

    if key_open:
        ok = False
        print("  [실패] tenant 테이블이 공개 역할에 열려 있습니다 (access_key 노출)")
    else:
        print("  [통과] access_key 는 tenant_public 뷰로 가려짐")

    return ok


async def up() -> None:
    con = await _connect()
    try:
        await con.execute(LEDGER)
        applied = {
            r["filename"]: r["checksum"]
            for r in await con.fetch("select filename, checksum from schema_migration")
        }
        print("[1/3] 마이그레이션")
        names = {p.name for p in _files()}
        for path in _files():
            name, csum = path.name, _checksum(path)
            if name in applied:
                mark = "OK " if applied[name] == csum else "변경됨"
                print(f"  건너뜀 {name:34s} [{mark}]")
                if applied[name] != csum:
                    print("        └ 파일이 적용 후 수정됐습니다. 새 번호로 마이그레이션을 추가하세요.")
                continue
            print(f"  적용   {name}")
            await con.execute(path.read_text(encoding="utf-8"))
            await con.execute(
                "insert into schema_migration (filename, checksum) values ($1, $2)",
                name, csum,
            )

        # 파일이 사라진 대장 항목 정리 (예: 권한이 db/always/ 로 옮겨간 경우)
        for stale in sorted(set(applied) - names):
            await con.execute("delete from schema_migration where filename=$1", stale)
            print(f"  정리   {stale:34s} [파일 없음 — 대장에서 제거]")

        await _apply_always(con)
        ok = await _verify_grants(con)
    finally:
        await con.close()

    if not ok:
        print("\n권한 검증 실패. db/always/900_grants.sql 을 확인하세요.")
        sys.exit(1)
    print("\n완료 — 스키마·권한이 모두 맞습니다.")


async def status() -> None:
    con = await _connect()
    try:
        await con.execute(LEDGER)
        applied = {
            r["filename"]: r for r in await con.fetch("select * from schema_migration")
        }
        print(f"{'파일':36s} {'상태':10s} 적용시각")
        print("-" * 74)
        for path in _files():
            r = applied.get(path.name)
            if r is None:
                print(f"{path.name:36s} {'미적용':10s} -")
            else:
                ok = "적용됨" if r["checksum"] == _checksum(path) else "파일변경"
                print(f"{path.name:36s} {ok:10s} {r['applied_at']:%Y-%m-%d %H:%M:%S}")

        rows = await con.fetch(
            "select tenant_type, count(*) c from tenant group by tenant_type order by 1"
        )
        if rows:
            print("\n테넌트: " + ", ".join(f"{r['tenant_type']} {r['c']}개" for r in rows))
    finally:
        await con.close()


async def reset() -> None:
    if input("public 스키마를 전부 삭제합니다. 'RESET' 을 입력하세요: ").strip() != "RESET":
        print("취소")
        return
    con = await _connect()
    try:
        await con.execute("drop schema public cascade; create schema public;")
        print("삭제 완료")
    finally:
        await con.close()
    await up()


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    fn = {"up": up, "status": status, "reset": reset}.get(cmd)
    if fn is None:
        print(__doc__)
        sys.exit(1)
    asyncio.run(fn())


if __name__ == "__main__":
    main()
