-- =============================================================================
-- W1 팩토리 시뮬레이터 — 001 스키마
-- 경남대 RISE 피지컬AI 사관학교 8월 Agentic AI 특강
--
-- 실행:  python tools/migrate.py up
-- 원칙:  이 파일들만 순서대로 실행하면 빈 Supabase 프로젝트가 그대로 복원된다.
--        (무료 프로젝트 → Pro 전환 시 재실행만으로 이관 가능)
--
-- 근거:
--   * 교안 3절  — CNC 6대(온도·진동·rpm·가동상태) / AMR 2대(위치·배터리·적재상태),
--                 1초 주기 변동, Supabase 스트리밍 적재, 학생별 네임스페이스 분리
--   * 교안 부록A — sensor_readings 6컬럼 고정
--                 (equipment_id, timestamp, temperature, vibration, rpm, run_state)
--   * 리서치     — 격리는 RLS·스키마분리가 아니라 "테넌트 컬럼" 방식
-- =============================================================================

create schema if not exists public;

-- -----------------------------------------------------------------------------
-- 1. 테넌트 (네임스페이스)
--
-- 공장은 학생 PC 에서 하나씩 돌고 DB 도 각자 것이다. 테넌트는 003 이 심는
-- 「내 공장」 하나뿐이지만, 모든 테이블이 이 키로 격리되는 구조는 그대로 둔다 —
-- 실제 멀티테넌트 서비스와 같은 모양을 학생이 그대로 보는 것이 교안의 일부다.
-- -----------------------------------------------------------------------------
create table if not exists tenant (
    tenant_id     text primary key,
    tenant_type   text        not null check (tenant_type in ('individual')),
    display_name  text        not null,
    access_key    text        not null,          -- 제어 API(3일차) 호출용. 읽기 API는 불필요
    control_unlocked boolean  not null default false,  -- 3일차에 개방
    active        boolean     not null default true,   -- 시뮬레이션 대상 여부
    created_at    timestamptz not null default now()
);

comment on table  tenant is '네임스페이스. 모든 상태·이력 테이블이 이 키로 격리된다.';
comment on column tenant.access_key       is '제어 API 인증 키. 읽기 API는 키 없이 tenant_id 만으로 접근(첫 실습 진입장벽 최소화).';
comment on column tenant.control_unlocked is '제어 API 4종은 교안상 3일차에 최초 개방. 기본 false.';

-- -----------------------------------------------------------------------------
-- 2. 설비 현재 상태 — CNC 6대 x 테넌트
-- -----------------------------------------------------------------------------
create table if not exists equipment (
    tenant_id     text        not null references tenant(tenant_id) on delete cascade,
    equipment_id  text        not null,                       -- EQ-01 ~ EQ-06
    display_name  text        not null,
    pos_x         real        not null,                       -- 2D 뷰 배치 좌표
    pos_y         real        not null,
    temperature   real,                                       -- ℃  (결측 주입 시 null)
    vibration     real,                                       -- mm/s RMS
    rpm           real,
    run_state     text        not null default 'RUN',         -- RUN | IDLE | STOP | ALARM
    target_rpm    real        not null default 1800,
    sensor_online boolean     not null default true,          -- 센서 결측 주입 시 false
    updated_at    timestamptz not null default now(),
    primary key (tenant_id, equipment_id)
);

-- -----------------------------------------------------------------------------
-- 3. 로봇 현재 상태 — AMR 2대 x 테넌트
-- -----------------------------------------------------------------------------
create table if not exists robot (
    tenant_id      text        not null references tenant(tenant_id) on delete cascade,
    robot_id       text        not null,                      -- AMR-01, AMR-02
    display_name   text        not null,
    pos_x          real        not null,
    pos_y          real        not null,
    battery        real        not null default 100,          -- %
    payload_state  text        not null default 'EMPTY',      -- EMPTY | LOADED
    status         text        not null default 'IDLE',       -- IDLE | MOVING | CHARGING
    target_node    text,                                      -- 파견 목적지 노드명
    path           jsonb,                                     -- 남은 경유 좌표 [[x,y],...]
    updated_at     timestamptz not null default now(),
    primary key (tenant_id, robot_id)
);

