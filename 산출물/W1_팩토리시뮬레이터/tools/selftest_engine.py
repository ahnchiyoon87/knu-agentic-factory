"""엔진 자체 검증 — DB 없이 시뮬레이션 로직만 확인한다.

    python tools/selftest_engine.py

Supabase 없이도 돌기 때문에 강의장에서 네트워크가 막혔을 때
"시뮬레이터 자체는 정상"임을 즉시 가릴 수 있다.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.app.sim.engine import Injection, SimEngine, default_end  # noqa: E402

UTC = timezone.utc
LAYOUT = json.loads((ROOT / "config" / "layout.json").read_text(encoding="utf-8"))
PROFILE = json.loads((ROOT / "config" / "sim_profile.json").read_text(encoding="utf-8"))

PASS, FAIL = "  [통과]", "  [실패]"
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{PASS if ok else FAIL} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def run(engine: SimEngine, start: datetime, seconds: int, dt: float = 1.0) -> datetime:
    now = start
    for _ in range(seconds):
        now += timedelta(seconds=dt)
        engine.tick(now, dt)
    return now


def new_engine() -> tuple[SimEngine, datetime]:
    e = SimEngine(LAYOUT, PROFILE)
    e.ensure_tenant("S01")
    e.ensure_tenant("S02")
    return e, datetime(2026, 8, 20, 3, 0, 0, tzinfo=UTC)


# =============================================================================
print("\n1. 정상 운전 — 상태값이 1초 주기로 변동하는가 (교안 3절)")
# =============================================================================
eng, t0 = new_engine()
f = eng.factories["S01"]
now = run(eng, t0, 120)

eq3 = f.equipment["EQ-03"]
check("CNC 6대 존재", len(f.equipment) == 6, ", ".join(f.equipment))
check("AMR 2대 존재", len(f.robots) == 2, ", ".join(f.robots))
check("EQ-03 정상 온도 62℃ 근처", 61.0 <= eq3.temperature <= 63.0,
      f"{eq3.temperature:.2f}℃ (슬라이드 서사 기준값 62℃)")
check("EQ-03 진동 정상 범위", 1.5 <= eq3.vibration <= 2.5, f"{eq3.vibration:.2f} mm/s")
check("가동상태 RUN", eq3.run_state == "RUN", eq3.run_state)

temps = []
for _ in range(20):
    now = run(eng, now, 1)
    temps.append(eq3.temperature)
check("매 tick 값이 변동(노이즈 존재)", len(set(temps)) > 15,
      f"20틱 중 서로 다른 값 {len(set(temps))}개")
spread = max(temps) - min(temps)
check("노이즈가 과하지 않음", 0.2 < spread < 3.0, f"20틱 진폭 {spread:.2f}℃")

hot = {e.equipment_id: round(e.temperature, 1) for e in f.equipment.values()}
check("설비마다 정상 온도가 다름(고정 임계값 하향 시 오탐이 생기는 근거)",
      len(set(hot.values())) >= 4, str(hot))

# =============================================================================
print("\n2. 온도 드리프트 주입 — 0.5℃/h · 4시간 · 62→64℃ (확정 수치)")
# =============================================================================
eng, t0 = new_engine()
f = eng.factories["S01"]
now = run(eng, t0, 60)
base = f.equipment["EQ-03"].temperature

d = PROFILE["anomaly_defaults"]["temp_drift"]
params = {"slope_c_per_hour": d["slope_c_per_hour"], "duration_hours": d["duration_hours"]}
eng.injections[1] = Injection(
    id=1, tenant_id="S01", equipment_id="EQ-03", kind="temp_drift",
    params=params, starts_at=now, ends_at=default_end("temp_drift", params, now, PROFILE),
)

marks = {}
for hours in (1, 2, 3, 4):
    now = run(eng, now, 3600, dt=1.0)
    marks[hours] = f.equipment["EQ-03"].temperature

check("1시간 후 +0.5℃", abs((marks[1] - base) - 0.5) < 0.8, f"{base:.2f} → {marks[1]:.2f}℃")
check("4시간 후 +2.0℃ (62→64)", abs((marks[4] - base) - 2.0) < 0.9,
      f"{base:.2f} → {marks[4]:.2f}℃")
check("고정 임계값 80℃ 를 넘지 않음 — Day 3 미탐 학습의 전제",
      marks[4] < PROFILE["alarm"]["temp_high_c"],
      f"최고 {marks[4]:.2f}℃ < 80℃")
check("드리프트 중 TEMP_HIGH 알람 미발생",
      not any(k[1] == "TEMP_HIGH" for k, a in f.alarms.items() if a.state == "OPEN"),
      "고정 임계값으로는 안 잡힌다")
check("다른 테넌트 S02 는 영향 없음",
      abs(eng.factories["S02"].equipment["EQ-03"].temperature - base) < 2.0,
      f"S02 EQ-03 {eng.factories['S02'].equipment['EQ-03'].temperature:.2f}℃")

# =============================================================================
print("\n3. 진동 스파이크 주입")
# =============================================================================
eng, t0 = new_engine()
f = eng.factories["S01"]
now = run(eng, t0, 60)
v_base = f.equipment["EQ-05"].vibration

sp = {"magnitude_mm_s": 8.0, "duration_seconds": 3.0, "repeat_count": 1,
      "repeat_interval_seconds": 20.0}
eng.injections[2] = Injection(
    id=2, tenant_id="S01", equipment_id="EQ-05", kind="vibration_spike",
    params=sp, starts_at=now, ends_at=default_end("vibration_spike", sp, now, PROFILE),
)
now = run(eng, now, 2)
v_spike = f.equipment["EQ-05"].vibration
check("스파이크 순간 진동 급등", v_spike > v_base + 6.0,
      f"{v_base:.2f} → {v_spike:.2f} mm/s")
check("VIB_HIGH 알람 발생", any(k[1] == "VIB_HIGH" and a.state == "OPEN"
                              for k, a in f.alarms.items()),
      f"임계 {PROFILE['alarm']['vibration_high_mm_s']} mm/s")
now = run(eng, now, 10)
check("스파이크 종료 후 정상 복귀", f.equipment["EQ-05"].vibration < v_base + 1.0,
      f"{f.equipment['EQ-05'].vibration:.2f} mm/s")

# 미세 스파이크(6σ) — 고정 임계값은 못 잡고 z-score 로만 잡히는 경우
eng2, t2 = new_engine()
f2 = eng2.factories["S01"]
t2 = run(eng2, t2, 60)
sp2 = {"magnitude_sigma": 6.0, "duration_seconds": 3.0, "repeat_count": 1}
eng2.injections[3] = Injection(id=3, tenant_id="S01", equipment_id="EQ-05",
                               kind="vibration_spike", params=sp2, starts_at=t2, ends_at=None)
vb = f2.equipment["EQ-05"].vibration
t2 = run(eng2, t2, 2)
va = f2.equipment["EQ-05"].vibration
sigma = PROFILE["vibration"]["noise_sigma"]
check("6σ 미세 스파이크는 고정 임계값을 못 넘음(z-score 로만 탐지)",
      va < PROFILE["alarm"]["vibration_high_mm_s"] and va > vb + 3 * sigma,
      f"{vb:.2f} → {va:.2f} mm/s, 임계 {PROFILE['alarm']['vibration_high_mm_s']}")

# =============================================================================
print("\n4. 센서 결측 주입")
# =============================================================================
eng, t0 = new_engine()
f = eng.factories["S01"]
now = run(eng, t0, 60)
dp = {"duration_seconds": 120.0}
eng.injections[4] = Injection(
    id=4, tenant_id="S01", equipment_id="EQ-01", kind="sensor_dropout",
    params=dp, starts_at=now, ends_at=default_end("sensor_dropout", dp, now, PROFILE),
)
now = run(eng, now, 5)
eq1 = f.equipment["EQ-01"]
check("결측 중 온도 NULL", eq1.temperature is None)
check("결측 중 진동·rpm 도 NULL", eq1.vibration is None and eq1.observed_rpm is None)
s_rows, _ = f.readings(now)
row = next(r for r in s_rows if r[0] == "EQ-01")
check("적재 행도 NULL 로 나감(z-score 통계가 깨지는 경험)",
      row[2] is None and row[3] is None, str(row[:5]))
now = run(eng, now, 40)
check("결측 30초 경과 후 SENSOR_LOSS 알람",
      any(k == ("EQ-01", "SENSOR_LOSS") and a.state == "OPEN" for k, a in f.alarms.items()))
now = run(eng, now, 120)
check("결측 종료 후 값 복귀", f.equipment["EQ-01"].temperature is not None,
      f"{f.equipment['EQ-01'].temperature:.2f}℃")

# =============================================================================
print("\n5. 제어 API — 폐루프가 닫히는가 (Day 4 핵심)")
# =============================================================================
eng, t0 = new_engine()
f = eng.factories["S01"]
now = run(eng, t0, 120)
before = f.equipment["EQ-03"].temperature

f.set_speed("EQ-03", 1200)
now = run(eng, now, 300)
after = f.equipment["EQ-03"].temperature
check("set_equipment_speed 로 감속하면 온도가 실제로 내려간다",
      after < before - 10, f"1800rpm {before:.1f}℃ → 1200rpm {after:.1f}℃")
check("rpm 도 실제로 내려감", 1150 < f.equipment["EQ-03"].rpm < 1250,
      f"{f.equipment['EQ-03'].rpm:.0f} rpm")

f.stop("EQ-04")
now = run(eng, now, 60)
check("stop_equipment 로 정지", f.equipment["EQ-04"].run_state == "STOP"
      and f.equipment["EQ-04"].rpm == 0, f"rpm {f.equipment['EQ-04'].rpm:.0f}")

r = f.robots["AMR-01"]
start_pos = (r.pos_x, r.pos_y)
res = f.dispatch("AMR-01", "EQ-03")
check("dispatch_robot 경로 산출", res["waypoints"] > 0,
      f"경유 {res['waypoints']}점, ETA {res['eta_seconds']}초")
now = run(eng, now, int(res["eta_seconds"]) + 5)
node = eng.graph.nodes["EQ-03"]
dist = ((r.pos_x - node[0]) ** 2 + (r.pos_y - node[1]) ** 2) ** 0.5
check("AMR 이 목적지에 실제로 도착", dist < 1.0,
      f"{start_pos} → ({r.pos_x:.0f},{r.pos_y:.0f}), 목표 ({node[0]:.0f},{node[1]:.0f})")
check("이동 중 배터리 소모", r.battery < 100.0, f"{r.battery:.2f}%")

# =============================================================================
print("\n6. 네임스페이스 격리 — 한 학생의 제어가 다른 학생에게 영향 없음 (교안 3절)")
# =============================================================================
eng, t0 = new_engine()
a, b = eng.factories["S01"], eng.factories["S02"]
now = run(eng, t0, 60)
a.stop("EQ-02")
a.set_speed("EQ-06", 600)
a.dispatch("AMR-02", "EQ-01")
now = run(eng, now, 120)
check("S01 만 정지됨", a.equipment["EQ-02"].run_state == "STOP"
      and b.equipment["EQ-02"].run_state == "RUN",
      f"S01={a.equipment['EQ-02'].run_state} / S02={b.equipment['EQ-02'].run_state}")
check("S01 만 감속됨", a.equipment["EQ-06"].target_rpm == 600
      and b.equipment["EQ-06"].target_rpm != 600,
      f"S01={a.equipment['EQ-06'].target_rpm:.0f} / S02={b.equipment['EQ-06'].target_rpm:.0f}")
check("S01 로봇만 이동", (a.robots["AMR-02"].pos_x, a.robots["AMR-02"].pos_y)
      != (b.robots["AMR-02"].pos_x, b.robots["AMR-02"].pos_y),
      f"S01={a.robots['AMR-02'].pos_x:.0f},{a.robots['AMR-02'].pos_y:.0f} / "
      f"S02={b.robots['AMR-02'].pos_x:.0f},{b.robots['AMR-02'].pos_y:.0f}")

eng.injections[9] = Injection(id=9, tenant_id="S01", equipment_id="EQ-03",
                              kind="temp_drift", params={"slope_c_per_hour": 5.0,
                                                         "duration_hours": 4},
                              starts_at=now, ends_at=None)
now = run(eng, now, 1800)
check("이상 주입도 지정 테넌트에만 적용",
      a.equipment["EQ-03"].temperature > b.equipment["EQ-03"].temperature + 1.5,
      f"S01={a.equipment['EQ-03'].temperature:.2f}℃ / S02={b.equipment['EQ-03'].temperature:.2f}℃")

# =============================================================================
print("\n7. 전 테넌트 일괄 주입 ('*')")
# =============================================================================
eng, t0 = new_engine()
now = run(eng, t0, 30)
eng.injections[10] = Injection(id=10, tenant_id="*", equipment_id="EQ-03",
                               kind="temp_drift",
                               params={"slope_c_per_hour": 6.0, "duration_hours": 1},
                               starts_at=now, ends_at=None)
now = run(eng, now, 1800)
both = [eng.factories[t].equipment["EQ-03"].temperature for t in ("S01", "S02")]
check("'*' 는 모든 테넌트에 동시 적용", all(v > 64.0 for v in both),
      f"S01={both[0]:.2f}℃ / S02={both[1]:.2f}℃")

# =============================================================================
print("\n8. 경로 그래프")
# =============================================================================
g = eng.graph
p = g.shortest_path("DOCK", "EQ-01")
check("DOCK → EQ-01 경로 존재", p == ["DOCK", "J4", "J3", "J2", "J1", "EQ-01"], " → ".join(p))
check("모든 노드가 DOCK 에서 도달 가능",
      all(g.shortest_path("DOCK", n) for n in g.nodes),
      f"{len(g.nodes)}개 노드")

# =============================================================================
print("\n9. 적재 행 스키마 — 교안 부록 A")
# =============================================================================
eng, t0 = new_engine()
now = run(eng, t0, 3)
s_rows, r_rows = eng.factories["S01"].readings(now)
check("설비 6행 + 로봇 2행 = 1초당 8행", len(s_rows) == 6 and len(r_rows) == 2,
      f"sensor {len(s_rows)}, robot {len(r_rows)}")
check("센서 행이 (equipment_id, timestamp, temperature, vibration, rpm, run_state, tenant_id)",
      len(s_rows[0]) == 7 and s_rows[0][0].startswith("EQ-") and s_rows[0][6] == "S01",
      str(s_rows[0]))

# =============================================================================
print("\n10. 가상 시계 — 배속을 올려도 샘플당 상승폭이 W5 와 같은가")
# =============================================================================
# 라이브 시연은 기울기를 키우는 것이 아니라 시계를 가속해서 만든다.
# 기울기를 키우면 샘플당 상승폭이 커져 Day 3 의 "드리프트는 미탐된다"가 깨진다.
W5_SAMPLE_MIN = 1.0
SLOPE = PROFILE["anomaly_defaults"]["temp_drift"]["slope_c_per_hour"]
w5_per_sample = SLOPE * W5_SAMPLE_MIN / 60

for scale, virt_step in ((1, 1.0), (60, 60.0), (80, 60.0), (120, 60.0)):
    eng, t0 = new_engine()
    f = eng.factories["S01"]
    f.virtual_step = virt_step
    now = t0
    for _ in range(30):                       # 안정화
        now += timedelta(seconds=virt_step)
        eng.tick(now, virt_step, dt_real=1.0)

    params = {"slope_c_per_hour": SLOPE, "duration_hours": 4.0, "hold_hours": 1.0}
    eng.injections[1] = Injection(id=1, tenant_id="S01", equipment_id="EQ-03",
                                  kind="temp_drift", params=params, starts_at=now,
                                  ends_at=default_end("temp_drift", params, now, PROFILE))
    # 잡음을 뺀 순수 드리프트 가산분으로 검증한다
    steps = int(4 * 3600 / virt_step)
    offs = []
    for _ in range(steps):
        now += timedelta(seconds=virt_step)
        eng.tick(now, virt_step, dt_real=1.0)
        offs.append(f.equipment["EQ-03"].drift_offset)
    deltas = [b - a for a, b in zip(offs, offs[1:]) if b > a]
    per_sample = sum(deltas) / len(deltas)
    real_tick = 1.0 if scale == 1 else 60.0 / scale
    real_min = 4 * 3600 / scale / 60

    if scale == 1:
        check(f"x{scale}: 기본 운전 — 실제 tick {real_tick}초", abs(real_tick - 1.0) < 1e-9)
    else:
        check(f"x{scale}: 샘플당 상승폭이 W5 와 동일",
              abs(per_sample - w5_per_sample) < 1e-6,
              f"{per_sample:.6f}℃ vs W5 {w5_per_sample:.6f}℃")
        check(f"x{scale}: 공장 4시간이 실제 {real_min:.0f}분",
              abs(offs[-1] - 2.0) < 0.01,
              f"총 상승 {offs[-1]:.3f}℃ (62→64), 실제 tick {real_tick:.2f}초")

eng, t0 = new_engine()
f = eng.factories["S01"]
f.virtual_step = 60.0
now = t0
for _ in range(30):
    now += timedelta(seconds=60); eng.tick(now, 60.0, dt_real=1.0)
params = {"slope_c_per_hour": SLOPE, "duration_hours": 4.0, "hold_hours": 1.0}
eng.injections[1] = Injection(id=1, tenant_id="S01", equipment_id="EQ-03", kind="temp_drift",
                              params=params, starts_at=now,
                              ends_at=default_end("temp_drift", params, now, PROFILE))
peak = 0.0
for _ in range(240):
    now += timedelta(seconds=60); eng.tick(now, 60.0, dt_real=1.0)
    peak = max(peak, f.equipment["EQ-03"].temperature)
check("가속해도 고정 임계값 80℃ 를 넘지 않음 — Day 1 서사·Day 3 미탐 학습 유지",
      peak < PROFILE["alarm"]["temp_high_c"], f"최고 {peak:.2f}℃")
check("가속해도 TEMP_HIGH 알람 미발생",
      not any(k[1] == "TEMP_HIGH" and a.state == "OPEN" for k, a in f.alarms.items()))

# 스파이크는 가상 샘플 한 칸보다 짧으면 데이터에서 사라진다 — 최소 한 칸으로 늘어나야 한다
eng, t0 = new_engine()
f = eng.factories["S01"]
f.virtual_step = 60.0
now = t0
for _ in range(10):
    now += timedelta(seconds=60); eng.tick(now, 60.0, dt_real=1.0)
v_base = f.equipment["EQ-05"].vibration
eng.injections[2] = Injection(id=2, tenant_id="S01", equipment_id="EQ-05",
                              kind="vibration_spike",
                              params={"magnitude_mm_s": 8.0, "duration_seconds": 3.0,
                                      "repeat_count": 1},
                              starts_at=now, ends_at=None)
now += timedelta(seconds=60); eng.tick(now, 60.0, dt_real=1.0)
check("가속 중 3초짜리 스파이크도 샘플에 잡힘(가상 1칸으로 보정)",
      f.equipment["EQ-05"].vibration > v_base + 6.0,
      f"{v_base:.2f} → {f.equipment['EQ-05'].vibration:.2f} mm/s")

# 로봇 주행은 배속과 무관하게 실제 시간을 따른다
eng, t0 = new_engine()
f = eng.factories["S01"]
f.virtual_step = 60.0
res = f.dispatch("AMR-01", "EQ-03")
now = t0
moved_ticks = 0
for _ in range(60):
    now += timedelta(seconds=60)
    eng.tick(now, 60.0, dt_real=1.0)          # 가상 60초, 실제 1초
    if f.robots["AMR-01"].waypoints:
        moved_ticks += 1
check("AMR 주행은 실제 시간 기준 — 배속을 올려도 순간이동하지 않음",
      abs(moved_ticks - res["eta_seconds"]) <= 2,
      f"{moved_ticks}틱(실제 {moved_ticks}초) 이동, ETA {res['eta_seconds']}초")

# =============================================================================
print("\n" + "=" * 70)
if failures:
    print(f"실패 {len(failures)}건: " + ", ".join(failures))
    sys.exit(1)
print("전 항목 통과")
