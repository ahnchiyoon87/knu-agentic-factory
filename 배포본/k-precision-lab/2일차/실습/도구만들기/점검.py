# -*- coding: utf-8 -*-
"""내 도구가 어디까지 됐는지 스스로 확인한다.

    python 점검.py              지금 상태를 짚어 준다 (답은 알려주지 않는다)
    python 점검.py --힌트 1     막힌 곳의 힌트 (개념)
    python 점검.py --힌트 2     막힌 곳의 힌트 (의사코드)
    python 점검.py --열기 1     ★ 시간이 다 됐을 때만. 도구 하나만 완성본으로 채운다

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


# ══════════════════════════════════════════════ 0. 준비 상태
def _csv_경로(fb: dict) -> Path:
    """mcp_server.py 의 _csv_경로() 와 같은 규칙. 두 곳이 어긋나면 판정이 거짓말이 된다."""
    설정 = str(fb.get("csv_path", "auto")).strip()
    if 설정 and 설정 != "auto":
        return (ROOT / 설정).resolve()
    for base in (ROOT, *list(ROOT.parents)[:4]):
        for cand in (base / "데이터", base / "백스테이지" / "센서데이터" / "데이터"):
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
    api = str(fb.get("shared_api", ""))
    if not api.startswith("http"):
        ok = False
        msg.append(f"fallback.shared_api 가 이상합니다 ({api!r}). http:// 로 시작해야 합니다.")
    ten = str(fb.get("tenant", ""))
    if not re.fullmatch(r"S\d{2}", ten):
        ok = False
        msg.append(f"fallback.tenant 가 {ten!r} 입니다. 쪽지의 내 번호(예: S07)로 바꾸세요.")
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
                           "shared_api 주소와 내 번호를 쪽지와 대조하세요 — "
                           "여기가 비면 원인 추정이 안 나옵니다.")
            else:
                msg.append(f"서버 {api} · 내 번호 {ten} · 정비 이력 확인")
        except Exception as exc:                                 # noqa: BLE001
            ok = False
            msg.append(f"서버에 못 닿습니다 — {type(exc).__name__}. "
                       "shared_api 주소를 쪽지와 대조하세요. 그래도 안 되면 손 드세요.")
    return ok, msg


def 검사_어제코드() -> tuple[bool, list[str]]:
    """1일차에 짠 detect 가 실제로 도는가 — 오늘 도구가 이걸 그대로 쓴다."""
    어제 = ROOT.parents[2] / "1일차" / "실습"
    try:
        sys.path.insert(0, str(어제))
        import detect as d
    except Exception as e:                                       # noqa: BLE001
        return False, [f"1일차에 만든 detect.py 를 못 불러옵니다 — {type(e).__name__}: {e}",
                       f"찾아본 곳: {어제}",
                       "실습 저장소의 `1일차` 폴더가 그대로 있어야 합니다 "
                       "(오늘 도구가 어제 코드를 그대로 불러 씁니다).",
                       "폴더가 없으면 손 드세요 — 다시 받아 드립니다."]
    try:
        out = d.detect([1.0] * 70 + [99.0], window=60, k=3.0)
    except NotImplementedError:
        return False, ["1일차 TODO 세 곳이 아직 비어 있습니다.",
                       "`1일차/실습` 폴더에서 `python 점검.py` 로 먼저 끝내세요.",
                       "시간이 없으면 `python 점검.py --열기 1` 부터 쓰세요."]
    except Exception as e:                                       # noqa: BLE001
        return False, [f"detect() 가 터집니다 — {type(e).__name__}: {e}"]
    if not isinstance(out, list) or len(out) != 71:
        return False, [f"detect() 가 길이 71 리스트를 돌려줘야 하는데 {type(out).__name__} 이 왔습니다."]
    return True, ["1일차에 만든 detect() 가 정상입니다."]


# ══════════════════════════════════════════════ 도구 검사
def _tools():
    import mcp_server
    return mcp_server


def 검사_1(m) -> tuple[bool, list[str]]:
    fn = getattr(m, "detect_anomaly", None)
    fn = getattr(fn, "fn", fn)          # @mcp.tool() 로 감싸인 경우
    try:
        out = fn("EQ-03", hours=24)
    except NotImplementedError:
        return False, ["아직 안 채웠습니다."]
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
    fn = getattr(m, "query_equipment", None)
    fn = getattr(fn, "fn", fn)
    try:
        out = fn("EQ-03", hours=24)
    except NotImplementedError:
        return False, ["아직 안 채웠습니다."]
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


힌트 = {
    1: {1: "어제 만든 detect() 를 온도와 진동에 각각 돌리고, True 로 나온 자리를 모으면 됩니다.",
        2: "rows = _fetch_readings(...) · temps = [r.get('temperature') for r in rows] · "
           "flags = detect(temps, window, k) · True 인 index 를 anomalies 에 담기"},
    2: {1: "센서 요약 하나, 정비 이력 하나. 둘을 합쳐 돌려주면 됩니다. note 를 빠뜨리지 마세요.",
        2: "rows = _fetch_readings(...) 로 평균·최대·결측 수를 계산 · "
           "mt = _fetch_maintenance(...) · return {'equipment_id':…, 'recent':…, 'maintenance': mt}"},
}


def 열기(n: int) -> int:
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

    tgt = ROOT / "mcp_server.py"
    bak = ROOT / "mcp_server_내가짠것.py"
    if not bak.is_file():
        shutil.copyfile(tgt, bak)
        print(f"지금까지 쓴 것을 {bak.name} 로 남겨 뒀습니다.")

    cur = tgt.read_text(encoding="utf-8")
    m2 = re.search(rf'(    # TODO: 여기를 채우세요\n    raise NotImplementedError\("{name} [^"]*"\)\n)',
                   cur)
    if not m2:
        # 두 번 누르는 일이 흔하다. 그때 「못 찾았습니다」만 뜨면 파일이 깨진 줄 안다.
        # 이미 채워진 것인지, 정말로 자리가 사라진 것인지를 갈라서 말해 준다.
        if f"def {name}" in cur:
            print(f"  {name} 은 이미 채워져 있습니다. 다시 열 것이 없습니다.")
            print("  이어서 —  python 점검.py")
            return 0
        print(f"  mcp_server.py 안에서 {name} 을 못 찾았습니다.")
        print("  파일을 크게 고쳤다면 mcp_server_내가짠것.py 로 되돌린 뒤 다시 해 보세요.")
        print("  그래도 안 되면 손 드세요.")
        return 1
    # 완성본은 함수 통째로(def 부터)이고, 넣을 자리는 함수 **본문 안**이다.
    # def 줄과 docstring 을 걷어내고, 남은 본문을 원래 들여쓰기(4칸)로 맞춘다.
    줄 = m.group(0).split("\n")[1:]                     # def 줄 제거
    따옴 = 줄[0].lstrip()[:3] if 줄 else ""
    if 따옴 in ('"' * 3, "'" * 3):                       # docstring 제거
        if 줄[0].lstrip().count(따옴) < 2:
            끝 = next(i for i, l in enumerate(줄[1:], 1) if 따옴 in l)
            줄 = 줄[끝 + 1:]
        else:
            줄 = 줄[1:]
    while 줄 and not 줄[0].strip():
        줄 = 줄[1:]
    들여 = min((len(l) - len(l.lstrip()) for l in 줄 if l.strip()), default=4)
    본문 = "\n".join(("    " + l[들여:]) if l.strip() else "" for l in 줄).rstrip() + "\n"
    tgt.write_text(cur[:m2.start()] + 본문 + cur[m2.end():], encoding="utf-8")

    print(f"\n  도구 {n} ({name}) 만 완성본으로 채웠습니다. 나머지는 그대로입니다.")
    print("  이어서 —  python 점검.py")
    print("  되돌리려면 mcp_server_내가짠것.py 를 mcp_server.py 로 복사하세요.\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="내 도구 점검")
    ap.add_argument("--힌트", type=int, choices=[1, 2], metavar="단계")
    ap.add_argument("--열기", type=int, choices=[1, 2], metavar="도구번호")
    args = ap.parse_args()

    if args.열기:
        return 열기(args.열기)

    print("=" * 62)
    print("내 도구 점검")
    print("=" * 62)

    설정ok, 설정msg = 검사_설정()
    print(f"\n{OK if 설정ok else NO} 0-1 · config.json")
    for m in 설정msg:
        print(f"       {m}")

    어제ok, 어제msg = 검사_어제코드()
    print(f"\n{OK if 어제ok else NO} 0-2 · 1일차에 만든 detect.py")
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
        print("\n  둘 다 됐습니다.  이제 —  python mcp_server.py")
        print("  그리고 에이전트에게 지시 한 문장을 주세요.")
        return 0
    if args.힌트:
        print(f"\n  힌트 {args.힌트} · 도구 {막힌곳}")
        print(f"       {힌트[막힌곳][args.힌트]}")
    else:
        print(f"  다음에 볼 곳 — 도구 {막힌곳}")
        print("  힌트가 필요하면 —  python 점검.py --힌트 1")
    return 1


if __name__ == "__main__":
    sys.exit(main())