-- -----------------------------------------------------------------------------
-- 4. 센서 이력 (스트리밍 적재) — 교안 부록 A 스키마 고정
--
--   equipment_id, timestamp, temperature, vibration, rpm, run_state
--
-- tenant_id 는 교안이 별도로 요구한 "학생별 네임스페이스 분리"를 위한 격리 컬럼이며
-- 6개 고정 컬럼 뒤에 둔다. W5 레거시 CSV와 컬럼명·순서·의미가 동일하므로
-- 뷰 sensor_readings_csv 로 CSV와 1:1 대응된다.
-- -----------------------------------------------------------------------------
create table if not exists sensor_readings (
    id            bigserial   primary key,
    equipment_id  text        not null,
    "timestamp"   timestamptz not null,
    temperature   real,
    vibration     real,
    rpm           real,
    run_state     text,
    tenant_id     text        not null
);

comment on table sensor_readings is
    '교안 부록 A 고정 스키마(6컬럼) + 격리용 tenant_id. W5 레거시 CSV와 동일 스키마.';

-- 최신행 조회(폴링)와 구간 조회(Day3 이상감지) 양쪽에 쓰는 인덱스
create index if not exists ix_sr_tenant_eq_ts
    on sensor_readings (tenant_id, equipment_id, "timestamp" desc);
-- 보존정책 정리(오래된 행 삭제) 전용
create index if not exists ix_sr_ts
    on sensor_readings ("timestamp");

-- -----------------------------------------------------------------------------
-- 5. 로봇 이력 (스트리밍 적재)
--    교안 "위 값들이 1초 주기로 변동하며 Supabase에 스트리밍 적재" 의 AMR 몫
-- -----------------------------------------------------------------------------
create table if not exists robot_readings (
    id            bigserial   primary key,
    robot_id      text        not null,
    "timestamp"   timestamptz not null,
    pos_x         real,
    pos_y         real,
    battery       real,
    payload_state text,
    status        text,
    tenant_id     text        not null
);

create index if not exists ix_rr_tenant_robot_ts
    on robot_readings (tenant_id, robot_id, "timestamp" desc);
create index if not exists ix_rr_ts
    on robot_readings ("timestamp");

-- -----------------------------------------------------------------------------
-- 6. 알람 — ack_alarm(id) 의 대상
-- -----------------------------------------------------------------------------
create table if not exists alarm (
    id           bigserial   primary key,
    tenant_id    text        not null references tenant(tenant_id) on delete cascade,
    equipment_id text        not null,
    rule_code    text        not null,        -- TEMP_HIGH | VIB_HIGH | SENSOR_LOSS
    severity     text        not null,        -- INFO | WARN | CRITICAL
    message      text        not null,
    value        real,
    threshold    real,
    state        text        not null default 'OPEN',   -- OPEN | ACKED | CLEARED
    raised_at    timestamptz not null default now(),
    acked_at     timestamptz,
    acked_by     text,
    cleared_at   timestamptz
);

create index if not exists ix_alarm_tenant_state
    on alarm (tenant_id, state, raised_at desc);

-- -----------------------------------------------------------------------------
-- 7. 제어 명령 감사 로그 — 제어 API 4종
--    네임스페이스 분리 검증(완료기준 ⑤)의 증거가 되는 테이블
-- -----------------------------------------------------------------------------
create table if not exists control_command (
    id          bigserial   primary key,
    tenant_id   text        not null references tenant(tenant_id) on delete cascade,
    command     text        not null,   -- set_equipment_speed | stop_equipment
                                        -- dispatch_robot      | ack_alarm
    target      text,                   -- EQ-03 / AMR-01 / alarm id
    params      jsonb       not null default '{}'::jsonb,
    status      text        not null default 'EXECUTED',  -- PENDING | APPROVED | EXECUTED | REJECTED | FAILED
    result      jsonb,
    issued_by   text,                   -- 호출 주체(에이전트명 등). 자유 기입
    issued_at   timestamptz not null default now(),
    decided_at  timestamptz,
    decided_by  text
);

create index if not exists ix_cmd_tenant_time
    on control_command (tenant_id, issued_at desc);

-- -----------------------------------------------------------------------------
-- 8. 이상 주입 (강사 콘솔) — 교안 3절 이상 이벤트 3종
-- -----------------------------------------------------------------------------
create table if not exists anomaly_injection (
    id           bigserial   primary key,
    tenant_id    text        not null,     -- '*' = 전체 테넌트 일괄 주입
    equipment_id text        not null,
    kind         text        not null check (kind in ('temp_drift', 'vibration_spike', 'sensor_dropout')),
    params       jsonb       not null default '{}'::jsonb,
    starts_at    timestamptz not null default now(),
    ends_at      timestamptz,
    active       boolean     not null default true,
    created_by   text,
    created_at   timestamptz not null default now()
);

create index if not exists ix_inj_active on anomaly_injection (active, tenant_id);
