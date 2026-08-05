-- =============================================================================
-- W1 팩토리 시뮬레이터 — 005 가상 시계 도입
--
-- 왜 필요한가
--   Day 4 라이브 시연에서 온도 드리프트를 강의 시간 안에 보여줘야 한다.
--   그런데 기울기를 키우면 두 가지가 깨진다.
--     · Day 1 논지 — "드리프트는 사람이 못 알아챌 만큼 미묘하다"
--     · Day 3 학습 — "드리프트는 이동평균이 적응해 미탐된다"
--       (샘플당 상승폭이 커지면 z-score 가 쉽게 잡아 Day 4 시연과 모순된다)
--
--   그래서 기울기가 아니라 **시뮬레이터 시계를 가속**한다.
--   0.5℃/h 라는 성질과 1분 간격 가상 샘플을 그대로 두고, 그 샘플을 실제로는
--   0.5~1초마다 내보낸다. 샘플당 상승폭이 W5 레거시 CSV 와 정확히 같으므로
--   (0.00833℃/샘플) 이상감지 알고리즘 검증 결과가 그대로 유효하다.
--
-- 이 마이그레이션이 하는 일
--   timestamp 는 이제 **공장의 시계(가상 시각)** 다. 가속 중에는 실제 시각보다
--   앞서 나간다. 따라서 보존정책과 운영 질의가 now() 를 쓰면 어긋난다.
--   실제 적재 시각을 담을 ingested_at 을 따로 두고, 운영 질의는 그쪽을 쓴다.
--
--   교안 부록 A 의 6컬럼 계약은 그대로다. sensor_readings_csv 뷰도 그대로다.
-- =============================================================================

alter table sensor_readings add column if not exists ingested_at timestamptz not null default now();
alter table robot_readings  add column if not exists ingested_at timestamptz not null default now();

comment on column sensor_readings."timestamp"  is '공장의 시계(가상 시각). 배속 가동 중에는 실제 시각보다 앞선다.';
comment on column sensor_readings.ingested_at  is '실제 적재 시각. 보존정책·운영 질의 전용.';

-- 보존정책 정리 전용 인덱스를 실제 시각 기준으로 교체
create index if not exists ix_sr_ingested on sensor_readings (ingested_at);
create index if not exists ix_rr_ingested on robot_readings  (ingested_at);
drop index if exists ix_sr_ts;
drop index if exists ix_rr_ts;

-- -----------------------------------------------------------------------------
-- 보존정책 — 실제 적재 시각 기준으로 바꾼다.
-- 가상 시각으로 자르면 가속 중 미래 타임스탬프가 쌓여 아무것도 지워지지 않는다.
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
    delete from sensor_readings where ingested_at < v_cut;
    get diagnostics v_s = row_count;

    delete from robot_readings  where ingested_at < v_cut;
    get diagnostics v_r = row_count;

    return query select v_s, v_r;
end;
$$;

-- -----------------------------------------------------------------------------
-- 적재 현황도 실제 시각 기준
-- -----------------------------------------------------------------------------
-- 컬럼 구성이 바뀌므로 create or replace 로는 안 된다(컬럼명 변경 불가)
drop view if exists ingest_health;
create view ingest_health
    with (security_invoker = true)
as
select tenant_id,
       count(*)                                      as rows_last_60s,
       max(ingested_at)                              as latest_ingest,
       max("timestamp")                              as latest_virtual_ts,
       extract(epoch from (now() - max(ingested_at))) as lag_seconds
from sensor_readings
where ingested_at > now() - interval '60 seconds'
group by tenant_id;

-- -----------------------------------------------------------------------------
-- 새로 만든 뷰·컬럼에 권한을 다시 맞춘다 (004_grants.sql 과 같은 규칙)
-- -----------------------------------------------------------------------------
revoke insert, update, delete, truncate on ingest_health from anon, authenticated;
grant select on ingest_health to anon, authenticated;
