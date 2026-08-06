"""W5 — K-정밀 레거시 센서 데이터셋 생성기.

교안 부록 A:
    CNC 6대 x 7일 x 1분 간격 ≈ 6만 행
    컬럼 equipment_id, timestamp, temperature, vibration, rpm, run_state
    삽입 이상 3종 — EQ-03 온도 드리프트(5일차) / EQ-05 진동 스파이크(3일차)
                     / EQ-01 센서 결측 2시간(6일차)
    시드 고정, 재현 가능

견적서 W5 제약:
    "시뮬레이터 실시간 스트림과 동일 스키마"
    "정상 구간에 가우시안 노이즈 포함 — 단순 임계값으로 전부 잡히면
     Lab 3-2 의 오탐·미탐 학습이 성립하지 않음"

그래서 물리 파라미터를 여기에 다시 적지 않는다.
W1 시뮬레이터의 config/sim_profile.json 과 layout.json 을 그대로 읽어 쓴다.
두 벌로 나누면 반드시 어긋나고, 어긋나면 Lab 3-1 의 "과거 + 현재가 한 테이블에
합쳐진다"가 성립하지 않는다.

실행:
    python generate.py
    python generate.py --seed 42 --out 데이터
    python generate.py --no-diurnal          일주기 변동 제외
    python generate.py --w1-config <경로>     W1 config 디렉터리 지정
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DEFAULT_W1_CONFIG = ROOT.parents[1] / "0_공통" / "W1_팩토리시뮬레이터" / "config"

# 교안 부록 A 가 고정한 컬럼. 순서를 바꾸지 말 것.
COLUMNS = ["equipment_id", "timestamp", "temperature", "vibration", "rpm", "run_state"]

RUN, IDLE, STOP = "RUN", "IDLE", "STOP"


# =============================================================================
# 설정 로딩
# =============================================================================
def load_configs(w1_dir: Path) -> tuple[dict, dict, dict]:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

    profile_path = w1_dir / "sim_profile.json"
    layout_path = w1_dir / "layout.json"
    if not profile_path.exists() or not layout_path.exists():
        sys.exit(
            f"W1 설정을 찾지 못했습니다: {w1_dir}\n"
            "  W5 는 물리 파라미터를 W1 시뮬레이터와 공유합니다(동일 스키마·동일 성질 보장).\n"
            "  --w1-config 로 W1_팩토리시뮬레이터/config 경로를 지정하세요."
        )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    return cfg, profile, layout


# =============================================================================
# 물리식 — W1 engine.py 와 동일
# =============================================================================
def temp_target(rpm: float, ambient: float, gain: float, exponent: float) -> float:
    if rpm <= 1.0:
        return ambient
    return ambient + gain * (rpm / 1000.0) ** exponent


def vib_true(rpm: float, base: float, gain: float, ref: float) -> float:
    if rpm <= 1.0:
        return 0.0
    return base + gain * (rpm / ref) ** 2


# =============================================================================
# 생성
# =============================================================================
def generate(cfg: dict, profile: dict, layout: dict, *,
             seed: int, diurnal_on: bool) -> tuple[pd.DataFrame, list[dict]]:
    rng = np.random.default_rng(seed)

    th, vb, rp = profile["thermal"], profile["vibration"], profile["rpm"]
    ambient = float(th["ambient_c"])
    gain, expo = float(th["gain"]), float(th["rpm_exponent"])
    tau = float(th["tau_seconds"])
    t_noise = float(th["noise_sigma_c"])
    v_noise = float(vb["noise_sigma"])
    r_noise = float(rp["noise_sigma"])

    step_min = int(cfg["sample_interval_minutes"])
    step_sec = step_min * 60
    alpha = 1.0 - math.exp(-step_sec / tau)          # 1차 지연 (W1 과 동일)

    start = datetime.fromisoformat(cfg["start_date"])
    n_steps = int(cfg["days"]) * 24 * 60 // step_min
    stamps = [start + timedelta(minutes=step_min * i) for i in range(n_steps)]

    dn = cfg["diurnal"]
    dn_amp = float(dn["amplitude_c"]) if (diurnal_on and dn.get("enabled", True)) else 0.0
    dn_peak = float(dn["peak_hour"])

    anom = cfg["anomalies"]
    drift_defaults = profile["anomaly_defaults"]["temp_drift"]
    spike_defaults = profile["anomaly_defaults"]["vibration_spike"]

    # --- 이상 구간 계산 -------------------------------------------------------
    def day_start(day: int) -> datetime:
        return start + timedelta(days=day - 1)

    d = anom["temp_drift"]
    drift_from = day_start(d["day"]) + timedelta(hours=d["start_hour"])
    drift_slope = float(drift_defaults["slope_c_per_hour"])
    drift_hours = float(drift_defaults["duration_hours"])
    drift_to = drift_from + timedelta(hours=drift_hours)

    s = anom["vibration_spike"]
    spike_at = {
        day_start(s["day"]) + timedelta(hours=s["start_hour"], minutes=s["start_minute"])
        + timedelta(minutes=s["interval_minutes"] * k)
        for k in range(int(s["count"]))
    }
    spike_sigma = float(s.get("magnitude_sigma", spike_defaults["magnitude_sigma"]))
    spike_mag = spike_sigma * v_noise

    m = anom["sensor_dropout"]
    drop_from = day_start(m["day"]) + timedelta(hours=m["start_hour"])
    drop_to = drop_from + timedelta(hours=float(m["duration_hours"]))

    labels = [
        {"equipment_id": d["equipment_id"], "kind": "temp_drift",
         "start": drift_from, "end": drift_to,
         "detail": f"온도 점진 상승 {drift_slope}℃/시간 x {drift_hours:.0f}시간 (총 +{drift_slope*drift_hours:.1f}℃)"},
        {"equipment_id": s["equipment_id"], "kind": "vibration_spike",
         "start": min(spike_at), "end": max(spike_at),
         "detail": f"순간 진동 급등 {spike_sigma:g}σ (+{spike_mag:.2f} mm/s) x {s['count']}회, 간격 {s['interval_minutes']}분"},
        {"equipment_id": m["equipment_id"], "kind": "sensor_dropout",
         "start": drop_from, "end": drop_to,
         "detail": f"센서 값 수신 중단 {m['duration_hours']}시간"},
    ]

    # --- 정지 구간 (정상 운전이며 이상이 아니다) ------------------------------
    st = cfg["stops"]
    stop_windows: dict[str, list[tuple[datetime, datetime]]] = {}
    for eq in layout["equipment"]:
        wins = []
        for day in range(int(cfg["days"]) if int(st["per_machine_per_day"]) else 0):
            for _ in range(int(st["per_machine_per_day"])):
                hh = int(rng.integers(int(st["hour_min"]), int(st["hour_max"])))
                mm = int(rng.integers(0, 60))
                dur = int(rng.integers(int(st["duration_minutes_min"]),
                                       int(st["duration_minutes_max"]) + 1))
                a = start + timedelta(days=day, hours=hh, minutes=mm)
                wins.append((a, a + timedelta(minutes=dur)))
        stop_windows[eq["equipment_id"]] = wins

    def in_stop(eid: str, ts: datetime) -> bool:
        return any(a <= ts < b for a, b in stop_windows[eid])

    # --- 설비별 시계열 --------------------------------------------------------
    frames = []
    for eq in layout["equipment"]:
        eid = eq["equipment_id"]
        nominal = float(eq["nominal_rpm"])

        t_eps = rng.normal(0.0, t_noise, n_steps)
        v_eps = rng.normal(0.0, v_noise, n_steps)
        r_eps = rng.normal(0.0, r_noise, n_steps)

        core = temp_target(nominal, ambient, gain, expo)
        temps, vibs, rpms, states = [], [], [], []

        for i, ts in enumerate(stamps):
            stopped = in_stop(eid, ts)
            rpm_cmd = 0.0 if stopped else nominal

            # 일주기 외기 변동
            amb = ambient
            if dn_amp:
                hour = ts.hour + ts.minute / 60.0
                amb += dn_amp * math.sin(2 * math.pi * (hour - dn_peak + 6) / 24.0)

            core += (temp_target(rpm_cmd, amb, gain, expo) - core) * alpha

            drift = drift_slope * ((ts - drift_from).total_seconds() / 3600.0) \
                if (eid == d["equipment_id"] and drift_from <= ts < drift_to) else 0.0
            spike = spike_mag if (eid == s["equipment_id"] and ts in spike_at) else 0.0

            temps.append(core + drift + t_eps[i])
            vibs.append(max(0.0, vib_true(rpm_cmd, float(vb["base_mm_s"]),
                                          float(vb["rpm_gain"]), float(vb["rpm_reference"]))
                            + spike + v_eps[i]))
            rpms.append(max(0.0, rpm_cmd + (r_eps[i] if rpm_cmd > 0 else 0.0)))
            states.append(STOP if stopped else RUN)

        df = pd.DataFrame({
            "equipment_id": eid,
            "timestamp": stamps,
            "temperature": np.round(temps, 3),
            "vibration": np.round(vibs, 3),
            "rpm": np.round(rpms, 1),
            "run_state": states,
        })

        # 센서 결측 — 값만 빠지고 행과 run_state 는 남는다(W1 실시간 스트림과 동일)
        if eid == m["equipment_id"]:
            mask = (df["timestamp"] >= drop_from) & (df["timestamp"] < drop_to)
            df.loc[mask, ["temperature", "vibration", "rpm"]] = np.nan

        frames.append(df)

    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(["timestamp", "equipment_id"], kind="mergesort").reset_index(drop=True)
    return out[COLUMNS], labels


# =============================================================================
# 라벨
# =============================================================================
def build_row_labels(df: pd.DataFrame, labels: list[dict]) -> pd.DataFrame:
    lab = pd.DataFrame({
        "equipment_id": df["equipment_id"],
        "timestamp": df["timestamp"],
        "is_anomaly": 0,
        "anomaly_kind": "",
    })
    for L in labels:
        mask = ((df["equipment_id"] == L["equipment_id"])
                & (df["timestamp"] >= L["start"]) & (df["timestamp"] <= L["end"]))
        lab.loc[mask, "is_anomaly"] = 1
        lab.loc[mask, "anomaly_kind"] = L["kind"]
    # 스파이크는 구간이 아니라 점이라 사이 구간까지 1 이 되면 안 된다
    spike = next(L for L in labels if L["kind"] == "vibration_spike")
    between = ((lab["equipment_id"] == spike["equipment_id"])
               & (lab["anomaly_kind"] == "vibration_spike")
               & (~df["timestamp"].isin(_spike_points(df, spike))))
    lab.loc[between, ["is_anomaly", "anomaly_kind"]] = [0, ""]
    return lab


def _spike_points(df: pd.DataFrame, spike: dict) -> set:
    sub = df[(df["equipment_id"] == spike["equipment_id"])
             & (df["timestamp"] >= spike["start"]) & (df["timestamp"] <= spike["end"])]
    # 진동 상위 3개가 스파이크 지점
    return set(sub.nlargest(3, "vibration")["timestamp"])


# =============================================================================
# main
# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description="W5 레거시 센서 데이터셋 생성")
    ap.add_argument("--seed", type=int, default=None, help="비우면 config.json 값")
    ap.add_argument("--out", default="데이터", help="출력 디렉터리")
    ap.add_argument("--no-diurnal", action="store_true", help="일주기 외기 변동 제외")
    ap.add_argument("--w1-config", default=str(DEFAULT_W1_CONFIG), help="W1 config 디렉터리")
    args = ap.parse_args()

    cfg, profile, layout = load_configs(Path(args.w1_config))
    seed = args.seed if args.seed is not None else int(cfg["seed"])

    print("=" * 72)
    print("W5 레거시 센서 데이터셋 생성")
    print(f"  W1 설정   {args.w1_config}")
    print(f"  시드      {seed} (고정 — 같은 시드는 같은 파일)")
    print(f"  기간      {cfg['start_date']} 부터 {cfg['days']}일 · {cfg['sample_interval_minutes']}분 간격")
    print(f"  설비      {len(layout['equipment'])}대")
    print("=" * 72)

    df, labels = generate(cfg, profile, layout, seed=seed,
                          diurnal_on=not args.no_diurnal)

    outdir = ROOT / args.out
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "sensor_readings_7days.csv"
    # float_format 을 전역으로 주면 rpm 이 1799.300 처럼 나온다.
    # 컬럼별로 이미 반올림했으므로 그대로 내보낸다.
    df.to_csv(csv_path, index=False, date_format="%Y-%m-%dT%H:%M:%S",
              encoding="utf-8", lineterminator="\n")

    iv = pd.DataFrame([{
        "equipment_id": L["equipment_id"], "kind": L["kind"],
        "start": L["start"].isoformat(), "end": L["end"].isoformat(),
        "detail": L["detail"],
    } for L in labels])
    iv.to_csv(outdir / "labels_intervals.csv", index=False,
              encoding="utf-8-sig", lineterminator="\n")

    row_lab = build_row_labels(df, labels)
    row_lab.to_csv(outdir / "labels_rowwise.csv", index=False,
                   date_format="%Y-%m-%dT%H:%M:%S", encoding="utf-8", lineterminator="\n")

    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    print(f"\n행 수        {len(df):,} (설비 {df['equipment_id'].nunique()}대 x "
          f"{len(df)//df['equipment_id'].nunique():,} 시점)")
    print(f"기간         {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    print(f"결측         temperature {int(df['temperature'].isna().sum())}행")
    print(f"이상 라벨    {int(row_lab['is_anomaly'].sum())}행")
    for L in labels:
        print(f"   · {L['equipment_id']} {L['kind']:16s} {L['start']:%m-%d %H:%M} ~ "
              f"{L['end']:%m-%d %H:%M}  {L['detail']}")
    print(f"\nSHA-256      {digest}")
    print(f"출력         {csv_path}")
    print(f"             {outdir / 'labels_intervals.csv'}  (강사용)")
    print(f"             {outdir / 'labels_rowwise.csv'}    (강사용, 채점용)")

    (outdir / "생성정보.json").write_text(json.dumps({
        "생성일시": datetime.now().isoformat(timespec="seconds"),
        "시드": seed,
        "일주기변동": not args.no_diurnal,
        "행수": int(len(df)),
        "기간": [str(df["timestamp"].min()), str(df["timestamp"].max())],
        "sha256": digest,
        "컬럼": COLUMNS,
        "이상": [{k: (v.isoformat() if isinstance(v, datetime) else v)
                 for k, v in L.items()} for L in labels],
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
