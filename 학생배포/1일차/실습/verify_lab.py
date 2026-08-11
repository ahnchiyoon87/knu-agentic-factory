"""1일차 실습 뼈대 검증 — 코드 쪽 품질 게이트.

"파일이 있다"와 "50분 실습이 성립한다"는 다르다.
1일차가 가르치려는 것이 이 뼈대 + 7일치 데이터 위에서 실제로 재현되는지 확인한다.

교안 Step 2 — "심어둔 이상 3곳 중 몇 개를 잡아내는지 확인하고,
              임계값을 이리저리 조정해 보면서 정탐과 오탐을 직접 겪습니다."
리서치 주제3 — 드리프트는 이동평균이 적응해 미탐, 스파이크는 정탐,
              임계를 낮추면 오탐 급증, 결측은 통계를 깨뜨림.

    python verify_lab.py
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

import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent


def 데이터폴더() -> Path:
    """run.py 와 같은 규칙으로 찾는다 — 배포본(`데이터/`)과 강사본 둘 다."""
    for base in (ROOT, *list(ROOT.parents)[:3]):
        for cand in (base / "데이터", base / "백스테이지" / "센서데이터" / "데이터"):
            if (cand / "sensor_readings_7days.csv").is_file():
                return cand
    return ROOT.parents[1] / "데이터"


DATA = 데이터폴더()
sys.path.insert(0, str(ROOT))

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'통과' if ok else '실패'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def run_impl(mod, k: float, window: int = 60):
    df = pd.read_csv(DATA / "sensor_readings_7days.csv", parse_dates=["timestamp"])
    labels = pd.read_csv(DATA / "labels_rowwise.csv", parse_dates=["timestamp"])
    hits = set()
    for eid, g in df.groupby("equipment_id"):
        g = g.sort_values("timestamp").reset_index(drop=True)
        for col in ("temperature", "vibration"):
            vals = [None if pd.isna(v) else float(v) for v in g[col]]
            for ts, f in zip(g["timestamp"], mod.detect(vals, window=window, k=k)):
                if f:
                    hits.add((eid, ts))

    lab_idx = labels.set_index(["equipment_id", "timestamp"])["is_anomaly"]
    fp = sum(1 for (e, t) in hits if not lab_idx.get((e, t), 0))
    n_normal = int((labels["is_anomaly"] == 0).sum())
    per_kind = {}
    for kind in ("temp_drift", "vibration_spike", "sensor_dropout"):
        rows = labels[labels["anomaly_kind"] == kind]
        n_hit = sum(1 for r in rows.itertuples() if (r.equipment_id, r.timestamp) in hits)
        per_kind[kind] = (n_hit, len(rows))
    return per_kind, fp, fp / n_normal


def main() -> int:
    print("=" * 74)
    print("1일차 실습 뼈대 검증")
    print("=" * 74)

    # ------------------------------------------------------------ 1. 뼈대
    print("\n1. 뼈대 — 학생이 처음 실행했을 때")
    import detect as skeleton
    raised = []
    for fn, args in ((skeleton.window_stats, ([1.0] * 70, 65, 60)),
                     (skeleton.is_anomaly, (1.0, 0.0, 1.0, 3.0)),
                     (skeleton.handle_missing, ([1.0, None],))):
        try:
            fn(*args)
            raised.append(False)
        except NotImplementedError:
            raised.append(True)
        except Exception:
            raised.append(False)
    check("TODO 3군데가 모두 NotImplementedError 로 막혀 있다", all(raised),
          f"{sum(raised)}/3")

    r = subprocess.run([sys.executable, "run.py"], capture_output=True, text=True,
                       cwd=ROOT, encoding="utf-8", errors="replace")
    check("빈 뼈대로 실행하면 무엇을 채워야 하는지 알려준다",
          "TODO" in r.stdout and r.returncode == 1,
          (r.stdout.strip().splitlines() or ["(출력 없음)"])[-1][:60])

    # ------------------------------------------------------- 2. 참고 정답
    print("\n2. 참고 정답으로 돌렸을 때 — 교안이 가르치려는 것이 재현되는가")
    sys.path.insert(0, str(ROOT / "정답"))
    import importlib
    ans = importlib.import_module("정답.detect_answer")

    t0 = time.time()
    k3, fp3, base3 = run_impl(ans, 3.0)
    elapsed = time.time() - t0
    check("60,480행 처리가 실습에 쓸 만한 시간 안에 끝난다", elapsed < 20,
          f"{elapsed:.1f}초")

    hit, tot = k3["vibration_spike"]
    check("(b) 진동 스파이크는 k=3 에서 전부 잡힌다", hit == tot, f"{hit}/{tot}")

    hit, tot = k3["temp_drift"]
    rate = hit / tot
    check("(a) 온도 드리프트는 노이즈 수준으로만 울린다 — 이동평균이 적응",
          rate < base3 * 3, f"구간 {rate*100:.1f}% vs 기준선 {base3*100:.2f}%")

    # ------------------------------------------------- 3. 임계값 트레이드오프
    print("\n3. 임계값을 바꾸면 — Step 2 의 '정탐과 오탐을 직접 겪는다'")
    k2, fp2, base2 = run_impl(ans, 2.0)
    k4, fp4, base4 = run_impl(ans, 4.0)
    print(f"        k=4.0  오탐 {fp4:6,}행   드리프트 {k4['temp_drift'][0]:3d}/{k4['temp_drift'][1]}")
    print(f"        k=3.0  오탐 {fp3:6,}행   드리프트 {k3['temp_drift'][0]:3d}/{k3['temp_drift'][1]}")
    print(f"        k=2.0  오탐 {fp2:6,}행   드리프트 {k2['temp_drift'][0]:3d}/{k2['temp_drift'][1]}")
    check("임계를 낮추면 오탐이 크게 는다", fp2 > fp3 * 5, f"{fp2/max(1,fp3):.1f}배")
    check("임계를 올리면 오탐이 준다", fp4 < fp3, f"{fp3:,} → {fp4:,}")
    check("k 를 아무리 낮춰도 드리프트는 끝내 안 잡힌다 — 미탐의 본질",
          k2["temp_drift"][0] / k2["temp_drift"][1] < base2 * 3,
          f"k=2 에서도 구간 {k2['temp_drift'][0]/k2['temp_drift'][1]*100:.1f}% vs 기준선 {base2*100:.2f}%")
    check("스파이크는 어느 k 에서도 잡힌다",
          k2["vibration_spike"][0] == k4["vibration_spike"][0] == 3, "k=2·3·4 모두 3/3")

    # ----------------------------------------------------- 4. 결측 (TODO 3)
    print("\n4. 결측 — TODO 3 이 없으면 실습이 진행되지 않는가")

    def naive_stats(values, i, window):
        """결측을 거르지 않은 구현 — TODO 3 을 안 채운 상태를 흉내낸다."""
        if i < window:
            return None
        seg = values[i - window:i]                  # None 을 그대로 둔다
        mean = sum(seg) / len(seg)                  # 여기서 터진다
        var = sum((x - mean) ** 2 for x in seg) / (len(seg) - 1)
        return mean, var ** 0.5

    vals = [1.0] * 70 + [None] * 5 + [1.0] * 10     # 74번 창에 None 이 들어 있다

    broke = False
    try:
        naive_stats(vals, 74, 60)
    except TypeError:
        broke = True
    check("결측을 거르지 않으면 통계 계산이 실제로 터진다 (TODO 3 이 필요한 이유)",
          broke, "None 이 섞인 창에서 TypeError")

    survived = ans.window_stats(vals, 74, 60)
    check("걸러내면 같은 창에서 통계가 나온다", survived is not None,
          f"평균 {survived[0]:.2f} · 표준편차 {survived[1]:.2f}" if survived else "None")

    flags = ans.detect(vals, window=60, k=3.0)
    check("결측이 끝나고 값이 돌아오는 자리에 없던 이상이 생기지 않는다",
          not any(flags[75:]), f"복귀 구간 검출 {sum(flags[75:])}건")

    hit, tot = k3["sensor_dropout"]
    check("결측 구간을 '이상'으로 볼지는 학생 선택으로 남는다 (참고 정답은 안 봄)",
          hit == 0, f"참고 정답 {hit}/{tot} — Step 3 비교 논점")

    print("\n" + "=" * 74)
    if failures:
        print(f"실패 {len(failures)}건: " + ", ".join(failures))
        return 1
    print("전 항목 통과 — 1일차 실습이 이 뼈대와 7일치 데이터 위에서 성립합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
