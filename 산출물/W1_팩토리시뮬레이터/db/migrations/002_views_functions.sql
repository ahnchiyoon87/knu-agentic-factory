-- =============================================================================
-- W1 팩토리 시뮬레이터 — 002 뷰 · 함수 · 보존정책
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. W5 레거시 CSV와 1:1 대응하는 뷰
--    교안 부록 A 컬럼 순서 그대로. 학생이 "과거 + 현재"를 한 테이블로 볼 때 쓴다.
-- -----------------------------------------------------------------------------
create or replace view sensor_readings_csv as
select equipment_id,
       "timestamp",
       temperature,
       vibration,
       rpm,
       run_state
from sensor_readings;

comment on view sensor_readings_csv is
    'W5 레거시 CSV(equipment_id, timestamp, temperature, vibration, rpm, run_state)와 동일한 6컬럼 뷰.';

-- -----------------------------------------------------------------------------
-- 2. 최신 상태 뷰 — 클라이언트 1~2초 폴링용 (리서치 확정안 3)
--
--    학생이 시뮬레이터 API 대신 Supabase를 직접 폴링하는 경로도 열어 둔다.
--    Realtime 구독이 아니라 폴링인 이유: Postgres Changes 가 순서 보장을 위해
--    단일 스레드로 처리되어 초당 64건 변경이 병목(리서치 주제2).
-- -----------------------------------------------------------------------------
create or replace view equipment_latest as
select tenant_id, equipment_id, display_name, pos_x, pos_y,
       temperature, vibration, rpm, run_state, target_rpm, sensor_online, updated_at
from equipment;

create or replace view robot_latest as
select tenant_id, robot_id, display_name, pos_x, pos_y,
       battery, payload_state, status, target_node, updated_at
from robot;

-- -----------------------------------------------------------------------------
-- 3. 보존정책 — sensor_readings / robot_readings 최근 N시간만 유지
--
--    부하 기준: 설비 8행 x 1초 x 39테넌트 ≈ 312 rows/s
--    → 시간당 약 112만 행. 4시간이면 약 440MB 로 무료 티어 DB 500MB 를 넘긴다.
--    러너가 RETENTION_SWEEP_SECONDS 마다 이 함수를 호출한다.
--    (pg_cron 을 쓰지 않는 이유: 무료/Pro 어느 쪽에서도 확장 활성화 없이 동작해야 함)
-- -----------------------------------------------------------------------------
create or replace function prune_readings(p_retain_hours numeric default 2)
returns table (sensor_deleted bigint, robot_deleted bigint)
language plpgsql
as $$
declare
    v_cut timestamptz := now() - make_interval(mins => (p_retain_hours * 60)::int);
    v_s   bigint;
    v_r   bigint;
begin
    delete from sensor_readings where "timestamp" < v_cut;
    get diagnostics v_s = row_count;

    delete from robot_readings  where "timestamp" < v_cut;
    get diagnostics v_r = row_count;

    return query select v_s, v_r;
end;
$$;

comment on function prune_readings is
    '보존정책: 최근 p_retain_hours 시간분만 남기고 이력 삭제. 러너가 주기 호출.';

-- -----------------------------------------------------------------------------
-- 4. 테넌트 완전 초기화 — 강사 콘솔 "리셋"
-- -----------------------------------------------------------------------------
create or replace function reset_tenant(p_tenant_id text)
returns void
language plpgsql
as $$
begin
    delete from sensor_readings   where tenant_id = p_tenant_id;
    delete from robot_readings    where tenant_id = p_tenant_id;
    delete from alarm             where tenant_id = p_tenant_id;
    delete from control_command   where tenant_id = p_tenant_id;
    delete from anomaly_injection where tenant_id = p_tenant_id;
end;
$$;

-- -----------------------------------------------------------------------------
-- 5. 적재 현황 — 부하 테스트·운영 점검용
-- -----------------------------------------------------------------------------
create or replace view ingest_health as
select tenant_id,
       count(*)                                    as rows_last_60s,
       max("timestamp")                            as latest_ts,
       extract(epoch from (now() - max("timestamp"))) as lag_seconds
from sensor_readings
where "timestamp" > now() - interval '60 seconds'
group by tenant_id;
