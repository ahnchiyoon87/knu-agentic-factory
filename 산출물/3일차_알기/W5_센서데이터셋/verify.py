"""W5 데이터셋 검증.

만들어진 CSV 가 실제로 Day 3 실습을 성립시키는지 확인한다.
파일이 있다는 것과 학습이 성립한다는 것은 다르다.

견적서 W5 설계 요건:
    "정상 구간에 가우시안 노이즈 포함 — 단순 임계값으로 전부 잡히면
     Lab 3-2 의 오탐·미탐 학습이 성립하지 않음"

리서치 주제 3 의 가설:
    (a) 점진 드리프트 → 이동평균이 적응해 z-score 가 커지지 않아 미탐
    (b) 순간 스파이크 → point anomaly 로 z-score 에 쉽게 잡히나 임계를 낮추면 오탐 급증
    (c) 결측 → std 계산에서 NaN 전파로 통계 자체가 깨짐

그래서 Lab 3-2 학생이 짤 바로 그 알고리즘(이동 윈도 z-score)을 여기서 돌려
세 가설이 데이터에서 실제로 재현되는지 본다.

    python verify.py
"""

from __future__ import annotations

# ── 한글 윈도우(cp949)에서 출력이 깨져 죽는 것을 막는다 ──────────────────
#    학생 PC 기본 콘솔은 cp949 라 `—` `→` 같은 글자에서 UnicodeEncodeError 가 난다.
#    리허설은 PYTHONUTF8=1 로 돌아가 이 문제가 안 보인다. 학생은 그냥 실행한다.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────────────────

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "데이터"
W1_CONFIG = ROOT.parents[1] / "0_공통" / "W1_팩토리시뮬레이터" / "config"

COLUMNS = ["equipment_id", "timestamp", "temperature", "vibration", "rpm", "run_state"]

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'통과' if ok else '실패'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def rolling_z(series: pd.Series, window: int) -> pd.Series:
    """Lab 3-2 학생이 구현할 이동 윈도 z-score. TODO 3곳이 채워진 형태."""
    mean = series.rolling(window, min_periods=window).mean()
    std = series.rolling(window, min_periods=window).std()
    return (series - mean) / std.replace(0, np.nan)


