-- =============================================================================
-- 008 — 강사 전용 공장 S00 을 만든다
--
-- 왜 필요한가
--   강사도 학생과 **똑같이** 실습을 따라가야 한다. 특히 2일차 마지막
--   「AI 가 짠 것과 나란히」는 강사 화면에서 실제로 돌려 보여야 하는 자리다.
--   그런데 지금은 개인 공장이 S01~S39 뿐이라, 강사가 하나를 쓰면
--   **학생 39명 중 한 명이 자리를 못 받는다.**
--
-- 왜 tenant_type 을 새로 두는가 (S40 을 individual 로 늘리지 않고)
--   배정은 `claim.py` 의 `_개인공장()` 이 하는데, 그 함수는
--   `tenant_type = 'individual'` 만 고른다. 타입을 갈라 두면
--   **배정 로직을 건드리지 않고도** 강사 자리가 저절로 빠진다.
--   번호로 예외를 두면(「S40 은 빼고」) 그 규칙이 코드 곳곳에 번진다.
--
-- 러너 쪽 짝 변경
--   `db.list_tenants()` 가 mode='individual' 일 때 instructor 도 같이 싣는다.
--   안 그러면 강사 공장이 **만들어지기만 하고 돌지 않는다**.
--
-- 강사는 학생과 똑같이 `uv run 내번호.py S00` 한 줄로 받는다.
-- `claim` 의 되찾기 경로는 번호를 지정하면 그대로 붙여 주므로 코드 변경이 없다.
-- =============================================================================

-- 001 의 check 는 ('individual','team') 둘만 허용한다. 'instructor' 를 넓힌다.
-- 001 은 이미 적용된 파일이라 고치지 않고 여기서 바꾼다(007 과 같은 방식).
alter table tenant drop constraint if exists tenant_tenant_type_check;
alter table tenant add  constraint tenant_tenant_type_check
    check (tenant_type in ('individual', 'team', 'instructor'));

insert into tenant (tenant_id, tenant_type, display_name, access_key)
values ('S00', 'instructor', '강사',
        replace(gen_random_uuid()::text, '-', ''))
on conflict (tenant_id) do update
    set tenant_type  = 'instructor',
        display_name = '강사',
        active       = true;
