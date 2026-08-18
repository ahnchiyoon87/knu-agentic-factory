# -*- coding: utf-8 -*-
"""내 도구가 어디까지 됐는지 스스로 확인한다.

    uv run 점검.py              지금 상태를 짚어 준다 (답은 알려주지 않는다)
    uv run 점검.py --정답 1     ★ 막혔을 때. 그 도구 자리만 정답으로 채운다

`mcp_server.py --check` 는 서버 없이 도구를 한 번 불러 보는 것이고,
이 도구는 **연결 상태부터 도구 응답 모양까지** 순서대로 짚어 줍니다.
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
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

OK, NO = "  [O]", "  [ ]"
NAMES = {1: "detect_anomaly", 2: "query_equipment"}


def _빈함수(경로: Path, 이름들: tuple[str, ...]) -> list[str]:
    """소스를 읽어 **속이 빈** 함수 이름을 돌려준다.

    전에는 `raise NotImplementedError` 를 잡아서 판정했는데, 그 줄을 없애면서
    학생이 「지울지 고칠지」 헷갈리던 것이 사라진 대신 판정 근거도 같이 사라졌다.
    이제는 **설명글(docstring)과 주석 말고 실행되는 줄이 하나도 없으면** 안 채운 것으로 본다.

    ※ `mcp_server.py` 의 `안채운도구()` 와 같은 규칙이다. 두 곳이 어긋나면 판정이 거짓말이 된다.
    """
    import ast

    try:
        나무 = ast.parse(경로.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []                       # 없거나 깨진 파일은 부르는 쪽이 따로 짚어 준다
    빈것 = []
    for n in ast.walk(나무):
        if isinstance(n, ast.FunctionDef) and n.name in 이름들:
            if any(isinstance(x, ast.Constant) and x.value is Ellipsis
                   for x in ast.walk(n)):
                빈것.append(n.name); continue
            몸 = [x for x in n.body
                  if not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant)
                          and isinstance(x.value.value, str))]
            if not 몸:
                빈것.append(n.name)
    return 빈것


# ══════════════════════════════════════════════ 0. 준비 상태
def _csv_경로(fb: dict) -> Path:
    """mcp_server.py 의 _csv_경로() 와 같은 규칙. 두 곳이 어긋나면 판정이 거짓말이 된다."""
    설정 = str(fb.get("csv_path", "auto")).strip()
    if 설정 and 설정 != "auto":
        return (ROOT / 설정).resolve()
    for base in (ROOT, *list(ROOT.parents)[:5]):
        for cand in (base / "데이터", base / "제작" / "검증도구" / "센서데이터" / "데이터"):
            if (cand / "sensor_readings_7days.csv").is_file():
                return cand / "sensor_readings_7days.csv"
    return ROOT.parents[2] / "데이터" / "sensor_readings_7days.csv"


def 검사_설정() -> tuple[bool, list[str]]:
    msg = []
    p = ROOT / "config.json"
    if not p.is_file():
        return False, ["config.json 이 없습니다."]
    try:
        c = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:                                       # noqa: BLE001
        return False, [f"config.json 이 깨졌습니다 — {e}. 쉼표나 따옴표를 확인하세요."]

    ok = True
    if c.get("data_source") != "fallback":
        ok = False
        msg.append(f'data_source 가 "{c.get("data_source")}" 입니다. "fallback" 으로 두세요.')
    fb = c.get("fallback", {})
    # `mcp_server.py` 는 환경변수(SHARED_API·W6_TENANT)를 먼저 본다. 여기가 config.json 만
    # 보면 **도구는 붙는데 점검만 「서버에 못 닿습니다」라고 하는** 어긋남이 생긴다.
    # 실제로 리허설이 그렇게 걸렸다. 두 곳이 같은 규칙을 써야 판정이 거짓말이 안 된다.
    import os
    api = str(os.environ.get("SHARED_API") or fb.get("shared_api", ""))
    ten = str(os.environ.get("W6_TENANT") or fb.get("tenant", ""))

    # 둘 다 `내번호.py` 가 채웁니다. 학생이 손으로 적을 값이 아닙니다.
    if not api.strip() or not ten.strip():
        ok = False
        msg.append("서버 주소와 내 번호가 아직 비어 있습니다. 손으로 적지 마세요 —")
        msg.append("    cd ../../../2일차/실습  →  uv run 내번호.py")
        msg.append("    (2일차에 이미 돌렸으면 그냥 다시 치면 됩니다. 같은 번호가 나옵니다)")
    else:
        if not api.startswith("http"):
            ok = False
            msg.append(f"fallback.shared_api 가 이상합니다 ({api!r}). http:// 로 시작해야 합니다.")
        if not re.fullmatch(r"S\d{2}", ten):
            ok = False
            msg.append(f"fallback.tenant 가 {ten!r} 입니다. "
                       "2일차/실습 에서 uv run 내번호.py 를 돌리면 자동으로 채워집니다.")
    # csv_path 는 기본이 "auto" 다 — mcp_server.py 와 똑같이 찾아야 판정이 어긋나지 않는다
    csv = _csv_경로(fb)
    if not csv.is_file():
        ok = False
        msg.append(f"센서 CSV 를 못 찾았습니다: {csv}\n"
                   "       실습 저장소를 통째로 내려받았는지 확인하세요 "
                   "(「데이터」 폴더가 같이 옵니다).")
    if ok:
        try:
            import httpx
            r = httpx.get(f"{api.rstrip('/')}/api/v1/{ten}/maintenance",
                          params={"limit": 1}, timeout=8)
            건수 = len(r.json().get("maintenance", r.json() if isinstance(r.json(), list) else []))
            if r.status_code != 200 or 건수 == 0:
                ok = False
                msg.append(f"서버에 닿았지만 정비 이력이 안 옵니다 (HTTP {r.status_code}). "
                           "2일차/실습 에서 uv run 내번호.py 를 다시 돌려 주소와 번호를 "
                           "새로 채우세요 — 여기가 비면 원인 추정이 안 나옵니다.")
            else:
                msg.append(f"서버 {api} · 내 번호 {ten} · 정비 이력 확인")
        except Exception as exc:                                 # noqa: BLE001
            ok = False
            msg.append(f"서버에 못 닿습니다 — {type(exc).__name__}. "
                       "2일차/실습 에서 uv run 내번호.py 를 다시 돌려 주소를 새로 "
                       "채우세요. 그래도 안 되면 손 드세요.")
    return ok, msg


def 검사_어제코드() -> tuple[bool, list[str]]:
    """2일차에 짠 detect 가 실제로 도는가 — 오늘 도구가 이걸 그대로 쓴다."""
    어제 = ROOT.parents[2] / "2일차" / "실습"
    try:
        sys.path.insert(0, str(어제))
        import detect as d
    except Exception as e:                                       # noqa: BLE001
        return False, [f"2일차에 만든 detect.py 를 못 불러옵니다 — {type(e).__name__}: {e}",
                       f"찾아본 곳: {어제}",
                       "실습 저장소의 `2일차` 폴더가 그대로 있어야 합니다 "
                       "(오늘 도구가 어제 코드를 그대로 불러 씁니다).",
                       "폴더가 없으면 손 드세요 — 다시 받아 드립니다."]
    # 안 채운 자리는 조용히 None 을 돌려준다. 그대로 부르면 엉뚱한 예외로 튀어
    # 학생이 어제 코드가 아니라 오늘 도구를 의심하게 된다 — 소스로 먼저 가른다.
    빈것 = _빈함수(어제 / "detect.py", ("window_stats", "is_anomaly", "handle_missing"))
    if 빈것:
        return False, [f"2일차의 {' · '.join(빈것)} 이(가) 아직 비어 있습니다.",
                       "`2일차/실습` 폴더에서 `uv run 점검.py` 로 먼저 끝내세요.",
                       "시간이 없으면 `uv run 점검.py --열기 1` 부터 쓰세요."]
    try:
        out = d.detect([1.0] * 70 + [99.0], window=60, k=3.0)
    except Exception as e:                                       # noqa: BLE001
        return False, [f"detect() 가 터집니다 — {type(e).__name__}: {e}"]
    if not isinstance(out, list) or len(out) != 71:
        return False, [f"detect() 가 길이 71 리스트를 돌려줘야 하는데 {type(out).__name__} 이 왔습니다."]
    return True, ["2일차에 만든 detect() 가 정상입니다."]


# ══════════════════════════════════════════════ 도구 검사
def _tools():
    import mcp_server
    return mcp_server


def 검사_1(m) -> tuple[bool, list[str]]:
    if "detect_anomaly" in _빈함수(ROOT / "mcp_server.py", ("detect_anomaly",)):
        return False, ["아직 안 채웠습니다 — 그 함수의 `...` 줄을 고칩니다."]
    fn = getattr(m, "detect_anomaly", None)
    fn = getattr(fn, "fn", fn)          # @mcp.tool() 로 감싸인 경우
    try:
        out = fn("EQ-03", hours=24)
    except Exception as e:                                       # noqa: BLE001
        return False, [f"실행 중 터집니다 — {type(e).__name__}: {e}"]

    ok, msg = True, []
    if not isinstance(out, dict):
        return False, [f"딕셔너리를 돌려줘야 하는데 {type(out).__name__} 이 왔습니다."]
    필수 = ["equipment_id", "sample_count", "anomaly_count", "anomalies"]
    빠짐 = [k for k in 필수 if k not in out]
    if 빠짐:
        ok = False
        msg.append(f"빠진 항목: {', '.join(빠짐)} — 에이전트가 이걸 보고 판단합니다.")
    if out.get("sample_count", 0) == 0:
        ok = False
        msg.append("sample_count 가 0 입니다. 데이터를 못 읽고 있습니다 — 위 설정을 다시 보세요.")
    if not isinstance(out.get("anomalies", []), list):
        ok = False
        msg.append("anomalies 는 리스트여야 합니다.")
    elif len(out.get("anomalies", [])) > 200:
        msg.append(f"anomalies 가 {len(out['anomalies'])}개입니다. 너무 길면 에이전트가 다 못 읽습니다 — 추리세요.")
    if ok:
        msg.append(f"표본 {out['sample_count']}개 · 이상 {out['anomaly_count']}건")
    return ok, msg


def 검사_2(m) -> tuple[bool, list[str]]:
    if "query_equipment" in _빈함수(ROOT / "mcp_server.py", ("query_equipment",)):
        return False, ["아직 안 채웠습니다 — 그 함수의 `...` 줄을 고칩니다."]
    fn = getattr(m, "query_equipment", None)
    fn = getattr(fn, "fn", fn)
    try:
        out = fn("EQ-03", hours=24)
    except Exception as e:                                       # noqa: BLE001
        return False, [f"실행 중 터집니다 — {type(e).__name__}: {e}"]

    ok, msg = True, []
    if not isinstance(out, dict):
        return False, [f"딕셔너리를 돌려줘야 하는데 {type(out).__name__} 이 왔습니다."]
    if "recent" not in out:
        ok = False; msg.append("recent 가 없습니다 — 최근 센서 요약이 들어가야 합니다.")
    mt = out.get("maintenance")
    if mt is None:
        ok = False
        msg.append("maintenance 가 없습니다. **정비 이력이 진단의 재료입니다.**")
    elif not mt:
        ok = False
        msg.append("정비 이력이 비어 있습니다. shared_api 주소가 맞는지 다시 보세요 — "
                   "여기가 비면 에이전트가 원인을 추정할 재료가 없습니다.")
    else:
        본문 = json.dumps(mt, ensure_ascii=False)
        if "note" not in 본문:
            ok = False
            msg.append("정비 이력에 note 가 없습니다. **원인 추정이 note 에서 나옵니다.** 빠뜨리지 마세요.")
        elif "WO-" in 본문:
            wo = re.search(r"WO-[\d-]+", 본문)
            msg.append(f"정비 이력 {len(mt)}건 · {wo.group(0) if wo else ''} 확인")
    return ok, msg




def 열기(n: int) -> int:
    """★ 마지막 수단 — 도구 하나만 완성본으로 채운다.

    2일차 `점검.py --열기` 와 같은 규칙이다 — **함수를 통째로 갈아 끼운다.**
    전에는 `raise` 줄 하나를 찾아 그 자리에 본문을 끼워 넣었는데, 그 줄을 없앤 뒤로는
    찾을 것이 사라져 **안 채운 학생에게 「이미 채워져 있습니다」라고 답했다.**
    막혀서 마지막 수단을 쓴 사람에게 정확히 반대로 답하던 자리다.
    """
    ans = ROOT / "정답" / "tool_bodies.py"
    if not ans.is_file():
        print(f"완성본을 못 찾았습니다: {ans}")
        return 1
    name = NAMES[n]
    src = ans.read_text(encoding="utf-8")
    m = re.search(rf"^def {name}\(.*?(?=^# =====|^def |\Z)", src, re.S | re.M)
    if not m:
        print(f"완성본에서 {name} 을 못 찾았습니다.")
        return 1
    새함수 = m.group(0).rstrip() + "\n"

    tgt = ROOT / "mcp_server.py"
    # 두 번 누르는 일이 흔하다. 이미 채운 것을 덮어써서 학생이 쓴 것을 지우면 안 된다.
    if name not in _빈함수(tgt, (name,)):
        print(f"  {name} 은 이미 채워져 있습니다. 다시 열 것이 없습니다.")
        print("  이어서 —  uv run 점검.py")
        return 0

    bak = ROOT / "mcp_server_내가짠것.py"
    if not bak.is_file():
        shutil.copyfile(tgt, bak)
        print(f"지금까지 쓴 것을 {bak.name} 로 남겨 뒀습니다.")

    cur = tgt.read_text(encoding="utf-8")
    # `@mcp.tool()` 데코레이터 줄은 그대로 둔다 — def 줄부터 다음 구획 앞까지만 바꾼다.
    m2 = re.search(rf"^def {name}\(.*?(?=^# =====|^@mcp\.tool|^def |\Z)", cur, re.S | re.M)
    if not m2:
        print(f"  mcp_server.py 에서 {name} 을 못 찾았습니다. 함수 이름을 바꾸지 마세요.")
        print("  파일을 크게 고쳤다면 mcp_server_내가짠것.py 로 되돌린 뒤 다시 해 보세요.")
        print("  그래도 안 되면 손 드세요.")
        return 1
    tgt.write_text(cur[:m2.start()] + 새함수 + "\n\n" + cur[m2.end():], encoding="utf-8")

    print(f"\n  도구 {n} ({name}) 만 완성본으로 채웠습니다. 나머지는 그대로입니다.")
    print("  이어서 —  uv run 점검.py")
    print("  되돌리려면 mcp_server_내가짠것.py 를 mcp_server.py 로 복사하세요.\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="내 도구 점검")
    ap.add_argument("--정답", "--열기", dest="정답", type=int, choices=[1, 2],
                    metavar="도구번호",
                    help="★ 막혔을 때. 그 도구 하나만 정답으로 채운다 "
                         "(`--열기` 는 옛 이름, 그대로 받는다)")
    args = ap.parse_args()

    if args.정답:
        return 열기(args.정답)

    print("=" * 62)
    print("내 도구 점검")
    print("=" * 62)

    설정ok, 설정msg = 검사_설정()
    print(f"\n{OK if 설정ok else NO} 0-1 · config.json")
    for m in 설정msg:
        print(f"       {m}")

    어제ok, 어제msg = 검사_어제코드()
    print(f"\n{OK if 어제ok else NO} 0-2 · 2일차에 만든 detect.py")
    for m in 어제msg:
        print(f"       {m}")

    if not (설정ok and 어제ok):
        print("\n  위 두 개를 먼저 맞춰야 도구를 검사할 수 있습니다.")
        return 1

    try:
        m = _tools()
    except Exception as e:                                       # noqa: BLE001
        print(f"\n  mcp_server.py 를 못 불러옵니다 — {type(e).__name__}: {e}")
        return 1

    결과 = [검사_1(m), 검사_2(m)]
    통과 = sum(1 for ok, _ in 결과 if ok)
    막힌곳 = None
    for i, (ok, msgs) in enumerate(결과, 1):
        print(f"\n{OK if ok else NO} 도구 {i} · {NAMES[i]}")
        for x in msgs:
            print(f"       {x}")
        if not ok and 막힌곳 is None:
            막힌곳 = i

    print(f"\n  도구 2개 중 {통과}개 통과")
    if 통과 == 2:
        print("\n  둘 다 됐습니다.  이제 —  uv run agent.py")
        print("  AI 가 이 도구들을 스스로 골라 부르는 것을 보게 됩니다.")
        return 0
    else:
        print(f"  다음에 볼 곳 — 도구 {막힌곳}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
