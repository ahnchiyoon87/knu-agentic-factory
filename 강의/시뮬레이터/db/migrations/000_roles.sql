-- =============================================================================
-- 000 — 공개 역할을 먼저 만든다
--
-- Supabase 에는 anon·authenticated 가 원래 있었지만, 학생 PC 의 로컬 Postgres
-- (docker compose 의 db 서비스)에는 없다. 뒤의 마이그레이션과 권한 스크립트가
-- 이 두 역할에 grant 를 걸므로 **무엇보다 먼저** 있어야 한다.
-- =============================================================================

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then
        create role anon nologin;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then
        create role authenticated nologin;
    end if;
end $$;
