"""1일차 실습 Step 2 — 내 구현을 7일치 데이터에 돌려 본다.

    python run.py                 기본 (윈도 60분, 임계 k=3.0)
    python run.py --k 2.0         임계값을 낮춰서 — 오탐이 얼마나 느는가
    python run.py --window 30     윈도를 짧게
    python run.py --impl 정답     참고 구현으로 (강사용)

심어 둔 이상은 세 가지입니다. 몇 개를 잡아냈는지, 그리고 그 대가로
아닌 것을 몇 개나 잡았는지(오탐) 함께 봅니다.
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

import argparse
import importlib
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent


def 데이터폴더() -> Path:
    """센서 데이터 폴더를 찾는다 — 위로 올라가며 두 자리를 다 본다.

    나눠 준 실습 저장소는 `데이터/`, 강사 저장소는 `백스테이지/센서데이터/데이터/` 에 둔다.
    어느 쪽에서 실행하든 이 파일을 고치지 않아도 돌아가야 한다.
    """
    for base in (ROOT, *list(ROOT.parents)[:3]):
        for cand in (base / "데이터", base / "백스테이지" / "센서데이터" / "데이터"):
            if (cand / "sensor_readings_7days.csv").is_file():
                return cand
    return ROOT.parents[1] / "데이터"          # 못 찾았을 때 안내에 쓸 경로


DATA = 데이터폴더()


def load():
    csv = DATA / "sensor_readings_7days.csv"
    lab = DATA / "labels_rowwise.csv"
    if not csv.exists():
        sys.exit(f"센서 데이터를 못 찾았습니다.\n"
                 f"  찾아본 곳: {DATA}\n"
                 f"  실습 저장소를 통째로 내려받았는지 확인하세요 (「데이터」 폴더가 같이 옵니다).")
    df = pd.read_csv(csv, parse_dates=["timestamp"])
    labels = pd.read_csv(lab, parse_dates=["timestamp"])
    return df, labels


def main() -> int:
    ap = argparse.ArgumentParser(description="이상감지 실행 — 내 구현을 7일치에 돌린다")
    ap.add_argument("--window", type=int, default=60, help="이동 윈도 크기(분)")
    ap.add_argument("--k", type=float, default=3.0, help="임계값")
    ap.add_argument("--impl", default="detect", help="detect | 정답")
    args = ap.parse_args()

    mod_name = "detect" if args.impl == "detect" else "정답.detect_answer"
    try:
        mod = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        sys.exit(f"{mod_name} 을(를) 찾지 못했습니다.")

    df, labels = load()
    truth = labels.set_index(["equipment_id", "timestamp"])["is_anomaly"]

    print("=" * 74)
    print(f"이상감지 실행  윈도 {args.window}분 · 임계 k={args.k} · 구현 {args.impl}")
    print("=" * 74)

    t0 = time.time()
    hits: dict[tuple[str, pd.Timestamp], bool] = {}
    try:
        for eid, g in df.groupby("equipment_id"):
            g = g.sort_values("timestamp").reset_index(drop=True)
            for col in ("temperature", "vibration"):
                vals = [None if pd.isna(v) else float(v) for v in g[col]]
                flags = mod.detect(vals, window=args.window, k=args.k)
                if len(flags) != len(vals):
                    sys.exit(f"detect() 가 길이 {len(flags)} 를 돌려줬습니다. {len(vals)} 여야 합니다.")
                for ts, f in zip(g["timestamp"], flags):
                    if f:
                        hits[(eid, ts)] = True
    except NotImplementedError as e:
        print(f"\n  아직 채우지 않은 TODO 가 있습니다 — {e}")
        print("  detect.py 의 TODO 세 군데를 채운 뒤 다시 실행하세요.")
        return 1
    except ZeroDivisionError:
        print("\n  0 으로 나눴습니다. 표준편차가 0 인 구간을 어떻게 다룰지 정하세요 (TODO 2).")
        return 1
    except TypeError as e:
        print(f"\n  값이 없는 자리(None)를 계산에 넣은 것 같습니다 — {e}")
        print("  결측 처리를 먼저 정하세요 (TODO 3).")
        return 1
    elapsed = time.time() - t0

    # ---------------------------------------------------------------- 채점
    detected = pd.Series(
        [1 if (r.equipment_id, r.timestamp) in hits else 0 for r in df.itertuples()],
        index=pd.MultiIndex.from_arrays([df["equipment_id"], df["timestamp"]]),
    )
    y = truth.reindex(detected.index).fillna(0).astype(int)

    tp = int(((detected == 1) & (y == 1)).sum())
    fp = int(((detected == 1) & (y == 0)).sum())
    fn = int(((detected == 0) & (y == 1)).sum())

    n_normal = int((y == 0).sum())
    base = fp / n_normal if n_normal else 0.0      # 정상 구간에서 잘못 울린 비율

    print(f"\n총 {len(df):,}행 · {elapsed:.1f}초 소요")
    print(f"정상 구간에서 잘못 울린 비율(기준선) {base * 100:.2f}%\n")

    print("심어 둔 이상 3종을 잡았는가")
    print("-" * 74)
    caught = 0
    for kind, name in (("temp_drift", "온도 드리프트 (EQ-03, 5일차 새벽 3시~7시)"),
                       ("vibration_spike", "진동 스파이크 (EQ-05, 3일차)"),
                       ("sensor_dropout", "센서 결측 (EQ-01, 6일차 2시간)")):
        rows = labels[labels["anomaly_kind"] == kind]
        n_hit = sum(1 for r in rows.itertuples() if (r.equipment_id, r.timestamp) in hits)
        rate = n_hit / len(rows) if len(rows) else 0.0

        # 구간 안에서 울린 비율이 기준선의 3배를 넘어야 '잡았다'고 본다.
        # 넘지 못하면 노이즈로 우연히 울린 것과 구별되지 않는다.
        if n_hit == 0:
            verdict, mark = "못 잡음", "  "
        elif rate < base * 3:
            verdict, mark = "노이즈 수준 — 못 잡은 것과 같다", "~ "
        else:
            verdict, mark = "잡음", "O "
            caught += 1

        print(f"  [{mark}] {name}")
        print(f"         {len(rows)}개 중 {n_hit}개 ({rate * 100:.1f}%) → {verdict}")

    print("-" * 74)
    print(f"  분명하게 잡은 것: 3종 중 {caught}종")

    per_day = fp / 7
    print(f"\n대가 — 아닌데 울린 것 {fp:,}행")
    print(f"       7일 · 설비 6대 기준 하루 약 {per_day:.0f}번")
    if per_day > 20:
        print("       이 정도면 현장에서는 아무도 알람을 안 봅니다.")

    print("\n" + "=" * 74)
    print("해 볼 것 — 임계값을 바꾸면 어떻게 달라지는가")
    print("    python run.py --k 2.0     낮추면 더 잡히지만 오탐이 는다")
    print("    python run.py --k 4.0     올리면 오탐이 줄지만 놓치는 게 는다")
    print("    python run.py --window 30 윈도를 짧게 하면?")
    print("\n온도 드리프트가 안 잡힌다면 — 그게 정상입니다. 왜 그런지 생각해 보세요.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    sys.exit(main())
