# -*- coding: utf-8 -*-
"""내 코드가 어디까지 됐는지 스스로 확인한다.

    uv run 점검.py              지금 상태를 짚어 준다 (답은 알려주지 않는다)
    uv run 점검.py --열기 1     ★ 시간이 다 됐을 때만. TODO 1 하나만 완성본으로 채운다

`run.py` 는 7일치 전체를 돌려 결과를 보여 주는 것이고,
이 도구는 **작은 예제로 함수 하나하나가 제대로 도는지**만 봅니다. 훨씬 빠릅니다.
"""
from __future__ import annotations

# ── 한글 윈도우(cp949)에서 출력이 깨져 죽는 것을 막는다 ──────────────────
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
import math
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

OK, NO, WARN = "  [O]", "  [ ]", "  [!]"
NAMES = {1: "window_stats", 2: "is_anomaly", 3: "handle_missing"}


# ══════════════════════════════════════════════ 검사
def _load():
    try:
        import detect
        importlib.reload(detect)
        return detect
    except SyntaxError as e:
        # 학생이 채우다 만 문법 오류 — 역추적 대신 자리를 짚어 준다.
        print(f"detect.py {e.lineno}행에 문법 오류가 있습니다 — {e.msg}")
        if e.text:
            print(f"    {e.text.rstrip()}")
        print("  괄호·따옴표·들여쓰기를 그 줄에서 확인하세요. 고치고 다시 돌리면 됩니다.")
        raise SystemExit(1)


def _아직안채움(이름: str) -> bool:
    """detect.py 소스를 읽어 그 함수 속이 비어 있는지 본다.

    전에는 `raise NotImplementedError` 를 잡아서 판정했는데, 그 줄을 없애면서
    학생이 「지울지 고칠지」 헷갈리던 것이 사라진 대신 판정 근거도 같이 사라졌다.
    이제는 **설명글(docstring)과 주석 말고 실행되는 줄이 하나도 없으면** 안 채운 것으로 본다.
    """
    import ast
    try:
        나무 = ast.parse(Path(__file__).with_name("detect.py").read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    for n in ast.walk(나무):
        if isinstance(n, ast.FunctionDef) and n.name == 이름:
            몸 = [x for x in n.body
                  if not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant)
                          and isinstance(x.value.value, str))]
            return len(몸) == 0
    return False


def 검사_1(d) -> tuple[bool, list[str]]:
    """window_stats — 앞 W개로 (평균, 표준편차)"""
    if _아직안채움("window_stats"):
        return False, ["아직 안 채웠습니다 — `여기부터 구현합니다` 주석 아래에 씁니다."]
    msg = []
    try:
        r = d.window_stats([1.0, 2.0, 3.0, 4.0, 5.0, 99.0], 5, 5)
    except NotImplementedError:
        return False, ["아직 안 채웠습니다."]
    except Exception as e:                                      # noqa: BLE001
        return False, [f"실행 중 터집니다 — {type(e).__name__}: {e}"]

    if r is None:
        return False, ["앞 5개가 다 있는데 None 이 나왔습니다. 언제 None 을 돌려줘야 하는지 다시 보세요."]
    try:
        mean, std = r
    except Exception:                                           # noqa: BLE001
        return False, [f"(평균, 표준편차) 두 개로 돌려줘야 하는데 {r!r} 가 나왔습니다."]

    ok = True
    if abs(mean - 3.0) > 1e-6:
        ok = False
        if abs(mean - 19.0) < 1e-6:
            msg.append("지금 값(99)까지 평균에 넣었습니다. 지금 값은 빼야 합니다 — 자기가 자기를 숨깁니다.")
        else:
            msg.append(f"평균이 3.0 이어야 하는데 {mean:.4f} 가 나왔습니다. 자르는 구간을 다시 보세요.")
    want = math.sqrt(2.5)                     # 표본 표준편차
    pop = math.sqrt(2.0)                      # 모표준편차
    if abs(std - want) > 1e-6:
        ok = False
        if abs(std - pop) < 1e-6:
            msg.append("표준편차를 개수로 나눴습니다. 표본 표준편차는 (개수 − 1) 로 나눕니다.")
        else:
            msg.append(f"표준편차가 {want:.4f} 여야 하는데 {std:.4f} 가 나왔습니다.")

    try:
        if d.window_stats([1.0, 2.0, 3.0], 1, 5) is not None:
            ok = False
            msg.append("앞이 모자란 자리(i < window)에서도 값을 돌려줍니다. 그때는 None 이어야 합니다.")
    except Exception:                                           # noqa: BLE001
        ok = False
        msg.append("앞이 모자란 자리에서 터집니다. i < window 를 먼저 걸러 주세요.")
    return ok, msg