def main() -> int:
    csv = DATA / "sensor_readings_7days.csv"
    if not csv.exists():
        print(f"{csv} 가 없습니다. 먼저 python generate.py 를 실행하세요.")
        return 2

    df = pd.read_csv(csv, parse_dates=["timestamp"])
    lab = pd.read_csv(DATA / "labels_rowwise.csv", parse_dates=["timestamp"])
    iv = pd.read_csv(DATA / "labels_intervals.csv")
    info = json.loads((DATA / "생성정보.json").read_text(encoding="utf-8"))
    profile = json.loads((W1_CONFIG / "sim_profile.json").read_text(encoding="utf-8"))

    t_hi = float(profile["alarm"]["temp_high_c"])
    v_hi = float(profile["alarm"]["vibration_high_mm_s"])

    print("=" * 74)
    print("W5 데이터셋 검증")
    print("=" * 74)

    # ---------------------------------------------------------------- 1. 스키마
    print("\n1. 교안 부록 A 스키마 · 규모")
    check("컬럼이 6개, 순서까지 일치", list(df.columns) == COLUMNS, ", ".join(df.columns))
    check("행 수 약 6만", 59000 <= len(df) <= 62000, f"{len(df):,}행")
    check("설비 6대 EQ-01~EQ-06", sorted(df["equipment_id"].unique()) ==
          [f"EQ-0{i}" for i in range(1, 7)])
    step = df[df["equipment_id"] == "EQ-01"]["timestamp"].diff().dropna().dt.total_seconds()
    check("1분 간격", set(step.unique()) == {60.0}, f"{sorted(set(step.unique()))[:3]}")
    span = (df["timestamp"].max() - df["timestamp"].min())
    check("7일치", 6.9 <= span.total_seconds() / 86400 <= 7.0, str(span))

    # ---------------------------------------------------- 2. W1 실시간 스트림 정합
    print("\n2. W1 시뮬레이터 실시간 스트림과 동일 스키마인가")
    w1_sql = (ROOT.parents[1] / "0_공통" / "W1_팩토리시뮬레이터" / "db" / "migrations"
              / "002_views_functions.sql").read_text(encoding="utf-8")
    view_cols = [c.strip().strip('"') for c in
                 w1_sql.split("create or replace view sensor_readings_csv as")[1]
                 .split("from")[0].replace("select", "").split(",")]
    check("W1 sensor_readings_csv 뷰와 컬럼 일치", view_cols == COLUMNS, ", ".join(view_cols))

    layout = json.loads((W1_CONFIG / "layout.json").read_text(encoding="utf-8"))
    ambient = float(profile["thermal"]["ambient_c"])
    gain = float(profile["thermal"]["gain"])
    expo = float(profile["thermal"]["rpm_exponent"])
    ok_base = True
    detail = []
    for eq in layout["equipment"]:
        expected = ambient + gain * (float(eq["nominal_rpm"]) / 1000.0) ** expo
        actual = df[(df["equipment_id"] == eq["equipment_id"]) &
                    (df["run_state"] == "RUN")]["temperature"].median()
        detail.append(f"{eq['equipment_id']} {actual:.1f}(기대 {expected:.1f})")
        if abs(actual - expected) > 1.2:
            ok_base = False
    check("설비별 정상 온도가 W1 물리식과 일치", ok_base, " · ".join(detail))

    # ---------------------------------------------------------- 3. 이상 3종 존재
    print("\n3. 삽입 이상 3종 (교안 부록 A)")
    kinds = set(iv["kind"])
    check("3종 전부 존재", kinds == {"temp_drift", "vibration_spike", "sensor_dropout"},
          ", ".join(sorted(kinds)))
    for _, r in iv.iterrows():
        print(f"        {r['equipment_id']} {r['kind']:16s} {r['start'][5:16]} ~ {r['end'][5:16]}")

    drift = iv[iv["kind"] == "temp_drift"].iloc[0]
    seg = df[(df["equipment_id"] == drift["equipment_id"]) &
             (df["timestamp"] >= drift["start"]) & (df["timestamp"] <= drift["end"])]
    rise = seg["temperature"].tail(30).mean() - seg["temperature"].head(30).mean()
    check("EQ-03 드리프트 총 상승 약 +2.0℃ (62→64)", 1.4 <= rise <= 2.6, f"{rise:+.2f}℃")

    check("EQ-01 결측 120행", int(df["temperature"].isna().sum()) == 120,
          f"{int(df['temperature'].isna().sum())}행")

    # -------------------------------------- 4. 고정 임계값으로는 못 잡는다 (Day 1)
    print("\n4. 고정 임계값의 한계 — Day 1 서사가 데이터에서 성립하는가")
    over_t = int((df["temperature"] > t_hi).sum())
    check(f"온도가 {t_hi}℃ 를 넘은 적이 한 번도 없음", over_t == 0, f"{over_t}행")
    drift_max = seg["temperature"].max()
    check("드리프트 구간 최고 온도도 임계 미만", drift_max < t_hi, f"{drift_max:.2f}℃")

    spike_rows = lab[lab["anomaly_kind"] == "vibration_spike"]
    sv = df.merge(spike_rows[["equipment_id", "timestamp"]], on=["equipment_id", "timestamp"])
    check(f"진동 스파이크도 고정 임계 {v_hi}mm/s 를 못 넘음",
          sv["vibration"].max() < v_hi, f"최고 {sv['vibration'].max():.2f} mm/s")

    lowered = int((df["temperature"] > 66).sum())
    machines = df[df["temperature"] > 66]["equipment_id"].nunique()
    check("임계를 66℃ 로 낮추면 다른 설비들이 대량 오탐 — 슬라이드 문장이 성립",
          lowered > 5000 and machines >= 2, f"{lowered:,}행 · 설비 {machines}대")

    # ------------------------------ 5. 이동 윈도 z-score (Lab 3-2 학생 알고리즘)
    print("\n5. 이동 윈도 z-score 로 돌려본 결과 — Day 3 학습이 성립하는가")
    W = 60          # 60분 윈도
    res = {}
    for eid, g in df.groupby("equipment_id"):
        g = g.sort_values("timestamp").reset_index(drop=True)
        z = rolling_z(g["temperature"], W)
        zv = rolling_z(g["vibration"], W)
        res[eid] = (g, z, zv)

    # (a) 드리프트는 미탐되는가
    #     "구간 최대 |z| < 3" 으로 보면 안 된다. 241개 샘플이면 노이즈만으로도
    #     |z|>3 이 한두 개 나온다. 판정 기준은 "정상 구간과 구별되는가"여야 한다.
    g3, z3, _ = res["EQ-03"]
    in_drift = (g3["timestamp"] >= pd.Timestamp(drift["start"])) &                (g3["timestamp"] <= pd.Timestamp(drift["end"]))
    normal3 = (~in_drift) & z3.notna()
    m_drift, m_norm = z3[in_drift].abs().mean(), z3[normal3].abs().mean()
    r_drift = float((z3[in_drift].abs() > 3).mean())
    r_norm = float((z3[normal3].abs() > 3).mean())
    check("(a) 드리프트 구간의 z-score 가 정상 구간과 사실상 구별되지 않는다 — 이동평균이 적응",
          m_drift < 1.5 and m_drift - m_norm < 0.5,
          f"평균 |z| 드리프트 {m_drift:.2f} vs 정상 {m_norm:.2f}")
    check("(a') k=3 탐지율도 정상 구간 오탐율과 같은 수준 — 즉 미탐된다",
          r_drift < 0.02 and r_norm < 0.02,
          f"탐지율 {r_drift*100:.2f}% vs 정상 오탐율 {r_norm*100:.2f}%")

    # (b) 스파이크는 잡히는가
    g5, _, zv5 = res["EQ-05"]
    sp_ts = set(spike_rows["timestamp"])
    is_sp = g5["timestamp"].isin(sp_ts)
    zs = zv5[is_sp].abs()
    tail = zv5[~is_sp].abs().max()
    check("(b) 스파이크 3회 모두 k=3 에서 정탐 — point anomaly",
          bool((zs > 3.0).all()), "|z| = " + ", ".join(f"{v:.1f}" for v in zs))
    check("(b'') 스파이크가 노이즈 꼬리와 분리된다 — 서로 가리지 않게 윈도보다 넓게 배치",
          zs.min() > tail, f"스파이크 최소 |z| {zs.min():.2f} > 정상 최대 |z| {tail:.2f}")

    # (b') 임계를 낮추면 오탐이 급증하는가
    fp3 = fp2 = 0
    for eid, (g, z, zv) in res.items():
        truth = lab[(lab["equipment_id"] == eid)].set_index("timestamp")["is_anomaly"]
        t = g["timestamp"].map(truth).fillna(0).to_numpy()
        for k, acc in ((3.0, "3"), (2.0, "2")):
            hit = ((z.abs() > k) | (zv.abs() > k)).fillna(False).to_numpy()
            fp = int(((hit) & (t == 0)).sum())
            if acc == "3":
                fp3 += fp
            else:
                fp2 += fp
    check("(b') 임계를 k=3 → k=2 로 낮추면 오탐이 크게 는다",
          fp2 > fp3 * 1.5, f"오탐 k=3 {fp3:,}행 → k=2 {fp2:,}행 ({fp2/max(1,fp3):.1f}배)")

    # (c) 결측이 통계를 깨뜨리는가
    g1, z1, _ = res["EQ-01"]
    drop = iv[iv["kind"] == "sensor_dropout"].iloc[0]
    d_end = pd.Timestamp(drop["end"])
    after = (g1["timestamp"] > d_end) & (g1["timestamp"] <= d_end + pd.Timedelta(minutes=W))
    nan_after = int(z1[after].isna().sum())
    check("(c) 결측 뒤 윈도가 회복될 때까지 z-score 가 NaN — 결측 처리 TODO 가 필요해진다",
          nan_after > 0, f"결측 종료 후 {W}분 중 {nan_after}행이 NaN")

    # 정지 구간이 오탐 원인이 되는가 (run_state 를 봐야 한다는 교훈)
    stop_fp = 0
    for eid, (g, z, zv) in res.items():
        stopped = (g["run_state"] == "STOP").to_numpy()
        hit = ((z.abs() > 3.0) | (zv.abs() > 3.0)).fillna(False).to_numpy()
        stop_fp += int((hit & stopped).sum())
    n_stop = int((df["run_state"] == "STOP").sum())
    if n_stop:
        check("정지 구간을 거르지 않으면 오탐이 생긴다 — run_state 를 봐야 한다",
              stop_fp > 0, f"정지 구간 오탐 {stop_fp:,}행")
    else:
        print(f"  [해당없음] 정지 구간 없음 — config.json stops.per_machine_per_day = 0 "
              f"(전이 아티팩트가 스파이크를 덮어 기본값을 0 으로 둠)")

    # -------------------------------------------------------------- 6. 재현성
    print("\n6. 재현성")
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    check("생성정보의 SHA-256 과 일치", digest == info["sha256"], digest[:16] + "…")
    check("시드 고정 기록됨", info["시드"] is not None, f"seed={info['시드']}")

    # -------------------------------------------------------------- 7. 적재 형식
    print("\n7. Lab 3-1 적재 형식")
    raw = csv.read_text(encoding="utf-8").splitlines()
    check("헤더가 교안 부록 A 그대로", raw[0] == ",".join(COLUMNS), raw[0])
    check("결측은 빈 값으로 표기(NULL 적재)", any(",,," in ln for ln in raw),
          "예: " + next((ln for ln in raw if ",,," in ln), "")[:60])
    check("타임스탬프 ISO 8601", raw[1].split(",")[1].count("-") == 2
          and "T" in raw[1].split(",")[1], raw[1].split(",")[1])

    print("\n" + "=" * 74)
    if failures:
        print(f"실패 {len(failures)}건: " + ", ".join(failures))
        return 1
    print("전 항목 통과 — Day 3 실습이 이 데이터 위에서 성립합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
