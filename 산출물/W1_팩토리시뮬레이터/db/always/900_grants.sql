-- =============================================================================
-- 권한 — 매번 재적용된다 (db/always/)
--
-- 이 디렉터리의 파일은 마이그레이션 대장에 기록되지 않고, `migrate.py up` 을
-- 돌릴 때마다 **마지막에 항상** 다시 실행된다. 사람이 기억해서 다시 돌리는
-- 방식이 아니다.
--
-- 왜 이렇게 두는가 — 실측으로 확인한 두 가지 때문이다.
--
--   ① 쓰기 권한은 ALTER DEFAULT PRIVILEGES 로 자동화된다. (아래 4절)
--      새 테이블에 anon 은 SELECT/REFERENCES/TRIGGER 만 붙고 INSERT/UPDATE/
--      DELETE 는 붙지 않는 것을 확인했다.
--
--   ② 그러나 뷰의 security_invoker 는 자동화할 수 없다.
--      PostgreSQL 에 "앞으로 만들 뷰는 security_invoker 로" 같은 기본값이 없다.
--      새 뷰는 옵션 없이 생성되어 소유자(postgres) 권한으로 실행되고,
--      단순 뷰는 자동 갱신 가능이라 그 뷰를 통해 남의 행을 고칠 수 있다.
--      제작 중 실제로 PATCH /rest/v1/equipment_latest 가 204 로 통과했다.
--
--   그래서 ②를 막으려면 객체가 늘어날 때마다 다시 적용하는 수밖에 없고,
--   그 실행을 러너에 묶어 사람 기억에서 떼어냈다.
--
-- 이 파일은 하드코딩된 테이블 목록을 쓰지 않는다. public 스키마를 훑어
-- 그때그때 존재하는 객체 전부에 적용하므로, 마이그레이션이 늘어도 자동으로 덮는다.
--
-- 안전 방향 — 기본은 '막기'다.
--   기본 권한은 전부 회수하고, 존재하는 객체에만 SELECT 를 명시적으로 준다.
--   깜빡했을 때 "학생이 못 읽는다"(즉시 눈에 띔)로 실패하지,
--   "anon 이 쓸 수 있다"(조용히 뚫림)로 실패하지 않는다.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. 모든 뷰를 security_invoker 로 (tenant_public 만 예외)
--    tenant_public 은 access_key 컬럼을 감추는 것이 목적이라 소유자 권한이어야 한다.
--    켜면 기반 테이블 tenant 의 SELECT 를 요구해 감추려던 것을 다시 열게 된다.
-- -----------------------------------------------------------------------------
do $$
declare v record;
begin
    for v in
        select c.relname
        from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind = 'v'
          and c.relname <> 'tenant_public'
    loop
        execute format('alter view %I set (security_invoker = true)', v.relname);
    end loop;
end $$;

-- -----------------------------------------------------------------------------
-- 2. access_key 를 감추는 읽기 전용 뷰
-- -----------------------------------------------------------------------------
create or replace view tenant_public as
select tenant_id, tenant_type, display_name, control_unlocked, active
from tenant;

comment on view tenant_public is
    '학생 브라우저가 읽어도 되는 테넌트 정보. access_key 는 빠져 있다.';

-- -----------------------------------------------------------------------------
-- 3. 공개 역할에는 SELECT 만 — 존재하는 모든 테이블·뷰에 적용
--    revoke all 로 먼저 싹 지우고 필요한 것만 준다.
--    (revoke insert,update,... 로 나열하면 PostgreSQL 버전마다 늘어나는
--     새 권한 종류 — 예: PG17 의 MAINTAIN — 를 놓친다)
-- -----------------------------------------------------------------------------
do $$
declare r record;
begin
    for r in
        select c.relname, c.relkind
        from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind in ('r', 'v', 'm', 'p')
    loop
        execute format('revoke all on %I from anon, authenticated', r.relname);

        -- tenant 는 access_key 때문에 통째로 막고, schema_migration 은 학생이 볼 이유가 없다
        if r.relname not in ('tenant', 'schema_migration') then
            execute format('grant select on %I to anon, authenticated', r.relname);
        end if;
    end loop;

    -- 시퀀스도 회수 (INSERT 를 막았으므로 쓸 일이 없다)
    for r in
        select c.relname
        from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind = 'S'
    loop
        execute format('revoke all on sequence %I from anon, authenticated', r.relname);
    end loop;
end $$;

-- -----------------------------------------------------------------------------
-- 4. 앞으로 만들 객체의 기본값 — 전부 막는다
--    이것이 ①의 자동화다. 다음 migrate 실행 때 3절이 SELECT 를 다시 열어 준다.
--    Supabase 는 supabase_admin 역할로 anon 에 전 권한을 기본 부여하지만,
--    우리 마이그레이션은 postgres 역할로 돌므로 아래 설정이 우선한다.
-- -----------------------------------------------------------------------------
alter default privileges in schema public revoke all on tables    from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
alter default privileges in schema public revoke all on functions from anon, authenticated;
