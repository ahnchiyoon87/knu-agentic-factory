-- =============================================================================
-- W1 팩토리 시뮬레이터 — 003 테넌트 시드
--
-- 개인 39명(S01~S39) + 팀 8개(T1~T8) 를 함께 만든다.
-- Day 1~3 은 개인 네임스페이스, Day 4 는 팀 네임스페이스로 전환한다.
-- 두 종류가 같은 tenant 테이블에 공존하므로 Day 4 에 스키마 변경이 없다.
--
-- 설비·로봇 행은 여기서 만들지 않는다. 배치 좌표의 단일 출처가
-- config/layout.json 이고, 서버 기동 시 그 파일 기준으로 upsert 한다.
-- (좌표가 SQL 과 코드 두 곳에 존재해 어긋나는 것을 막기 위함)
-- =============================================================================

-- 개인 39명 ---------------------------------------------------------------
insert into tenant (tenant_id, tenant_type, display_name, access_key)
select
    'S' || lpad(n::text, 2, '0'),
    'individual',
    '수강생 ' || lpad(n::text, 2, '0'),
    replace(gen_random_uuid()::text, '-', '')
from generate_series(1, 39) as n
on conflict (tenant_id) do nothing;

-- 팀 8개 (Day 4: 4~5명 x 8팀) ----------------------------------------------
insert into tenant (tenant_id, tenant_type, display_name, access_key)
select
    'T' || n::text,
    'team',
    n::text || '팀',
    replace(gen_random_uuid()::text, '-', '')
from generate_series(1, 8) as n
on conflict (tenant_id) do nothing;

-- 팀 편성 기본안 — S01~S39 를 T1~T8 에 5,5,5,5,5,5,5,4 로 배분
-- 실제 편성은 강사 콘솔에서 바꾼다(교안: 컴공 아닌 2명은 서로 다른 팀에 배치).
insert into tenant_member (student_tenant_id, team_tenant_id)
select
    'S' || lpad(n::text, 2, '0'),
    'T' || (least(((n - 1) / 5) + 1, 8))::text
from generate_series(1, 39) as n
on conflict do nothing;
