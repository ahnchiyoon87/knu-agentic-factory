"""2일차 실습 Step 2 — 내 구현을 7일치 데이터에 돌려 본다.

    uv run run.py                 기본 (윈도 60분, 임계 k=3.0)
    uv run run.py --k 2.0         임계값을 낮춰서 — 오탐이 얼마나 느는가
    uv run run.py --window 30     윈도를 짧게
    uv run run.py --impl 정답     참고 구현으로 (강사용)

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

    나눠 준 실습 저장소는 `데이터/`, 강사 저장소는 `제작/검증도구/센서데이터/데이터/` 에 둔다.
    어느 쪽에서 실행하든 이 파일을 고치지 않아도 돌아가야 한다.
    """
    for base in (ROOT, *list(ROOT.parents)[:4]):
        for cand in (base / "데이터", base / "제작" / "검증도구" / "센서데이터" / "데이터"):
            if (cand / "sensor_readings_7days.csv").is_file():
                return cand
    return ROOT.parents[1] / "데이터"          # 못 찾았을 때 안내에 쓸 경로


DATA = 데이터폴더()


def 안채운자리(모듈이름: str) -> list[str]:
    """소스를 읽어 **속이 빈** 함수 이름을 돌려준다.

    전에는 `raise NotImplementedError` 를 잡아서 판정했는데, 그 줄을 없애면서
    학생이 「지울지 고칠지」 헷갈리던 것이 사라진 대신 판정 근거도 같이 사라졌다.
    이제는 **설명글(docstring)과 주석 말고 실행되는 줄이 하나도 없으면** 안 채운 것으로 본다.

    ※ `점검.py` 의 `_아직안채움()` 과 같은 규칙이다. 두 곳이 어긋나면 판정이 거짓말이 된다.
    """
    import ast

    경로 = ROOT / (모듈이름.replace(".", "/") + ".py")
    try:
        나무 = ast.parse(경로.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []                    # 없거나 깨진 파일은 위에서 이미 짚었다
    빈것 = []
    for n in ast.walk(나무):
        if isinstance(n, ast.FunctionDef) and n.name in (
                "window_stats", "is_anomaly", "handle_missing"):
            몸 = [x for x in n.body
                  if not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant)
                          and isinstance(x.value.value, str))]
            if not 몸:
                빈것.append(n.name)
    return 빈것


def load():
    csv = DATA / "sensor_readings_7days.csv"
    lab = DATA / "labels_rowwise.csv"
    if not csv.exists() or not lab.exists():
        빠진것 = csv.name if not csv.exists() else lab.name
        sys.exit(f"센서 데이터를 못 찾았습니다 ({빠진것}).\n"
                 f"  찾아본 곳: {DATA}\n"
                 f"  실습 저장소를 통째로 내려받았는지 확인하세요 (「데이터」 폴더가 같이 옵니다).")
    df = pd.read_csv(csv, parse_dates=["timestamp"])
    labels = pd.read_csv(lab, parse_dates=["timestamp"])
    return df, labels


def main() -> int:
    ap = argparse.ArgumentParser(description="이상감지 실행 — 내 구현을 7일치에 돌린다")
    ap.add_argument("--window", type=int, default=60, help="이동 윈도 크기(분)")
    ap.add_argument("--k", type=float, default=3.0, help="임계값")
    ap.add_argument("--impl", default="detect", help="detect | 정답 | 파일 이름")
    args = ap.parse_args()

    # `--impl` 은 **파일 이름을 그대로** 받는다.
    #   학생은 쓸 일이 없다 (기본값 detect 로 자기 코드가 돈다).
    #   2일차 마지막 「AI 가 짠 것과 나란히」 시연에서 **강사가** 쓴다 —
    #   AI 가 만든 것을 `detect_ai.py` 로 저장하고 `--impl detect_ai` 로
    #   **같은 7일치에 태워** 학생 숫자와 나란히 놓는다.
    #   코드를 보여 주기만 하면 「AI 가 짰다」는 말만 남는다. 돌려야 입증이 된다.
    mod_name = "정답.detect_answer" if args.impl == "정답" else args.impl
    try:
        mod = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        sys.exit(f"{mod_name}.py 를 찾지 못했습니다 — `2일차/실습` 안에 있어야 합니다.")
    except SyntaxError as e:
        # 채우다 만 문법 오류 — 역추적 대신 자리를 짚어 준다.
        sys.exit(f"{mod_name}.py {e.lineno}행에 문법 오류가 있습니다 — {e.msg}\n"
                 f"  괄호·따옴표·들여쓰기를 그 줄에서 확인하세요. uv run 점검.py 도 같이 짚어 줍니다.")

    # run.py 가 부르는 것은 `detect()` 하나다. 없으면 여기서 멈춰야
    # 시연 도중 AttributeError 로 깨지지 않는다.
    if not hasattr(mod, "detect"):
        sys.exit(f"{mod_name}.py 에 detect() 가 없습니다.\n"
                 f"  detect(values, window=60, k=3.0) 이 True/False 목록을 돌려줘야 합니다.")

    # 아직 안 채운 자리가 있으면 여기서 세운다.
    # 빈 함수는 조용히 None 을 돌려주므로 그냥 돌리면 60,480줄을 돌다가 엉뚱한 데서
    # TypeError 로 터지고, 학생은 **자기가 안 짠 코드를 디버깅하려 든다.**
    빈것 = 안채운자리(mod_name)
    if 빈것:
        번호 = {"window_stats": 1, "is_anomaly": 2, "handle_missing": 3}
        적을것 = " · ".join(f"TODO {번호[x]}({x})" for x in 빈것)
        print(f"\n  아직 채우지 않은 TODO 가 있습니다 — {적을것}")
        print("  detect.py 의 「여기부터 구현합니다」 주석 아래에 씁니다.")
        print("  어디가 왜 막혔는지 —  uv run 점검.py")
        return 1

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
    print("    uv run run.py --k 2.0     낮추면 더 잡히지만 오탐이 는다")
    print("    uv run run.py --k 4.0     올리면 오탐이 줄지만 놓치는 게 는다")
    print("    uv run run.py --window 30 윈도를 짧게 하면?")
    print("\n온도 드리프트가 안 잡힌다면 — 그게 정상입니다. 왜 그런지 생각해 보세요.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    sys.exit(main())
