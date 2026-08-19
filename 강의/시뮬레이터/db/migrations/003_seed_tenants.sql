-- =============================================================================
-- 003 — 내 공장 하나를 만든다
--
-- 공장은 학생 PC 에서 하나씩 돈다 (docker compose). DB 도 각자 것이라
-- 자리 배정·번호 관리가 없다 — 전원이 같은 S01 이고, 부딪힐 상대가 없다.
--
-- access_key 는 비밀이 아니다. 제어 API 호출 형식을 실제 서비스처럼
-- 유지하기 위한 고정값이며, 3일차 config.json 에 미리 채워져 나간다.
--
-- 설비·로봇 행은 여기서 만들지 않는다. 배치 좌표의 단일 출처가
-- config/layout.json 이고, 서버 기동 시 그 파일 기준으로 upsert 한다.
-- =============================================================================

insert into tenant (tenant_id, tenant_type, display_name, access_key)
values ('S01', 'individual', '내 공장', 'local-lab-key')
on conflict (tenant_id) do update
    set display_name = '내 공장',
        access_key   = 'local-lab-key',
        active       = true;
