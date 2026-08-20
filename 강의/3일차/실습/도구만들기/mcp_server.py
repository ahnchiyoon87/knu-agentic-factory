"""3일차 오전 Step 1 — MCP 도구 2개 만들기

    detect_anomaly    2일차에 내가 짠 이상감지를 에이전트가 부를 수 있게
    query_equipment   설비 조회 — 최근 센서값과 정비 이력

이 파일은 **템플릿**입니다. 뼈대와 연결은 이미 되어 있고,
표시된 두 자리만 채우면 됩니다. 필요한 것은 그 자리 주석에 다 적혀 있습니다.

    uv run mcp_server.py            서버 실행 (config.json 의 transport 를 따름)
    uv run mcp_server.py --check    도구가 실제로 도는지 서버 없이 확인

────────────────────────────────────────────────────────────────────
MCP 가 무엇인가

  내가 만든 함수를 에이전트가 **직접 호출할 수 있게** 내놓는 표준입니다.
  함수에 @mcp.tool() 을 붙이면 에이전트가 그 함수의 이름·설명·인자를 읽고
  필요할 때 스스로 부릅니다.

  오늘은 '읽는 손'입니다. 조회만 합니다.
  '움직이는 손'(설비 제어)은 오늘 오후에 열립니다.
────────────────────────────────────────────────────────────────────

설정은 미리 채워져 있습니다 — config.json 을 손댈 일이 없습니다.

  transport      stdio — 도구가 내 컴퓨터에서 돈다
  data_source    fallback — 센서값은 어제 받은 7일치 CSV 를 그대로 읽는다
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
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from mcp.server import MCPServer

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

# 2일차에 내가 짠 이상감지를 그대로 가져옵니다. **오늘의 핵심 장면입니다.**
_어제 = ROOT.parents[2] / "2일차" / "실습"
sys.path.insert(0, str(_어제))
try:
    from detect import detect            # noqa: E402  ← 내가 채운 그 함수
except ModuleNotFoundError:              # 2일차 폴더가 없어졌다
    print("2일차에 만든 detect.py 를 못 찾았습니다.", file=sys.stderr)
    print(f"  찾아본 곳: {_어제}", file=sys.stderr)
    print("  실습 저장소의 `2일차` 폴더가 그대로 있어야 합니다 —", file=sys.stderr)
    print("  오늘 도구는 어제 여러분이 짠 코드를 그대로 불러 씁니다.", file=sys.stderr)
    print("  폴더가 없으면 손 드세요. 다시 받아 드립니다.", file=sys.stderr)
    sys.exit(1)
except Exception as exc:                 # noqa: BLE001
    print(f"2일차의 detect.py 를 불러오지 못했습니다: {exc}", file=sys.stderr)
    print("  `2일차/실습` 에서 `uv run 확인.py` 로 먼저 확인해 보세요.", file=sys.stderr)
    sys.exit(1)

mcp = MCPServer(
    name="k-precision-tools",
    instructions="K-정밀 공장의 센서 이상감지와 설비 조회 도구입니다. 조회만 하며 설비를 움직이지 않습니다.",
)


# =============================================================================
# 데이터 가져오기 — 여기는 이미 되어 있습니다. 고치지 않아도 됩니다.
# =============================================================================
def _csv_경로() -> Path:
    """2일차에 쓴 그 CSV 를 찾는다.

    config.json 의 csv_path 가 "auto"(기본)면 위로 올라가며 스스로 찾는다.
    나눠 준 실습 저장소는 `데이터/`, 강사 저장소는 `제작/검증도구/센서데이터/데이터/` 에 둔다.
    직접 경로를 적어 두었으면 그것을 그대로 쓴다.
    """
    설정 = str(CFG["fallback"].get("csv_path", "auto")).strip()
    if 설정 and 설정 != "auto":
        return (ROOT / 설정).resolve()
    for base in (ROOT, *list(ROOT.parents)[:5]):
        for cand in (base / "데이터", base / "제작" / "검증도구" / "센서데이터" / "데이터"):
            if (cand / "sensor_readings_7days.csv").is_file():
                return cand / "sensor_readings_7days.csv"
    return ROOT.parents[2] / "데이터" / "sensor_readings_7days.csv"


def _fetch_readings(equipment_id: str, hours: int) -> list[dict]:
    """최근 hours 시간의 센서값. 오래된 것부터 정렬해서 돌려준다.

    어제 받은 7일치 CSV 를 파일에서 직접 읽는다.

    공장에서 가져오지 않는 이유 — 공장은 최근 1시간만 보관한다.
    "지난 주"를 물으려면 7일치가 있는 쪽을 봐야 한다.
    """
    import csv
    path = _csv_경로()
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["equipment_id"] != equipment_id:
                continue
            rows.append({
                "equipment_id": r["equipment_id"],
                "timestamp": r["timestamp"],
                "temperature": float(r["temperature"]) if r["temperature"] else None,
                "vibration": float(r["vibration"]) if r["vibration"] else None,
                "rpm": float(r["rpm"]) if r["rpm"] else None,
                "run_state": r["run_state"],
            })
    rows.sort(key=lambda x: x["timestamp"])
    if hours and rows:
        last = datetime.fromisoformat(rows[-1]["timestamp"])
        cutoff = (last - timedelta(hours=hours)).isoformat()
        rows = [r for r in rows if r["timestamp"] >= cutoff]
    return rows


def _fetch_maintenance(equipment_id: str) -> list[dict]:
    """정비 이력 — 어제 켠 내 공장에서 가져온다."""
    fb = CFG["fallback"]
    공장 = (os.environ.get("SHARED_API") or fb["shared_api"]).rstrip("/")
    r = httpx.get(f"{공장}/api/v1/{fb['tenant']}/maintenance",
                  params={"equipment_id": equipment_id}, timeout=30)
    r.raise_for_status()
    return r.json()["maintenance"]


# =============================================================================
# 도구 1 — detect_anomaly
# =============================================================================
@mcp.tool()
def detect_anomaly(equipment_id: str, hours: int = 168, k: float | None = None) -> dict:
    """설비 한 대의 센서값에서 이상 구간을 찾는다.

    Args:
        equipment_id: EQ-01 ~ EQ-06
        hours: 몇 시간 전까지 볼지 (기본 168 = 7일)
        k: 임계값. 비우면 config.json 의 값

    Returns:
        equipment_id, checked_hours, k, sample_count,
        anomaly_count, anomalies[{timestamp, metric, value}]

    """
    rows = _fetch_readings(equipment_id, hours)
    if not rows:
        return {"equipment_id": equipment_id, "checked_hours": hours,
                "sample_count": 0, "anomaly_count": 0, "anomalies": [],
                "note": "해당 구간에 데이터가 없습니다."}

    window = int(CFG["detect"]["window"])
    kk = float(k if k is not None else CFG["detect"]["k"])

    found: list[dict] = []
    for metric in ("temperature", "vibration"):

        # ── 빈칸 1 ───────────────────────────────────────────────────────────
        #   이 항목(metric)의 값만 순서대로 뽑는다. 값이 없는 자리는 None 으로 둔다.
        #   (2일차에 만든 결측 처리가 그 None 을 받아 준다)
        #   쓸 것 :  r.get(metric)   float(...)   [ ... for r in rows ]
        values = ...

        # ── 빈칸 2 ───────────────────────────────────────────────────────────
        #   ★ 오늘의 핵심 — 어제 짠 detect() 를 여기서 부른다.
        #   values 와 같은 길이의 True/False 목록이 나온다.
        #   쓸 것 :  detect(values, window=window, k=kk)
        플래그 = ...

        for row, flag in zip(rows, 플래그):
            if flag:
                found.append({"timestamp": str(row["timestamp"]),
                              "metric": metric,
                              "value": row.get(metric)})

    found.sort(key=lambda x: x["timestamp"], reverse=True)

    # 에이전트가 읽을 결과다. 다 넣으면 길어서 못 읽는다 — 최근 것 위주로 추린다.
    LIMIT = 30
    return {
        "equipment_id": equipment_id,
        "checked_hours": hours,
        "k": kk,
        "window": window,
        "sample_count": len(rows),
        "anomaly_count": len(found),
        "anomalies": found[:LIMIT],
        "truncated": len(found) > LIMIT,
    }


# =============================================================================
# 도구 2 — query_equipment
# =============================================================================
@mcp.tool()
def query_equipment(equipment_id: str, hours: int = 24) -> dict:
    """설비 한 대의 최근 상태와 정비 이력을 조회한다.

    Args:
        equipment_id: EQ-01 ~ EQ-06
        hours: 센서 요약을 낼 구간 (기본 24시간)

    Returns:
        equipment_id,
        recent{hours, sample_count, temperature{avg, max},
               vibration{avg, max}, missing_count},
        maintenance[{work_order_no, issued_at, status, action, note}],
        open_work_orders[ … ]      ← status 가 DONE 이 아닌 작업지시만 추린 것

    """
    rows = _fetch_readings(equipment_id, hours)

    def stat(metric: str) -> dict:
        vals = [float(r[metric]) for r in rows if r.get(metric) is not None]
        if not vals:
            return {"avg": None, "max": None}
        return {"avg": round(sum(vals) / len(vals), 2), "max": round(max(vals), 2)}

    missing = sum(1 for r in rows if r.get("temperature") is None)
    maint = _fetch_maintenance(equipment_id)

    trimmed = [{
        "work_order_no": m.get("work_order_no"),
        "issued_at": str(m.get("issued_at")),
        "status": m.get("status"),
        "action": m.get("action"),

        # ── 빈칸 3 ───────────────────────────────────────────────────────────
        #   ★ 정비 메모. **원인 추정이 여기서 나온다.** 빠뜨리면 잠시 뒤
        #     AI 리포트가 "원인 불명" 으로 끝난다.
        #   쓸 것 :  m.get("note")
        "note": ...,
    } for m in maint[:10]]

    # ── 빈칸 4 ───────────────────────────────────────────────────────────────
    #   아직 안 끝난 작업지시만 추린다. status 가 "DONE" 이 아닌 것.
    #   이게 오늘 AI 가 붙잡을 실마리다.
    #   쓸 것 :  [m for m in trimmed if ... ]
    미완 = ...

    return {
        "equipment_id": equipment_id,
        "recent": {
            "hours": hours,
            "sample_count": len(rows),
            "temperature": stat("temperature"),
            "vibration": stat("vibration"),
            "missing_count": missing,
        },
        "maintenance": trimmed,
        "open_work_orders": 미완,
    }


# =============================================================================
# 어디까지 채웠는지 보기 — 여기는 고치지 않아도 됩니다.
# =============================================================================
def 안채운도구() -> list[str]:
    """아직 안 채운 도구 이름을 돌려준다.

    전에는 `raise NotImplementedError` 를 잡아서 판정했는데, 그 줄을 없애면서
    학생이 「지울지 고칠지」 헷갈리던 것이 사라진 대신 판정 근거도 같이 사라졌다.
    이제는 **이 파일을 읽어** 설명글(docstring)과 주석 말고 실행되는 줄이
    하나도 없으면 안 채운 것으로 본다.

    안 그러면 빈 함수가 조용히 None 을 돌려주고, `--check` 는 「정상」이라 찍는다.
    학생은 다 된 줄 알고 다음으로 넘어간다 — 조용히 실패하면 안 된다.

    ※ `확인.py` 의 `_빈함수()` 와 같은 규칙이다. 두 곳이 어긋나면 판정이 거짓말이 된다.
    """
    import ast

    빈것: list[str] = []
    try:
        나무 = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError:
        return []                       # 문법 오류는 부르는 쪽이 따로 짚어 준다
    for n in ast.walk(나무):
        if isinstance(n, ast.FunctionDef) and n.name in ("detect_anomaly", "query_equipment"):
            if any(isinstance(x, ast.Constant) and x.value is Ellipsis
                   for x in ast.walk(n)):
                빈것.append(n.name); continue
            몸 = [x for x in n.body
                  if not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant)
                          and isinstance(x.value.value, str))]
            if not 몸:
                빈것.append(n.name)
    return 빈것


# =============================================================================
# 실행 — 여기는 고치지 않아도 됩니다.
# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description="MCP 도구 서버 — 3일차 오전")
    ap.add_argument("--확인", "--check", dest="확인", action="store_true", help="서버 없이 도구만 호출해 본다")
    ap.add_argument("--equipment", default="EQ-03", help="--check 에서 쓸 설비")
    args = ap.parse_args()

    if args.확인:
        print(f"설정  transport={CFG['transport']} · 데이터={CFG['data_source']}")
        빈것 = 안채운도구()
        for name, fn in (("detect_anomaly", lambda: detect_anomaly(args.equipment)),
                         ("query_equipment", lambda: query_equipment(args.equipment))):
            # 안 채운 것을 먼저 가른다. 빈 함수는 조용히 None 을 돌려주므로
            # 그냥 부르면 「정상」이라 찍힌다 — 학생이 다 된 줄 알고 넘어간다.
            # 안내 문구에 **찾는 말을 그대로 쓰지 않는다.** 학생이 Ctrl+F 로 찾을 때
            # 이 print 까지 걸려 「두 곳」이 세 곳이 된다. 채울 자리만 걸려야 한다.
            if name in 빈것:
                print(f"\n[{name}] 아직 안 채움 — 그 함수의 `...` 줄을 고칩니다.")
                continue
            try:
                out = fn()
                print(f"\n[{name}] 정상")
                print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:700])
            except Exception as e:                       # noqa: BLE001
                print(f"\n[{name}] 오류 — {type(e).__name__}: {e}")
        return

    print("MCP 서버 (stdio)", file=sys.stderr)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