def 검사_2(d) -> tuple[bool, list[str]]:
    """is_anomaly — |z| > k"""
    if _아직안채움("is_anomaly"):
        return False, ["아직 안 채웠습니다 — `여기부터 구현합니다` 주석 아래에 씁니다."]
    try:
        d.is_anomaly(10.0, 0.0, 1.0, 3.0)
    except NotImplementedError:
        return False, ["아직 안 채웠습니다."]
    except Exception as e:                                      # noqa: BLE001
        return False, [f"실행 중 터집니다 — {type(e).__name__}: {e}"]

    ok, msg = True, []
    if not d.is_anomaly(10.0, 0.0, 1.0, 3.0):
        ok = False; msg.append("z=10 인데 이상이 아니라고 합니다. 부등호 방향을 보세요.")
    if d.is_anomaly(1.0, 0.0, 1.0, 3.0):
        ok = False; msg.append("z=1 인데 이상이라고 합니다. 부등호 방향을 보세요.")
    if not d.is_anomaly(-10.0, 0.0, 1.0, 3.0):
        ok = False; msg.append("아래로 크게 벗어난 값(z=−10)을 못 잡습니다. 절댓값을 씌우세요.")
    try:
        d.is_anomaly(5.0, 5.0, 0.0, 3.0)
    except ZeroDivisionError:
        ok = False; msg.append("표준편차가 0 인 구간에서 터집니다. 값이 한동안 똑같으면 실제로 생깁니다.")
    except Exception as e:                                      # noqa: BLE001
        ok = False; msg.append(f"표준편차 0 에서 터집니다 — {type(e).__name__}")
    return ok, msg


def 검사_3(d) -> tuple[bool, list[str]]:
    """handle_missing — 방침은 자유, 형태만 본다"""
    if _아직안채움("handle_missing"):
        return False, ["아직 안 채웠습니다 — `여기부터 구현합니다` 주석 아래에 씁니다."]
    src = [1.0, 2.0, None, 4.0, None, None, 7.0]
    try:
        out = d.handle_missing(list(src))
    except NotImplementedError:
        return False, ["아직 안 채웠습니다."]
    except Exception as e:                                      # noqa: BLE001
        return False, [f"실행 중 터집니다 — {type(e).__name__}: {e}"]

    ok, msg = True, []
    if not isinstance(out, list):
        return False, [f"리스트를 돌려줘야 하는데 {type(out).__name__} 이 나왔습니다."]
    if len(out) != len(src):
        ok = False
        msg.append(f"길이가 달라졌습니다 ({len(src)} → {len(out)}). "
                   "값을 빼 버리면 시각이 밀려 엉뚱한 자리를 가리키게 됩니다.")
    if len(out) != len(src):
        return ok, msg          # 길이가 틀리면 방침 판정은 무의미하다
    남은결측 = sum(1 for v in out if v is None)
    if 남은결측 == 3:
        msg.append("고른 방침 — 결측을 그대로 둡니다. 그 구간은 판정하지 않게 됩니다. 괜찮습니다.")
    elif 남은결측 == 0:
        msg.append("고른 방침 — 결측을 전부 메웠습니다. 무엇으로 메웠는지 말할 수 있어야 합니다.")
    else:
        msg.append(f"고른 방침 — 일부만 메웠습니다(남은 결측 {남은결측}개). 의도한 것이면 괜찮습니다.")
    return ok, msg




