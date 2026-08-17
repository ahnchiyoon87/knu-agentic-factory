"""시뮬레이션 엔진 — 상태 생성기.

교안 3절: CNC 6대(온도·진동·rpm·가동상태) + AMR 2대(위치·배터리·적재상태) 가
1초 주기로 변동한다.

설계상 중요한 점 하나 — 온도는 rpm 의 함수다.
에이전트가 set_equipment_speed 로 감속하면 온도가 실제로 내려간다.
이 결합이 없으면 3일차의 「행동 → 다시 인지」 폐루프가 닫히지 않는다.

상태는 서버 프로세스 메모리에 있고 Supabase 에는 배치로 적재한다(리서치 확정안 4).
따라서 API 서버는 반드시 단일 프로세스로 띄운다(uvicorn --workers 1).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .graph import PathGraph

UTC = timezone.utc

RUN, IDLE, STOP, ALARM = "RUN", "IDLE", "STOP", "ALARM"
KIND_DRIFT, KIND_SPIKE, KIND_DROPOUT = "temp_drift", "vibration_spike", "sensor_dropout"


# =============================================================================
# 이상 주입
# =============================================================================
@dataclass
class Injection:
    id: int
    tenant_id: str          # '*' 이면 전체 테넌트
    equipment_id: str
    kind: str
    params: dict
    starts_at: datetime
    ends_at: datetime | None
    active: bool = True

    def is_live(self, now: datetime) -> bool:
        if not self.active or now < self.starts_at:
            return False
        return self.ends_at is None or now < self.ends_at


# =============================================================================
# 설비
# =============================================================================
@dataclass
class EquipmentState:
    equipment_id: str
    display_name: str
    pos_x: float
    pos_y: float
    nominal_rpm: float

    target_rpm: float = 0.0
    rpm: float = 0.0
    temperature: float | None = None
    vibration: float | None = None
    observed_rpm: float | None = None
    run_state: str = RUN
    sensor_online: bool = True

    # 내부 상태(관측값이 아니라 '진짜' 값)
    core_temp: float = 24.0
    temp_noise: float = 0.0       # 앞 값에 끌리는 온도 잡음(AR(1)) — 화면이 톡톡 안 튀게
    drift_offset: float = 0.0     # 현재 드리프트 가산분
    drift_target: float = 0.0     # 주입이 지시하는 목표 가산분
    spike_offset: float = 0.0
    offline_since: datetime | None = None


# =============================================================================
# 로봇
# =============================================================================
@dataclass
class RobotState:
    robot_id: str
    display_name: str
    pos_x: float
    pos_y: float
    home_node: str
    battery: float = 100.0
    payload_state: str = "EMPTY"
    status: str = "IDLE"
    target_node: str | None = None
    waypoints: list[tuple[float, float]] = field(default_factory=list)


# =============================================================================
# 알람 (메모리 미러 — 권위는 DB)
# =============================================================================
@dataclass
class AlarmState:
    key: tuple[str, str]          # (equipment_id, rule_code)
    db_id: int | None
    severity: str
    message: str
    value: float | None
    threshold: float | None
    raised_at: datetime
    state: str = "OPEN"


# =============================================================================
# 테넌트 하나의 공장
# =============================================================================
class Factory:
    def __init__(self, tenant_id: str, layout: dict, profile: dict, graph: PathGraph,
                 rng: random.Random) -> None:
        self.tenant_id = tenant_id
        self.layout = layout
        self.profile = profile
        self.graph = graph
        self.rng = rng

        th = profile["thermal"]
        self.equipment: dict[str, EquipmentState] = {}
        for spec in layout["equipment"]:
            eq = EquipmentState(
                equipment_id=spec["equipment_id"],
                display_name=spec["display_name"],
                pos_x=float(spec["pos_x"]),
                pos_y=float(spec["pos_y"]),
                nominal_rpm=float(spec["nominal_rpm"]),
            )
            eq.target_rpm = eq.nominal_rpm
            eq.rpm = eq.nominal_rpm
            eq.core_temp = self._temp_target(eq.rpm)
            eq.temperature = eq.core_temp
            eq.vibration = self._vib_true(eq.rpm)
            eq.run_state = RUN
            self.equipment[eq.equipment_id] = eq
        self._ambient = float(th["ambient_c"])

        self.robots: dict[str, RobotState] = {}
        for spec in layout["robots"]:
            home = spec["home_node"]
            hx, hy = graph.nodes[home]
            self.robots[spec["robot_id"]] = RobotState(
                robot_id=spec["robot_id"],
                display_name=spec["display_name"],
                pos_x=hx,
                pos_y=hy,
                home_node=home,
                status="CHARGING" if home == "DOCK" else "IDLE",
            )

        self.alarms: dict[tuple[str, str], AlarmState] = {}
        self.new_alarms: list[AlarmState] = []      # 러너가 DB 에 넣고 id 를 채운다
        self.cleared_alarms: list[AlarmState] = []

        # 가상 샘플 한 칸의 길이(초). 러너가 배속에 맞춰 갱신한다.
        self.virtual_step: float = 1.0

    # ---------------------------------------------------------------- 물리식
    def _temp_target(self, rpm: float) -> float:
        th = self.profile["thermal"]
        if rpm <= 1.0:
            return float(th["ambient_c"])
        return float(th["ambient_c"]) + float(th["gain"]) * (rpm / 1000.0) ** float(
            th["rpm_exponent"]
        )

    def _vib_true(self, rpm: float) -> float:
        vb = self.profile["vibration"]
        if rpm <= 1.0:
            return 0.0
        return float(vb["base_mm_s"]) + float(vb["rpm_gain"]) * (
            rpm / float(vb["rpm_reference"])
        ) ** 2

    # ------------------------------------------------------------------ tick
    def tick(self, now: datetime, dt: float, injections: list[Injection],
             dt_real: float | None = None) -> None:
        """now/dt 는 공장의 시계(가상). dt_real 은 실제 경과 시간.

        설비 물리·이상 주입·샘플링은 가상 시간을 따른다 — 그래야 배속을 올려도
        샘플당 상승폭이 7일치 CSV 와 같게 유지된다.

        로봇 주행만 실제 시간을 따른다. 배속 ×60 에서 가상 시간으로 움직이면
        공장을 가로지르는 데 0.2초가 걸려 눈에 안 보인다. 3일차 클라이맥스가
        "화면에서 AMR 이 실제로 움직인다"이므로 이 하나는 예외로 둔다.
        """
        self._apply_injections(now, injections)
        self._tick_equipment(now, dt)
        self._tick_robots(now, dt_real if dt_real is not None else dt)
        self._evaluate_alarms(now)

    # --------------------------------------------------------- 이상 주입 반영
    def _apply_injections(self, now: datetime, injections: list[Injection]) -> None:
        for eq in self.equipment.values():
            eq.drift_target = 0.0
            eq.spike_offset = 0.0
        online = {eid: True for eid in self.equipment}

        for inj in injections:
            eq = self.equipment.get(inj.equipment_id)
            if eq is None or not inj.is_live(now):
                continue
            elapsed_h = max(0.0, (now - inj.starts_at).total_seconds() / 3600.0)
            p = inj.params

            if inj.kind == KIND_DRIFT:
                # 램프 구간이 끝나면 최고점에서 유지된다(주입이 멈출 때까지).
                slope = float(p.get("slope_c_per_hour", 0.5))
                dur = float(p.get("duration_hours", 4.0))
                eq.drift_target += slope * min(elapsed_h, dur)

            elif inj.kind == KIND_SPIKE:
                # 스파이크가 가상 샘플 한 칸보다 짧으면 샘플 사이로 빠져나가
                # 데이터에 아예 안 잡힌다. 최소 한 칸은 유지한다.
                dur_s = max(float(p.get("duration_seconds", 3.0)), self.virtual_step)
                gap_s = float(p.get("repeat_interval_seconds", 20.0))
                count = int(p.get("repeat_count", 1))
                elapsed_s = (now - inj.starts_at).total_seconds()
                period = dur_s + gap_s
                idx = int(elapsed_s // period) if period > 0 else 0
                within = elapsed_s - idx * period
                # 끝점을 포함한다. 가상 샘플 한 칸으로 보정된 스파이크는 주입 직후
                # 첫 tick(경과 = 한 칸)에만 걸리므로 열린 구간이면 놓친다.
                if idx < count and 0.0 <= within <= dur_s:
                    mm_s = p.get("magnitude_mm_s")
                    if mm_s not in (None, ""):
                        eq.spike_offset += float(mm_s)
                    else:
                        sigma = float(self.profile["vibration"]["noise_sigma"])
                        eq.spike_offset += float(p.get("magnitude_sigma", 6.0)) * sigma

            elif inj.kind == KIND_DROPOUT:
                online[inj.equipment_id] = False

        for eid, is_on in online.items():
            eq = self.equipment[eid]
            if is_on and not eq.sensor_online:
                eq.sensor_online = True
                eq.offline_since = None
            elif not is_on and eq.sensor_online:
                eq.sensor_online = False
                eq.offline_since = now

    # ------------------------------------------------------------- 설비 갱신
    def _tick_equipment(self, now: datetime, dt: float) -> None:
        pr = self.profile
        th, vb, rp = pr["thermal"], pr["vibration"], pr["rpm"]
        tau = float(th["tau_seconds"])
        alpha = 1.0 - math.exp(-dt / tau) if tau > 0 else 1.0

        for eq in self.equipment.values():
            # 1) rpm 은 목표를 향해 램프
            desired = 0.0 if eq.run_state == STOP else eq.target_rpm
            step = float(rp["ramp_per_second"]) * dt
            if eq.rpm < desired:
                eq.rpm = min(desired, eq.rpm + step)
            elif eq.rpm > desired:
                eq.rpm = max(desired, eq.rpm - step)

            # 2) 가동상태 — 정지 지시가 아니면 rpm 으로 판정
            if eq.run_state != STOP:
                eq.run_state = RUN if eq.rpm > 50 else IDLE

            # 3) 온도 — 1차 지연으로 목표에 수렴 (감속하면 실제로 내려간다)
            eq.core_temp += (self._temp_target(eq.rpm) - eq.core_temp) * alpha

            # 3-1) 드리프트 가산분. 올라갈 때는 주입이 지시한 값을 그대로 따르고,
            #      주입이 끝나면 순간 복귀가 아니라 정해진 속도로 서서히 회복한다.
            #      (주입 종료 순간 2℃ 가 툭 떨어지면 화면에서 오작동처럼 보인다)
            recov = float(th.get("drift_recovery_c_per_minute", 0.2)) / 60.0 * dt
            if eq.drift_target >= eq.drift_offset:
                eq.drift_offset = eq.drift_target
            else:
                eq.drift_offset = max(eq.drift_target, eq.drift_offset - recov)

            # 4) 관측값 = 진짜값 + 이상주입 + 잡음
            #    노이즈가 없으면 단순 임계값으로 전부 잡혀 2일차 실습이 성립하지 않는다.
            #
            #    ★ 온도 잡음은 **앞 값에 끌린다**(AR(1) · 색깔 있는 잡음).
            #      전에는 매 샘플마다 독립적인 가우시안을 새로 뽑아서 화면 숫자가 톡톡 튀었다.
            #      진짜 베어링은 쇳덩이라 1분 간격으로 보면 부드럽게 움직인다.
            #      7일치 CSV 실측이 그 증거다 — **1차 자기상관 0.80**.
            #      라이브만 백색 잡음이라 질감이 혼자 달랐다.
            #
            #      폭은 그대로 둔다. a 를 섞어도 정상상태 표준편차가 noise_sigma_c 가 되도록
            #      새로 뽑는 몫에 sqrt(1-a²) 를 곱한다. 그래서 **오탐·미탐 성질이 안 바뀐다.**
            #      (실습 숫자는 전부 7일치 CSV 에서 나오므로 여기 값은 화면 질감만 정한다)
            if eq.sensor_online:
                a = float(th.get("noise_memory", 0.8))
                σ = float(th["noise_sigma_c"])
                eq.temp_noise = a * eq.temp_noise + self.rng.gauss(0.0, σ * (1 - a * a) ** 0.5)
                eq.temperature = round(
                    eq.core_temp + eq.drift_offset + eq.temp_noise, 3
                )
                eq.vibration = round(
                    max(0.0, self._vib_true(eq.rpm) + eq.spike_offset
                        + self.rng.gauss(0.0, float(vb["noise_sigma"]))), 3
                )
                observed_rpm = max(0.0, eq.rpm + self.rng.gauss(0.0, float(rp["noise_sigma"])))
                eq.observed_rpm = round(observed_rpm, 1)
            else:
                # 센서 결측 — 값이 아예 안 들어온다(NULL). z-score 통계가 깨진다.
                eq.temperature = None
                eq.vibration = None
                eq.observed_rpm = None

    # ------------------------------------------------------------- 로봇 갱신
    def _tick_robots(self, now: datetime, dt: float) -> None:
        bt = self.profile["battery"]
        rb = self.profile["robot"]
        speed = float(rb["speed_units_per_second"])

        for r in self.robots.values():
            if r.waypoints:
                remaining = speed * dt
                while remaining > 0 and r.waypoints:
                    tx, ty = r.waypoints[0]
                    d = math.hypot(tx - r.pos_x, ty - r.pos_y)
                    if d <= remaining or d < 1e-6:
                        r.pos_x, r.pos_y = tx, ty
                        r.waypoints.pop(0)
                        remaining -= d
                    else:
                        r.pos_x += (tx - r.pos_x) / d * remaining
                        r.pos_y += (ty - r.pos_y) / d * remaining
                        remaining = 0.0
                r.status = "MOVING" if r.waypoints else "IDLE"
                if not r.waypoints:
                    # 도착
                    if r.target_node == "DOCK":
                        r.status = "CHARGING"
                    elif r.target_node == "WH":
                        r.payload_state = "LOADED"
                    elif r.target_node and r.target_node.startswith("EQ-"):
                        r.payload_state = "EMPTY"
            else:
                at_dock = self.graph.nearest_node(r.pos_x, r.pos_y) == "DOCK"
                r.status = "CHARGING" if at_dock and r.battery < 99.9 else (
                    "CHARGING" if r.status == "CHARGING" and r.battery < 99.9 else "IDLE"
                )

            # 배터리
            if r.status == "MOVING":
                r.battery -= float(bt["drain_per_second_moving"]) * dt
            elif r.status == "CHARGING":
                r.battery += float(bt["charge_per_second"]) * dt
            else:
                r.battery -= float(bt["drain_per_second_idle"]) * dt
            r.battery = round(min(100.0, max(0.0, r.battery)), 2)

            # 배터리 부족 시 자동 복귀
            if (
                rb.get("auto_return_to_dock", True)
                and r.battery < float(bt["low_threshold"])
                and r.status not in ("CHARGING",)
                and r.target_node != "DOCK"
            ):
                self.dispatch(r.robot_id, "DOCK")

            r.pos_x, r.pos_y = round(r.pos_x, 2), round(r.pos_y, 2)

    # -------------------------------------------------------------- 알람 판정
    def _evaluate_alarms(self, now: datetime) -> None:
        al = self.profile["alarm"]
        t_hi = float(al["temp_high_c"])
        v_hi = float(al["vibration_high_mm_s"])
        hyst = float(al["clear_hysteresis"])
        loss_s = float(al["sensor_loss_seconds"])

        for eq in self.equipment.values():
            self._check(now, eq, "TEMP_HIGH",
                        eq.temperature is not None and eq.temperature > t_hi,
                        eq.temperature is not None and eq.temperature < t_hi - hyst,
                        "CRITICAL", f"{eq.equipment_id} 온도 {t_hi}℃ 초과",
                        eq.temperature, t_hi)

            self._check(now, eq, "VIB_HIGH",
                        eq.vibration is not None and eq.vibration > v_hi,
                        eq.vibration is not None and eq.vibration < v_hi - hyst * 0.25,
                        "WARN", f"{eq.equipment_id} 진동 {v_hi}mm/s 초과",
                        eq.vibration, v_hi)

            offline_for = (
                (now - eq.offline_since).total_seconds() if eq.offline_since else 0.0
            )
            self._check(now, eq, "SENSOR_LOSS",
                        (not eq.sensor_online) and offline_for >= loss_s,
                        eq.sensor_online,
                        "WARN", f"{eq.equipment_id} 센서 값 수신 중단",
                        None, None)

    def _check(self, now: datetime, eq: EquipmentState, rule: str,
               should_raise: bool, should_clear: bool,
               severity: str, message: str,
               value: float | None, threshold: float | None) -> None:
        key = (eq.equipment_id, rule)
        cur = self.alarms.get(key)

        if should_raise and (cur is None or cur.state == "CLEARED"):
            a = AlarmState(key=key, db_id=None, severity=severity, message=message,
                           value=value, threshold=threshold, raised_at=now)
            self.alarms[key] = a
            self.new_alarms.append(a)
        elif should_clear and cur is not None and cur.state in ("OPEN", "ACKED"):
            cur.state = "CLEARED"
            self.cleared_alarms.append(cur)

    # ------------------------------------------------------- 제어 API 진입점
    def set_speed(self, equipment_id: str, rpm: float) -> dict:
        eq = self.equipment[equipment_id]
        rpm = max(0.0, min(3000.0, float(rpm)))
        eq.target_rpm = rpm
        if rpm > 0 and eq.run_state == STOP:
            eq.run_state = IDLE          # 정지 해제 — 다음 tick 에 RUN 으로 올라간다
        return {"equipment_id": equipment_id, "target_rpm": rpm, "run_state": eq.run_state}

    def stop(self, equipment_id: str) -> dict:
        eq = self.equipment[equipment_id]
        eq.run_state = STOP
        eq.target_rpm = 0.0
        return {"equipment_id": equipment_id, "run_state": STOP}

    def dispatch(self, robot_id: str, target: str | dict) -> dict:
        r = self.robots[robot_id]
        if isinstance(target, dict):
            tx, ty = float(target["x"]), float(target["y"])
            node = self.graph.nearest_node(tx, ty)
        else:
            node = str(target)
            if node not in self.graph.nodes:
                raise KeyError(f"알 수 없는 목적지: {node}")
        r.waypoints = self.graph.waypoints(r.pos_x, r.pos_y, node)[1:]
        r.target_node = node
        r.status = "MOVING" if r.waypoints else r.status
        return {
            "robot_id": robot_id,
            "target": node,
            "waypoints": len(r.waypoints),
            "eta_seconds": round(self._eta(r), 1),
        }

    def _eta(self, r: RobotState) -> float:
        speed = float(self.profile["robot"]["speed_units_per_second"])
        if not r.waypoints or speed <= 0:
            return 0.0
        total = math.hypot(r.waypoints[0][0] - r.pos_x, r.waypoints[0][1] - r.pos_y)
        for a, b in zip(r.waypoints, r.waypoints[1:]):
            total += math.hypot(b[0] - a[0], b[1] - a[1])
        return total / speed

    # ------------------------------------------------------------- 스냅샷
    def snapshot(self, now: datetime) -> dict:
        return {
            "tenant_id": self.tenant_id,
            # server_time 은 공장의 시계(가상 시각)다. 배속 가동 중에는 실제 시각보다 앞선다.
            # sensor_readings.timestamp 와 같은 시계이므로 그래프 x축에 그대로 쓸 수 있다.
            "server_time": now.isoformat(),
            "equipment": [
                {
                    "equipment_id": e.equipment_id,
                    "display_name": e.display_name,
                    "pos_x": e.pos_x,
                    "pos_y": e.pos_y,
                    "temperature": e.temperature,
                    "vibration": e.vibration,
                    "rpm": e.observed_rpm,
                    "run_state": e.run_state,
                    "target_rpm": e.target_rpm,
                    "sensor_online": e.sensor_online,
                }
                for e in self.equipment.values()
            ],
            "robots": [
                {
                    "robot_id": r.robot_id,
                    "display_name": r.display_name,
                    "pos_x": r.pos_x,
                    "pos_y": r.pos_y,
                    "battery": r.battery,
                    "payload_state": r.payload_state,
                    "status": r.status,
                    "target_node": r.target_node,
                    "eta_seconds": round(self._eta(r), 1),
                }
                for r in self.robots.values()
            ],
            "alarms": [
                {
                    "id": a.db_id,
                    "equipment_id": a.key[0],
                    "rule_code": a.key[1],
                    "severity": a.severity,
                    "message": a.message,
                    "value": a.value,
                    "threshold": a.threshold,
                    "state": a.state,
                    "raised_at": a.raised_at.isoformat(),
                }
                for a in self.alarms.values()
                if a.state in ("OPEN", "ACKED")
            ],
        }

    # --------------------------------------------------- 적재용 행 만들기
    def readings(self, now: datetime) -> tuple[list[tuple], list[tuple]]:
        """(sensor_rows, robot_rows) — asyncpg copy_records_to_table 용 튜플."""
        sensor = [
            (
                e.equipment_id,
                now,
                e.temperature,
                e.vibration,
                e.observed_rpm,
                e.run_state,
                self.tenant_id,
            )
            for e in self.equipment.values()
        ]
        robot = [
            (
                r.robot_id,
                now,
                r.pos_x,
                r.pos_y,
                r.battery,
                r.payload_state,
                r.status,
                self.tenant_id,
            )
            for r in self.robots.values()
        ]
        return sensor, robot


# =============================================================================
# 전체 엔진
# =============================================================================
class SimEngine:
    def __init__(self, layout: dict, profile: dict, seed: int = 42) -> None:
        self.layout = layout
        self.profile = profile
        self.graph = PathGraph(layout)
        self.factories: dict[str, Factory] = {}
        self.injections: dict[int, Injection] = {}
        self._seed = seed

    def ensure_tenant(self, tenant_id: str) -> Factory:
        f = self.factories.get(tenant_id)
        if f is None:
            # 테넌트마다 다른 시드 → 같은 공장이지만 노이즈는 서로 다르다
            rng = random.Random(f"{self._seed}:{tenant_id}")
            f = Factory(tenant_id, self.layout, self.profile, self.graph, rng)
            self.factories[tenant_id] = f
        return f

    def drop_tenant(self, tenant_id: str) -> None:
        self.factories.pop(tenant_id, None)

    def injections_for(self, tenant_id: str) -> list[Injection]:
        return [
            i for i in self.injections.values()
            if i.tenant_id in ("*", tenant_id)
        ]

    def tick(self, now: datetime, dt: float, dt_real: float | None = None) -> None:
        for tid, f in self.factories.items():
            f.tick(now, dt, self.injections_for(tid), dt_real)

    def set_virtual_step(self, seconds: float) -> None:
        for f in self.factories.values():
            f.virtual_step = seconds

    def expire_injections(self, now: datetime) -> list[int]:
        """끝난 주입을 비활성화하고 그 id 목록을 돌려준다."""
        done = [
            i.id for i in self.injections.values()
            if i.active and i.ends_at is not None and now >= i.ends_at
        ]
        for iid in done:
            self.injections[iid].active = False
        return done


def default_end(kind: str, params: dict, starts_at: datetime,
                profile: dict) -> datetime | None:
    """주입 종료시각 기본값 계산."""
    d = profile["anomaly_defaults"]
    if kind == KIND_DRIFT:
        # 램프 구간 + 유지 구간. 유지 구간 동안 최고 온도가 그대로 남아 있어야
        # 에이전트가 감지·진단·조치할 시간이 생긴다.
        hours = float(params.get("duration_hours", d["temp_drift"]["duration_hours"]))
        hold = float(params.get("hold_hours", d["temp_drift"].get("hold_hours", 1.0)))
        return starts_at + timedelta(hours=hours + hold)
    if kind == KIND_SPIKE:
        dur = float(params.get("duration_seconds", d["vibration_spike"]["duration_seconds"]))
        gap = float(params.get("repeat_interval_seconds",
                               d["vibration_spike"]["repeat_interval_seconds"]))
        cnt = int(params.get("repeat_count", d["vibration_spike"]["repeat_count"]))
        return starts_at + timedelta(seconds=(dur + gap) * max(1, cnt))
    if kind == KIND_DROPOUT:
        secs = float(params.get("duration_seconds", d["sensor_dropout"]["duration_seconds"]))
        return starts_at + timedelta(seconds=secs)
    return None
