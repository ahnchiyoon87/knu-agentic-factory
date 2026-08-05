-- =============================================================================
-- W1 팩토리 시뮬레이터 — 006 공용 정비 이력 (폴백용)
--
-- 왜 넣는가
--   교안 Lab 3-3 Step 2 의 지시문이 "해당 설비의 정비 이력을 조회해" 를 요구한다.
--   그 정비 이력의 정본은 **학생이 Day 2 에 만드는 것**이다 —
--   교안 Lab 2-1 스펙 저장소 capability ③ 「정비 작업지시(발행→수행→완료 상태기계)」.
--   Day 2 자산을 Day 3 에서 회수하는 것이 누적 결과물 설계의 핵심이라
--   그 연결을 끊지 않는다.
--
--   여기 있는 것은 **Day 2 를 못 끝낸 팀을 위한 폴백**이다.
--   교안 강사 노트가 이미 같은 종류의 이중화를 요구하고 있다 —
--   Day 3 "공용 MCP 서버로 우회할 경로", Day 4 "동작 보장 최소 경로 카드".
--
--   query_equipment 도구는 조회 대상만 바꿔 끼우고 **도구 이름과 응답 형태는 같다.**
--   학생 코드를 고치지 않고 강사가 우회시킬 수 있다.
--
-- 내용 설계
--   W5 7일치 데이터에 심어 둔 이상 3종의 **원인을 추정할 재료**가 되도록 짰다.
--   이 재료가 없으면 Step 2 의 "원인 추정과 권고 조치"가 성립하지 않는다.
--     · EQ-03 냉각 계통 점검이 발행만 되고 완료되지 않음 → 5일차 온도 드리프트
--     · EQ-05 주축 베어링 유격을 경과 관찰로 넘김        → 3일차 진동 스파이크
--     · EQ-01 온도센서 배선 접촉 불량이 재발 이력 있음   → 6일차 센서 결측
-- =============================================================================

create table if not exists maintenance_log (
    id            bigserial   primary key,
    tenant_id     text        not null references tenant(tenant_id) on delete cascade,
    equipment_id  text        not null,
    work_order_no text        not null,
    issued_at     timestamptz not null,
    status        text        not null check (status in ('ISSUED', 'IN_PROGRESS', 'DONE')),
    action        text        not null,
    technician    text,
    completed_at  timestamptz,
    note          text
);

comment on table maintenance_log is
    '공용 정비 이력 — Lab 3-3 폴백용. 정본은 학생이 Day 2 에 만드는 정비 작업지시 테이블이다.';

create index if not exists ix_maint_tenant_eq
    on maintenance_log (tenant_id, equipment_id, issued_at desc);

-- -----------------------------------------------------------------------------
-- 시드 — 모든 테넌트에 같은 이력을 넣는다
-- W5 데이터 기간은 2026-08-01 ~ 08-07 이다.
-- -----------------------------------------------------------------------------
insert into maintenance_log
    (tenant_id, equipment_id, work_order_no, issued_at, status, action, technician, completed_at, note)
select t.tenant_id, m.equipment_id, m.work_order_no, m.issued_at::timestamptz, m.status,
       m.action, m.technician, m.completed_at::timestamptz, m.note
from tenant t
cross join (values
    -- EQ-03 — 온도 드리프트(5일차 새벽)의 원인 추정 재료
    ('EQ-03', 'WO-2026-0712', '2026-07-12 09:00+09', 'DONE',        '냉각수 필터 교체',        '김정비', '2026-07-12 11:30+09', '필터 오염 심함. 다음 교체 주기 45일 권장'),
    ('EQ-03', 'WO-2026-0801', '2026-08-01 08:30+09', 'IN_PROGRESS', '냉각 계통 정기점검',      '김정비', null,                  '부품 입고 지연으로 보류. 재개 일자 미정'),
    ('EQ-03', 'WO-2026-0620', '2026-06-20 13:00+09', 'DONE',        '주축 윤활유 보충',        '박기사', '2026-06-20 15:00+09', '정상'),

    -- EQ-05 — 진동 스파이크(3일차)의 원인 추정 재료
    ('EQ-05', 'WO-2026-0728', '2026-07-28 13:00+09', 'DONE',        '주축 베어링 이상음 점검', '박기사', '2026-07-28 16:20+09', '베어링 유격 0.04mm 확인. 기준 이내이나 경과 관찰 필요'),
    ('EQ-05', 'WO-2026-0715', '2026-07-15 10:00+09', 'DONE',        '공구 홀더 교체',          '박기사', '2026-07-15 12:00+09', '정상'),

    -- EQ-01 — 센서 결측(6일차)의 원인 추정 재료
    ('EQ-01', 'WO-2026-0630', '2026-06-30 14:00+09', 'DONE',        '온도센서 배선 접촉 불량 보수', '이전기', '2026-06-30 15:10+09', '커넥터 재체결. 동일 증상 3개월 내 2회째'),
    ('EQ-01', 'WO-2026-0725', '2026-07-25 09:00+09', 'DONE',        '정기 청소',              '이전기', '2026-07-25 10:00+09', '정상'),

    -- 나머지 설비 — 평범한 이력
    ('EQ-02', 'WO-2026-0718', '2026-07-18 09:00+09', 'DONE',        '정기 점검',              '김정비', '2026-07-18 11:00+09', '정상'),
    ('EQ-04', 'WO-2026-0722', '2026-07-22 09:00+09', 'DONE',        '절삭유 교체',            '박기사', '2026-07-22 10:30+09', '정상'),
    ('EQ-06', 'WO-2026-0730', '2026-07-30 09:00+09', 'DONE',        '벨트 장력 조정',          '이전기', '2026-07-30 10:00+09', '정상')
) as m(equipment_id, work_order_no, issued_at, status, action, technician, completed_at, note)
where t.active
on conflict do nothing;
