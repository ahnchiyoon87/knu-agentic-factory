"""3일차 오전 Step 1 — MCP 도구 2개 만들기

    detect_anomaly    2일차에 내가 짠 이상감지를 에이전트가 부를 수 있게
    query_equipment   설비 조회 — 최근 센서값과 정비 이력

이 파일은 **템플릿**입니다. 뼈대와 연결은 이미 되어 있고,
표시된 두 자리만 채우면 됩니다. 막히면 `uv run 점검.py --힌트 1`.

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

바꿔 끼우기 — config.json 한 곳만 고칩니다

  transport            stdio(내 컴퓨터 — 기본) ↔ http(강사 공용 서버로 우회)
  data_source          fallback(이번 특강의 정상 경로 — 기본) ↔ student(개인 DB — 이번엔 안 씀)

  어느 쪽으로 두든 **도구 이름과 응답 형태는 같습니다.**
  그래서 강사가 우회시켜도 내가 만든 에이전트 쪽은 고칠 게 없습니다.
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
    print("  `2일차/실습` 에서 `uv run 점검.py` 로 먼저 확인해 보세요.", file=sys.stderr)
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

    student  → 개인 DB (이번 특강에서는 쓰지 않습니다)
    fallback → 나눠받은 7일치 CSV 를 파일에서 직접 읽는다

    강사 시뮬레이터에서 가져오지 않는 이유 — 시뮬레이터는 최근 1시간만 보관한다.
    "지난 주"를 물으려면 7일치가 있는 쪽을 봐야 한다.
    """
    if CFG["data_source"] == "fallback":
        import csv
        path = _csv_경로()
        cutoff = None
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

    db = CFG["student_db"]
    r = httpx.get(f"{db['url'].rstrip('/')}/rest/v1/{db['readings_table']}",
                  params={"select": "equipment_id,timestamp,temperature,vibration,rpm,run_state",
                          "equipment_id": f"eq.{equipment_id}",
                          "order": "timestamp.desc", "limit": 20000},
                  headers={"apikey": db["key"], "Authorization": f"Bearer {db['key']}"},
                  timeout=30)
    r.raise_for_status()
    return sorted(r.json(), key=lambda x: x["timestamp"])


def _fetch_maintenance(equipment_id: str) -> list[dict]:
    """정비 이력.

    student  → 개인 DB (이번 특강에서는 쓰지 않습니다)
    fallback → 강사 시뮬레이터의 공용 정비 이력

    어느 쪽이든 이 함수가 같은 모양으로 돌려주므로 도구 쪽은 신경 쓰지 않아도 된다.
    """
    if CFG["data_source"] == "fallback":
        fb = CFG["fallback"]
        # 강사 시뮬레이터 주소 — 환경변수가 있으면 그것을 쓴다(리허설·클라우드 전환용)
        shared = (os.environ.get("SHARED_API") or fb["shared_api"]).rstrip("/")
        r = httpx.get(f"{shared}/api/v1/{fb['tenant']}/maintenance",
                      params={"equipment_id": equipment_id}, timeout=30)
        r.raise_for_status()
        return r.json()["maintenance"]

    db = CFG["student_db"]
    r = httpx.get(f"{db['url'].rstrip('/')}/rest/v1/{db['maintenance_table']}",
                  params={"select": "*", "equipment_id": f"eq.{equipment_id}",
                          "order": "issued_at.desc", "limit": 50},
                  headers={"apikey": db["key"], "Authorization": f"Bearer {db['key']}"},
                  timeout=30)
    r.raise_for_status()
    return r.json()


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

    ──────────────────────────────────────────────────────────
    ★ 여기를 채우세요

    할 일은 네 가지입니다.
      1. _fetch_readings(equipment_id, hours) 로 데이터를 가져온다
      2. temperature 와 vibration 각각을 리스트로 뽑는다
         (값이 없는 자리는 None 으로 둔다 — 2일차의 결측 처리가 받아 준다)
      3. 2일차의 detect(values, window, k) 를 각각 돌린다
      4. True 로 나온 자리를 위 Returns 모양으로 정리해 돌려준다

    주의 — 에이전트가 읽을 결과입니다.
      · anomalies 가 너무 길면 에이전트가 다 못 읽습니다. 최근 것 위주로 추리세요
      · 값이 없으면 빈 리스트를 돌려주고, 예외를 밖으로 던지지 마세요
    ──────────────────────────────────────────────────────────
    """
    # TODO: 여기를 채우세요
    raise NotImplementedError("detect_anomaly 를 완성하세요")


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

    ──────────────────────────────────────────────────────────
    ★ 여기를 채우세요

    할 일은 세 가지입니다.
      1. _fetch_readings 로 최근 구간 요약을 만든다 (평균·최대·결측 수)
      2. _fetch_maintenance 로 정비 이력을 가져온다
      3. 위 Returns 모양으로 합쳐 돌려준다

    주의 — 이 도구가 진단의 재료입니다.
      · 정비 이력의 note 를 빠뜨리지 마세요. 원인 추정이 거기서 나옵니다
      · status 가 DONE 이 아닌 작업지시(미완)는 특히 중요합니다
      · 결측이 있으면 그 사실 자체가 정보입니다. 조용히 빼지 마세요
    ──────────────────────────────────────────────────────────
    """
    # TODO: 여기를 채우세요
    raise NotImplementedError("query_equipment 를 완성하세요")


# =============================================================================
# 실행 — 여기는 고치지 않아도 됩니다.
# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description="MCP 도구 서버 — 3일차 오전")
    ap.add_argument("--check", action="store_true", help="서버 없이 도구만 호출해 본다")
    ap.add_argument("--equipment", default="EQ-03", help="--check 에서 쓸 설비")
    args = ap.parse_args()

    if args.check:
        print(f"설정  transport={CFG['transport']} · 데이터={CFG['data_source']}")
        for name, fn in (("detect_anomaly", lambda: detect_anomaly(args.equipment)),
                         ("query_equipment", lambda: query_equipment(args.equipment))):
            try:
                out = fn()
                print(f"\n[{name}] 정상")
                print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:700])
            except NotImplementedError as e:
                print(f"\n[{name}] 아직 안 채움 — {e}")
            except Exception as e:                       # noqa: BLE001
                print(f"\n[{name}] 오류 — {type(e).__name__}: {e}")
        return

    transport = CFG["transport"]
    if transport == "http":
        mcp.settings.host = CFG["http"]["host"]
        mcp.settings.port = int(CFG["http"]["port"])
        print(f"MCP 서버 (http) — {CFG['http']['host']}:{CFG['http']['port']}", file=sys.stderr)
        mcp.run(transport="streamable-http")
    else:
        print("MCP 서버 (stdio)", file=sys.stderr)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