def 열기(n: int) -> int:
    """★ 마지막 수단 — 함수 하나만 완성본으로 채운다."""
    ans = ROOT / "정답" / "detect_answer.py"
    if not ans.is_file():
        print(f"완성본을 못 찾았습니다: {ans}")
        return 1
    name = NAMES[n]
    src = ans.read_text(encoding="utf-8")
    m = re.search(rf"^def {name}\(.*?(?=^def |\Z)", src, re.S | re.M)
    if not m:
        print(f"완성본에서 {name} 을 못 찾았습니다.")
        return 1
    새함수 = m.group(0).rstrip() + "\n"

    tgt = ROOT / "detect.py"
    bak = ROOT / "detect_내가짠것.py"
    if not bak.is_file():
        shutil.copyfile(tgt, bak)
        print(f"지금까지 쓴 것을 {bak.name} 로 남겨 뒀습니다.")

    cur = tgt.read_text(encoding="utf-8")

    # 완성본이 쓰는 모듈이 detect.py 에 없으면 같이 넣는다 (없으면 NameError 로 또 막힌다)
    NL = chr(10)
    for mod in ("math",):
        if re.search(rf"{mod}\.", 새함수) and not re.search(rf"^import {mod}$", cur, re.M):
            anchor = "from __future__ import annotations" + NL
            add = NL + f"import {mod}" + NL
            cur = (cur.replace(anchor, anchor + add, 1) if anchor in cur
                   else f"import {mod}" + NL + cur)
            print(f"  (완성본이 쓰는 import {mod} 를 함께 넣었습니다)")

    m2 = re.search(rf"^def {name}\(.*?(?=^# =====|^def |\Z)", cur, re.S | re.M)
    if not m2:
        print(f"detect.py 에서 {name} 을 못 찾았습니다. 함수 이름을 바꾸지 마세요.")
        return 1
    tgt.write_text(cur[:m2.start()] + 새함수 + "\n\n" + cur[m2.end():], encoding="utf-8")

    print(f"\n  TODO {n} ({name}) 만 완성본으로 채웠습니다. 나머지는 그대로입니다.")
    print("  이어서 —  uv run 점검.py")
    print("  되돌리려면 detect_내가짠것.py 를 detect.py 로 복사하세요.\n")
    print("  ※ 채운 함수를 한 번 읽어 보세요. 내가 막혔던 자리가 어디였는지 보입니다.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="내 코드 점검")
    ap.add_argument("--열기", type=int, choices=[1, 2, 3], metavar="TODO번호")
    args = ap.parse_args()

    if args.열기:
        return 열기(args.열기)

    d = _load()
    결과 = [검사_1(d), 검사_2(d), 검사_3(d)]
    통과 = sum(1 for ok, _ in 결과 if ok)

    print("=" * 62)
    print(f"내 코드 점검   —   3개 중 {통과}개 통과")
    print("=" * 62)
    막힌곳 = None
    for i, (ok, msgs) in enumerate(결과, 1):
        print(f"\n{OK if ok else NO} TODO {i} · {NAMES[i]}")
        for m in msgs:
            print(f"       {m}")
        if not ok and 막힌곳 is None:
            막힌곳 = i

    print()
    if 통과 == 3:
        print("  세 개 다 됐습니다.  이제 —  uv run run.py")
        print("  숫자를 적어 두고,  --k 2.0  --k 4.0  --window 30  으로 흔들어 보세요.")
        return 0

    else:
        print(f"  다음에 볼 곳 — TODO {막힌곳}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
