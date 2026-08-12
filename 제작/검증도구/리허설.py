"""2일치 무인 리허설 — 이틀 수업을 사람 없이 처음부터 끝까지 재생해 본다.

왜 만들었는가
  제작 중 "짧게 돌리면 통과 · 오래 돌리면 실패"하는 결함을 두 번 놓쳤다.
  검증이 매번 초기화 직후에 돌아서 가장 유리한 조건만 재고 있었기 때문이다.

  그래서 이 하네스에는 규칙이 둘 있다.

      ★ 1. 시작할 때 한 번 말고는 초기화하지 않는다.
      ★ 2. 학생이 실행하는 것은 학생 환경 그대로 실행한다.

  2번이 특히 중요하다. 예전 리허설은 자식 프로세스에 PYTHONUTF8=1 을 주입해
  돌렸고, 그래서 cp949 콘솔에서 실습이 중간에 죽는 결함(UnicodeEncodeError)이
  39/39 통과 뒤에 숨어 있었다. 학생 PC 에는 그 환경변수가 없다.
  여기서는 PYTHONUTF8·PYTHONIOENCODING 을 **일부러 벗기고** 돌린다.

무엇을 검사하지 못하는가 (정직하게)
  · 강의장 무선 구간 · 브라우저 렌더링 — 사람이 있어야 한다
  · 사람이 터미널에 y 를 치는 승인 — 여기서는 자동 승인으로 대체한다
  · 강사가 화면에서 AI 로 코드를 만들어 보이는 시연 — 사람이 있어야 한다

사용법
    python 리허설.py --token <강사토큰>
    python 리허설.py --token <토큰> --quick        누적 대기를 줄여 빠르게(결함을 놓칠 수 있음)
    python 리허설.py --token <토큰> --부하          39명 동시 진단까지 (돈이 든다)
    python 리허설.py --token <토큰> --base-url http://34.64.94.16:8000

서버가 떠 있어야 한다. 서버 설정은 **건드리지 않는다** — 출하 기본값 그대로가 도는지 보는 것이 목적이다.
이 특강은 개인 단위다. 팀 네임스페이스는 쓰지 않는다.
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
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent          # 제작/검증도구/
REPO = ROOT.parents[1]                          # 경남대특강/ (저장소 루트)
특강 = REPO / "특강"                             # 일차별 원본: 특강/{일차}/실습
SIM = REPO / "특강" / "시뮬레이터"
DATA = ROOT / "센서데이터" / "데이터"
LAB1 = 특강 / "2일차" / "실습"                   # 이상감지
LAB2 = 특강 / "3일차" / "실습" / "도구만들기"      # MCP 도구
LAB3 = 특강 / "3일차" / "실습" / "폐루프"          # 오케스트레이터

START = time.time()
results: list[tuple[str, str, bool, str]] = []   # (구간, 항목, 통과, 상세)
skipped: list[tuple[str, str, str]] = []         # (구간, 항목, 이유)
_phase = "준비"


def elapsed() -> str:
    s = time.time() - START
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((_phase, name, bool(ok), detail))
    mark = "통과" if ok else "실패"
    print(f"  [{elapsed()}] [{mark}] {name}" + (f" — {detail}" if detail else ""), flush=True)
    return bool(ok)


def skip(name: str, why: str) -> None:
    """검사하지 않은 것을 통과로 세지 않는다. 침묵이 성공처럼 보이면 안 된다."""
    skipped.append((_phase, name, why))
    print(f"  [{elapsed()}] [건너뜀] {name} — {why}", flush=True)


def phase(title: str) -> None:
    global _phase
    _phase = title
    print(f"\n{'=' * 78}\n{title}   (경과 {elapsed()})\n{'=' * 78}", flush=True)


def wait(seconds: float, why: str) -> None:
    """데이터가 쌓이기를 기다린다. 이 하네스의 핵심이다 — 짧게 돌면 결함을 놓친다."""
    if seconds <= 0:
        return
    print(f"  [{elapsed()}] … {why} — {seconds:.0f}초 대기", flush=True)
    time.sleep(seconds)


# =============================================================================
# 학생 환경으로 실행한다 — 여기서 인코딩 결함이 드러난다
# =============================================================================
def 학생환경() -> dict[str, str]:
    """학생 PC 를 흉내낸다. UTF-8 강제 환경변수를 벗긴다.

    이것을 벗기지 않으면 cp949 콘솔에서 나는 UnicodeEncodeError 를 못 본다.
    (실제로 그 결함이 이 자리 때문에 한 번 숨었다)
    """
    return {k: v for k, v in os.environ.items()
            if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}


def 살아있나(out: str) -> bool:
    """학생 화면에 파이썬 역추적이 뜨지 않았는가 — 뜨면 그 자리에서 이탈한다."""
    return "Traceback (most recent call last)" not in out


def run_script(path: Path, args: list[str], timeout: int,
               extra_env: dict[str, str] | None = None) -> tuple[bool, str, str]:
    """학생이 치는 그대로 돌린다. (성공?, 마지막 줄, 전체 출력)

    출력은 bytes 로 받아 UTF-8 로 푼다 — 진입점의 UTF-8 가드가 살아 있으면
    UTF-8 로 나오고, 가드가 빠졌으면 자식이 cp949 로 죽어 그 사실이 드러난다.
    """
    env = {**학생환경(), **(extra_env or {})}
    try:
        p = subprocess.run([sys.executable, str(path.name), *args], cwd=str(path.parent),
                           capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, f"{timeout}초 안에 안 끝남", ""
    out = p.stdout.decode("utf-8", errors="replace")
    err = p.stderr.decode("utf-8", errors="replace")
    if "UnicodeEncodeError" in err:
        return False, "★ cp949 에서 죽었다 — UTF-8 가드가 빠졌다", out + err
    tail = [line for line in out.splitlines() if line.strip()]
    detail = tail[-1][:70] if tail else (err.strip().splitlines() or [f"종료코드 {p.returncode}"])[-1][:70]
    return p.returncode == 0, detail, out + err


class Sim:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.h = {"X-Instructor-Token": token}
        self.c = httpx.Client(timeout=60.0)

    def get(self, path: str, **params) -> dict:
        r = self.c.get(f"{self.base}{path}", params=params or None)
        r.raise_for_status()
        return r.json()

    def inst(self, method: str, path: str, **kw) -> dict:
        r = self.c.request(method, f"{self.base}/api/instructor{path}", headers=self.h, **kw)
        r.raise_for_status()
        return r.json()

    def status_code(self, method: str, path: str, **kw) -> int:
        return self.c.request(method, f"{self.base}{path}", **kw).status_code


# =============================================================================
# 준비 — 강사가 서버를 켠 직후
# =============================================================================
def 준비(s: Sim, ns: str) -> dict:
    phase("준비 — 강사가 서버를 켰다")

    # ── 출발선을 스스로 맞춘다 ────────────────────────────────────────────
    #    이 하네스는 D-3 에 사람 없이 돈다. 지난 실행이나 앞선 시험이 남긴
    #    상태(제어 개방·배속 120·주입) 때문에 실패가 나면, 강사는 그것이
    #    진짜 고장인지 찌꺼기인지 구분할 방법이 없다. 그래서 먼저 되돌린다.
    #    되돌릴 것이 있었으면 말은 해 준다 — 조용히 지나가지 않는다.
    이전 = s.get("/api/v1/health")["clock"]
    열린곳 = [t for t in s.inst("GET", "/tenants")["tenants"] if t["control_unlocked"]]
    주입 = s.inst("GET", "/status")["active_injections"]
    if 이전["real_tick_seconds"] != 1.0 or 열린곳 or 주입:
        s.inst("DELETE", "/inject")
        s.inst("POST", "/control-lock", params={"unlocked": "false", "tenant_id": "*"})
        s.inst("POST", "/time-scale", params={"scale": 60})
        print(f"  [{elapsed()}] 앞선 실행이 남긴 상태를 되돌렸습니다 — "
              f"배속 x{이전['time_scale']:g} · 제어 열린 곳 {len(열린곳)} · 진행 중 주입 {len(주입)}")

    h = s.get("/api/v1/health")
    c = h["clock"]
    check("서버가 떠 있다", h["status"] == "ok", f"네임스페이스 {h['tenants']}개")
    check("개인 39명이 처음부터 떠 있다 (수업 중 재시작할 일이 없다)", h["tenants"] >= 39,
          f"{h['tenants']}개")
    check("팀 네임스페이스가 없다 — 이번 특강은 개인 단위다",
          not [t for t in s.get("/api/v1/tenants")["tenants"]
               if t["tenant_id"].startswith("T")],
          "T* 0개")
    check("배속이 기본값으로 켜져 있다 (강사가 아무것도 안 눌렀다)", c["time_scale"] >= 2,
          f"x{c['time_scale']:g}")
    # 2일차 아침의 출하 상태는 배속 60(tick 1초)이다. 120 이면 어제 수업이나
    # 앞선 테스트가 남긴 상태다 — 그대로 두면 2일차 화면이 너무 빨리 흐른다.
    check("2일차 아침 상태다 (1초에 한 번씩 바뀐다)", c["real_tick_seconds"] == 1.0,
          f"실제 tick {c['real_tick_seconds']}초 · 배속 x{c['time_scale']:g}"
          + ("" if c["real_tick_seconds"] == 1.0 else
             "  → 이전 상태가 남았습니다. `python tools/제어개방.py --end` 로 되돌리세요"))
    check(f"내 공장({ns})이 있다",
          any(t["tenant_id"] == ns for t in s.get("/api/v1/tenants")["tenants"]))

    # ★ 학생이 아예 못 붙는 상태를 여기서 잡는다.
    #   .env 의 HOST 가 127.0.0.1 로 남아 있던 적이 있다 — 강사 본인 화면은 멀쩡하고
    #   학생 39명만 「연결 실패」가 난다. 혼자 리허설하면 절대 안 보인다.
    경고 = s.inst("GET", "/status")["warnings"]
    check("★ 학생이 붙을 수 있는 상태다 (서버가 127.0.0.1 에만 열려 있지 않다)",
          not any(w["code"] == "학생이_못_붙음" for w in 경고),
          next((w["message"] for w in 경고 if w["code"] == "학생이_못_붙음"), "정상"))
    check("팀 네임스페이스가 살아 있지 않다 (개인 단위)",
          not any(w["code"] == "팀_네임스페이스_있음" for w in 경고))

    # 실제로 LAN 주소로 한 번 붙어 본다 — 설정만 보고 넘어가지 않는다
    if s.base.startswith("http://127.0.0.1") or s.base.startswith("http://localhost"):
        lan = _내_LAN주소()
        if lan:
            try:
                r = httpx.get(f"http://{lan}:8000/api/v1/health", timeout=5)
                check("★ 옆자리에서 실제로 붙는다 (LAN 주소로 왕복)",
                      r.status_code == 200, f"http://{lan}:8000")
            except Exception as exc:                               # noqa: BLE001
                check("★ 옆자리에서 실제로 붙는다 (LAN 주소로 왕복)", False,
                      f"{type(exc).__name__} — 방화벽이 8000 을 막았거나 HOST 가 127.0.0.1 입니다")
        else:
            skip("옆자리에서 실제로 붙는다", "LAN 주소를 못 구했다")
    return h


def _내_LAN주소() -> str | None:
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None
    finally:
        s.close()


# =============================================================================
# 2일차 오전 — 학생이 자기 공장을 연다
# =============================================================================
def 자리배정(s: Sim, ns: str) -> None:
    """학생 여정의 첫 단계 — 여기서 막히면 나머지가 전부 의미 없다."""
    phase("2일차 맨 처음 — 학생이 자기 공장을 받는다 (python 내번호.py)")

    import secrets

    표1, 표2 = secrets.token_urlsafe(24), secrets.token_urlsafe(24)

    r = s.c.post(f"{s.base}/api/v1/claim", json={"번호표": 표1, "표시": "리허설-A"})
    check("처음 실행하면 공장 하나를 받는다", r.status_code == 200,
          r.json().get("tenant_id") if r.status_code == 200 else r.text[:60])
    받은 = r.json()["tenant_id"] if r.status_code == 200 else None
    check("접속 키도 같이 온다", bool(r.json().get("access_key")) if 받은 else False)

    r2 = s.c.post(f"{s.base}/api/v1/claim", json={"번호표": 표1})
    check("다시 실행해도 같은 번호다 (수시로 확인해도 안 바뀐다)",
          r2.status_code == 200 and r2.json()["tenant_id"] == 받은,
          f"{받은} → {r2.json().get('tenant_id')}")

    r3 = s.c.post(f"{s.base}/api/v1/claim", json={"번호표": 표2})
    check("옆 사람은 다른 번호를 받는다 (겹치지 않는다)",
          r3.status_code == 200 and r3.json()["tenant_id"] != 받은,
          f"{받은} vs {r3.json().get('tenant_id')}")

    표3 = secrets.token_urlsafe(24)
    r4 = s.c.post(f"{s.base}/api/v1/claim",
                  json={"번호표": 표3, "되찾을_번호": 받은})
    check("★ 자리를 옮겨도 번호 하나로 되찾는다",
          r4.status_code == 200 and r4.json()["tenant_id"] == 받은
          and r4.json().get("되찾음") is True, f"{받은} 되찾음")

    r5 = s.c.post(f"{s.base}/api/v1/claim",
                  json={"번호표": secrets.token_urlsafe(24), "되찾을_번호": "S99"})
    check("없는 번호를 치면 사람 말로 거절한다", r5.status_code == 404)

    현황 = s.get("/api/v1/claim/status")
    check("강사가 배정 현황을 아무 때나 본다",
          현황["전체"] == 현황["배정됨"] + 현황["남음"],
          f"전체 {현황['전체']} · 배정 {현황['배정됨']} · 남음 {현황['남음']}")

    # 리허설이 쓴 배정은 전부 되돌린다 — 당일 번호를 미리 소모하면 안 된다.
    # 되찾기로 옮겨 붙은 것까지 남으므로 현황을 보고 지운다.
    for a in s.get("/api/v1/claim/status")["배정"]:
        s.inst("POST", "/unclaim", params={"tenant_id": a["tenant_id"]})
    남은배정 = s.get("/api/v1/claim/status")["배정됨"]
    check("리허설이 쓴 배정을 되돌렸다 (당일 번호를 미리 안 쓴다)",
          남은배정 == 0, f"배정 {남은배정}건 남음")


def 일일차_공장(s: Sim, ns: str, quick: bool) -> None:
    phase("2일차 오전 — 학생이 브라우저로 자기 공장을 연다")

    st = s.get(f"/api/v1/{ns}/state")
    check("설비 6대 · 로봇 2대가 한 번에 온다",
          len(st["equipment"]) == 6 and len(st["robots"]) == 2)
    cols = {"equipment_id", "display_name", "pos_x", "pos_y", "temperature",
            "vibration", "rpm", "run_state", "target_rpm", "sensor_online"}
    check("설비 응답 필드가 API 명세와 같다", cols <= set(st["equipment"][0]))
    check("제어 통로 4개가 잠긴 채로 보인다 (내일 열린다)",
          st["control"]["unlocked"] is False and len(st["control"]["channels"]) == 4)
    check("제어를 부르면 403 이 돌아온다 (오늘은 못 움직인다)",
          s.status_code("POST", f"/api/v1/{ns}/control/stop_equipment/EQ-01") == 403)
    check("공장 배치도가 온다 (AMR 통로 좌표)",
          len(s.get("/api/v1/layout")["equipment"]) == 6)

    # 값이 실제로 변하는가 — 학생 화면이 살아 있는지의 본질
    a = s.get(f"/api/v1/{ns}/equipment/EQ-01")["temperature"]
    wait(6, "값이 변하는지 보려고")
    b = s.get(f"/api/v1/{ns}/equipment/EQ-01")["temperature"]
    check("값이 계속 바뀐다", a != b, f"{a:.2f}℃ → {b:.2f}℃")

    # null 처리 — 안 하면 학생 화면이 통째로 죽는다
    scale = max(1.0, s.get("/api/v1/health")["clock"]["time_scale"])
    inj = s.inst("POST", "/inject", json={"tenant_id": ns, "equipment_id": "EQ-02",
                                          "kind": "sensor_dropout",
                                          "params": {"duration_seconds": 40 * scale}})
    check("주입 응답이 실제 소요 시간을 알려준다", inj.get("lasts_real_seconds") is not None,
          inj.get("note", "")[:60])
    wait(6, "결측이 반영되기를")
    eq = s.get(f"/api/v1/{ns}/equipment/EQ-02")
    check("센서 결측이 null 로 온다 (결측 처리가 필요한 이유)",
          eq["temperature"] is None and eq["sensor_online"] is False)
    others = [e for e in s.get(f"/api/v1/{ns}/state")["equipment"]
              if e["equipment_id"] != "EQ-02"]
    check("결측은 그 설비에만 (나머지는 정상)", all(e["sensor_online"] for e in others))
    s.inst("DELETE", f"/inject/{inj['id']}")

    # 폴링 — 39명이 동시에 하는 그것
    lat, errs = [], 0
    for _ in range(10 if quick else 20):
        t0 = time.perf_counter()
        try:
            s.get(f"/api/v1/{ns}/state")
        except Exception:                                          # noqa: BLE001
            errs += 1
        lat.append(time.perf_counter() - t0)
        time.sleep(2)
    lat.sort()
    check("2초 폴링이 안정적이다", errs == 0 and lat[int(len(lat) * 0.95)] < 0.5,
          f"에러 {errs} · p95 {lat[int(len(lat) * 0.95)] * 1000:.0f}ms")


# =============================================================================
# 2일차 오후 — 이상감지를 직접 짠다
# =============================================================================
def 일일차_이상감지() -> None:
    phase("2일차 오후 — 이상감지를 직접 짠다 (학생 환경 그대로)")

    csv = DATA / "sensor_readings_7days.csv"
    info = DATA / "생성정보.json"
    if csv.is_file() and info.is_file():
        meta = json.loads(info.read_text(encoding="utf-8"))
        got = hashlib.sha256(csv.read_bytes()).hexdigest()
        check("나눠줄 데이터셋 해시가 기록과 일치한다 (배포본 대조)",
              got == meta.get("sha256"), got[:16] + "…")
        rows = sum(1 for _ in csv.open(encoding="utf-8")) - 1
        check("행수가 기록과 같다 (CNC 6대 × 7일 × 1분)",
              rows == meta.get("행수"), f"{rows:,}행")
        check("컬럼이 명세와 같다",
              meta.get("컬럼") == ["equipment_id", "timestamp", "temperature",
                                   "vibration", "rpm", "run_state"])
    else:
        check("나눠줄 데이터셋이 있다", False, f"없음: {csv.name} / {info.name}")

    check("실습 폴더에 requirements.txt 가 있다 (pandas 가 없으면 첫 명령에서 전원이 막힌다)",
          (LAB1 / "requirements.txt").is_file())

    # 학생이 아무것도 안 채우고 그냥 실행했을 때 — 여기서 죽으면 첫 5분에 전원이 이탈한다
    ok, msg, _ = run_script(LAB1 / "run.py", [], 300)
    check("빈 뼈대로 실행해도 무엇을 채워야 하는지 알려주고 끝난다 (죽지 않는다)",
          (not ok) and "TODO" in msg, msg)

    # 점검.py 는 아직 못 채웠으면 종료코드 1 이 정상이다. 종료코드가 아니라
    # "학생에게 무엇을 보여 주는가"로 판정한다.
    _, msg, out = run_script(LAB1 / "점검.py", [], 120)
    check("점검.py 가 빈 뼈대에서도 죽지 않고 어디가 막혔는지 짚는다 (이탈 방지 1단계)",
          살아있나(out) and "3개 중 0개 통과" in out and "다음에 볼 곳" in out, msg)
    check("점검.py 가 답을 알려주지 않는다 (짚어 주기만 한다)",
          "values[i-window:i]" not in out and "abs((value" not in out)
    _, msg, out = run_script(LAB1 / "점검.py", ["--힌트", "1"], 120)
    check("힌트 1(개념)이 나온다", 살아있나(out) and "힌트 1 · TODO" in out, msg)
    _, msg, out = run_script(LAB1 / "점검.py", ["--힌트", "2"], 120)
    check("힌트 2(의사코드)가 나온다", 살아있나(out) and "힌트 2 · TODO" in out, msg)

    ok, msg, _ = run_script(LAB1 / "verify_lab.py", [], 600)
    check("이상감지 뼈대 검증 — 교안이 가르치려는 것이 재현된다", ok, msg)


def 일일차_열기() -> None:
    """★ 마지막 수단이 정말로 마지막 수단인가 — 쓰고 나서 또 막히면 최악이다."""
    phase("2일차 — 이탈 방지 마지막 수단 (--열기 를 실제로 써 본다)")

    tgt = LAB1 / "detect.py"
    bak = LAB1 / "detect_내가짠것.py"
    원본 = tgt.read_bytes()
    try:
        for n in (1, 2, 3):
            ok, msg, out = run_script(LAB1 / "점검.py", ["--열기", str(n)], 120)
            check(f"--열기 {n} 이 함수 하나만 채운다", ok and 살아있나(out), msg)

        ok, msg, out = run_script(LAB1 / "점검.py", [], 120)
        check("세 개를 다 열면 점검이 3/3 이 된다", ok and "3개 중 3개 통과" in out, msg)

        ok, msg, out = run_script(LAB1 / "run.py", [], 600)
        check("★ --열기 를 쓴 뒤 run.py 가 끝까지 간다 (또 막히지 않는다)", ok, msg)
        # 반전은 학생이 발견한다. 리허설은 그 장면이 나오는지만 본다.
        check("스파이크는 잡히고 드리프트는 안 잡히는 장면이 실제로 나온다",
              "3개 중 3개" in out and "노이즈 수준" in out,
              "run.py 출력에 두 장면이 다 있다")
    finally:
        tgt.write_bytes(원본)
        bak.unlink(missing_ok=True)
        print(f"  [{elapsed()}] detect.py 를 원래 뼈대로 되돌렸습니다")


# =============================================================================
# 3일차 오전 — 내 코드를 AI 의 도구로 내놓는다
# =============================================================================
def 이일차_도구(s: Sim) -> None:
    phase("3일차 오전 — 내 알고리즘을 MCP 도구로 내놓는다 (학생 환경 그대로)")

    cfg = json.loads((LAB2 / "config.json").read_text(encoding="utf-8"))
    check("도구 설정이 개인 네임스페이스를 본다 (팀이 아니다)",
          not str(cfg["fallback"]["tenant"]).startswith("T"),
          f"tenant={cfg['fallback']['tenant']}")
    # csv_path 기본값은 "auto" — 코드가 스스로 찾는다. 강사본과 배포본이 데이터를
    # 다른 자리에 두므로, 여기서도 같은 규칙으로 찾아 확인한다.
    설정 = str(cfg["fallback"].get("csv_path", "auto")).strip()
    if 설정 and 설정 != "auto":
        csv_path = (LAB2 / 설정).resolve()
    else:
        csv_path = DATA / "sensor_readings_7days.csv"
    check("도구가 읽을 CSV 를 실제로 찾는다", csv_path.is_file(),
          f"csv_path={설정} → {csv_path}")

    _, msg, out = run_script(LAB2 / "점검.py", [], 180, {"SHARED_API": s.base})
    check("점검.py 가 빈 템플릿에서도 죽지 않는다 (이탈 방지)", 살아있나(out), msg)
    check("점검.py 가 강사 서버에 실제로 닿아 정비 이력을 확인한다",
          "정비 이력 확인" in out, [line for line in out.splitlines()
                                    if "config.json" in line][-1][:70]
          if any("config.json" in line for line in out.splitlines()) else msg)
    check("2일차 detect.py 가 비면 그 사실을 먼저 알려 준다 (엉뚱한 데서 헤매지 않게)",
          "2일차" in out and "detect.py" in out, msg)

    ok, msg, _ = run_script(LAB2 / "verify_lab.py", [], 600, {"SHARED_API": s.base})
    check("MCP 도구 템플릿 검증 — 서버를 띄워 도구가 왕복한다", ok, msg)


def 이일차_열기(s: Sim, ns: str = "S01") -> None:
    phase("3일차 — 이탈 방지 마지막 수단 (--열기 를 실제로 써 본다)")

    detect_tgt, detect_bak = LAB1 / "detect.py", LAB1 / "detect_내가짠것.py"
    mcp_tgt, mcp_bak = LAB2 / "mcp_server.py", LAB2 / "mcp_server_내가짠것.py"
    detect_원본, mcp_원본 = detect_tgt.read_bytes(), mcp_tgt.read_bytes()
    try:
        # 도구는 2일차 detect.py 를 그대로 불러 쓴다 — 그쪽이 비어 있으면 도구도 못 돈다
        for n in (1, 2, 3):
            run_script(LAB1 / "점검.py", ["--열기", str(n)], 120)
        for n in (1, 2):
            ok, msg, _ = run_script(LAB2 / "점검.py", ["--열기", str(n)], 120)
            check(f"--열기 {n} 이 도구 본문만 채운다", ok, msg)

        ok, msg, out = run_script(LAB2 / "mcp_server.py", ["--check"], 300,
                                  {"SHARED_API": s.base})
        check("★ --열기 를 쓴 뒤 도구 2개가 실제로 돈다 (또 막히지 않는다)",
              ok and "아직 안 채움" not in out and "오류" not in out, msg)
        check("도구가 2일차에 짠 detect() 를 그대로 쓴다 — 오늘의 핵심 장면",
              "sample_count" in out and "anomaly_count" in out)
        check("정비 이력의 미완 작업지시가 도구 응답에 드러난다",
              "WO-2026-0801" in out or "open_work_orders" in out)

        # ★ 3일차 오전의 마지막 장면 — AI 가 **스스로** 도구를 골라 부른다.
        #   실제 모델을 부른다(비용). 여기가 죽으면 오전 22분이 통째로 빈다.
        #   `--check` 는 도구가 도는지만 보고, 이 검사는 **AI 가 부르는지**를 본다.
        # 학생은 `내번호.py` 가 남긴 `.내번호` 에서 키를 읽는다. 리허설은 그 파일을
        # 만들지 않으므로(당일 번호를 미리 소모하지 않는다) 환경변수로 같은 값을 준다.
        키 = {t["tenant_id"]: t["access_key"]
              for t in s.inst("GET", "/tenants")["tenants"]}
        ok, msg, out = run_script(LAB2 / "agent.py", ["--설비", "EQ-03"], 300,
                                  {"SHARED_API": s.base, "W6_TENANT": ns,
                                   "W6_ACCESS_KEY": 키.get(ns, "")})
        check("★ AI 가 내 도구를 스스로 골라 부른다 (3일차 오전 하이라이트)",
              ok and "도구 호출  detect_anomaly" in out, msg)
        check("AI 리포트가 작업지시 번호를 근거로 인용한다",
              "WO-2026-0801" in out,
              next((l.strip()[:70] for l in out.splitlines() if "WO-2026-0801" in l), msg))
    finally:
        detect_tgt.write_bytes(detect_원본)
        mcp_tgt.write_bytes(mcp_원본)
        detect_bak.unlink(missing_ok=True)
        mcp_bak.unlink(missing_ok=True)
        print(f"  [{elapsed()}] detect.py · mcp_server.py 를 원래 템플릿으로 되돌렸습니다")


# =============================================================================
# 3일차 오후 — 제어를 열고 폐루프를 돈다
# =============================================================================
def 이일차_제어(s: Sim, base: str, ns: str, ns2: str) -> dict:
    phase("3일차 오후 — 강사가 제어를 연다")

    ok, msg, _ = run_script(SIM / "tools" / "제어개방.py", ["--base", base], 180)
    check("3일차 준비가 명령 하나로 끝난다 (tools/제어개방.py)", ok, msg)

    st = s.get(f"/api/v1/{ns}/state")
    check("제어 통로가 열렸다", st["control"]["unlocked"] is True)
    warn = s.inst("GET", "/status")["warnings"]
    check("콘솔이 '주입이 없다'를 스스로 경고한다",
          any(w["code"] == "DAY2_NO_INJECTION" for w in warn),
          ", ".join(w["code"] for w in warn) or "경고 없음")

    keys = {t["tenant_id"]: t["access_key"] for t in s.inst("GET", "/tenants")["tenants"]}

    # ---- 격리 : 두 학생이 동시에 다른 설비를 제어한다 -------------------------
    ra = s.c.post(f"{base}/api/v1/{ns}/control/set_equipment_speed/EQ-04",
                  json={"rpm": 900, "issued_by": "rehearsal"},
                  headers={"X-Access-Key": keys[ns]})
    rb = s.c.post(f"{base}/api/v1/{ns2}/control/set_equipment_speed/EQ-05",
                  json={"rpm": 2400, "issued_by": "rehearsal"},
                  headers={"X-Access-Key": keys[ns2]})
    check("두 학생이 동시에 서로 다른 설비를 제어한다",
          ra.status_code == 200 and rb.status_code == 200)
    cross = s.c.post(f"{base}/api/v1/{ns}/control/stop_equipment/EQ-01",
                     json={}, headers={"X-Access-Key": keys[ns2]})
    check("남의 키로는 못 건드린다", cross.status_code == 401)
    sa = {e["equipment_id"]: e for e in s.get(f"/api/v1/{ns}/state")["equipment"]}
    sb = {e["equipment_id"]: e for e in s.get(f"/api/v1/{ns2}/state")["equipment"]}
    check("옆 사람 공장이 안 흔들린다 (교차 오염 없음)",
          abs(sa["EQ-04"]["target_rpm"] - 900) < 1 and abs(sb["EQ-05"]["target_rpm"] - 2400) < 1
          and abs(sb["EQ-04"]["target_rpm"] - 900) > 1,
          f"{ns}/EQ-04={sa['EQ-04']['target_rpm']:.0f} · {ns2}/EQ-04={sb['EQ-04']['target_rpm']:.0f}")
    return keys


def 이일차_폐루프(s: Sim, base: str, ns: str, keys: dict, quick: bool) -> None:
    """학생이 실제로 돌리는 그 코드를, 초기화하지 않은 공장 위에서 돌린다."""
    phase("3일차 오후 — 폐루프 (초기화하지 않은 공장 위에서)")

    cfg0 = json.loads((LAB3 / "config.json").read_text(encoding="utf-8"))
    dcfg = cfg0["detect"]

    # ★ 이 하네스의 요점 — 「초기화 직후의 유리한 조건」이 아닌 상태에서 잡는가.
    #
    #   감지기는 최근 window_samples×2 만 잘라서 본다. 그 자르기를 빠뜨리면
    #   창이 길어질수록 드리프트가 희석돼 미탐이 된다(실측: 12분 뒤 +0.50℃ 로 주저앉음).
    #   그러니 **창이 그 상한만큼 실제로 찬 뒤에** 잡히는지를 봐야 의미가 있다.
    #
    #   보존정책은 가상 시각 기준이라 배속이 높으면 사실상 안 지운다.
    #   배속 120 에서 1초에 약 2샘플 — 600샘플은 약 5분이면 찬다(실측 3분에 388).
    need = int(dcfg["window_samples"]) * 2

    def acc() -> int:
        return s.get(f"/api/v1/{ns}/readings", equipment_id="EQ-03",
                     minutes=30, limit=20000)["count"]

    n = acc()
    if quick:
        skip("창이 이미 꽉 차 있다 (초기화 직후가 아니다)",
             f"--quick 이라 {n}/{need}샘플. 창 희석 결함은 이 모드로 못 잡는다")
    else:
        t0 = time.time()
        while n < need and time.time() - t0 < 600:
            print(f"  [{elapsed()}] … 창이 차기를 기다린다 {n}/{need}샘플", flush=True)
            time.sleep(20)
            n = acc()
        if n >= need:
            check("★ 창이 감지기 상한만큼 꽉 찼다 (초기화 직후가 아니다 — 이 하네스의 요점)",
                  True, f"{n}/{need}샘플 누적")
        else:
            # 못 채웠으면 통과로 세지 않는다. 침묵이 성공처럼 보이면 안 된다.
            skip("창이 감지기 상한만큼 꽉 찼다",
                 f"10분 안에 {n}/{need}샘플까지만 쌓였다 — 창 희석 결함은 이 실행으로 "
                 "확인되지 않았다 (배속을 120 으로 두고 다시 돌리세요)")

    sys.path.insert(0, str(LAB3))
    sys.path.insert(0, str(LAB3 / "정답"))
    os.environ.update({"W6_BASE_URL": base, "W6_TENANT": ns,
                       "W6_ACCESS_KEY": keys[ns]})
    import agent_bodies                                            # noqa: E402
    agent_bodies.install()
    import hitl                                                    # noqa: E402
    import loop as looper                                          # noqa: E402
    from agents import detector                                    # noqa: E402
    from control_client import CONTROL_TOOLS, MCPControl           # noqa: E402
    from factory_api import FactoryAPI                             # noqa: E402

    hitl.CFG["hitl"]["auto_approve"] = True      # 사람이 y 를 치는 대신
    api = FactoryAPI()
    mcp = MCPControl(api=api)
    check("제어 4종이 MCP 도구로 열린다",
          sorted(mcp.tools) == sorted(CONTROL_TOOLS), ", ".join(sorted(mcp.tools)))

    cfg = json.loads((LAB3 / "config.json").read_text(encoding="utf-8"))
    cfg["hitl"]["auto_approve"] = True
    ctx = looper.Context(api=api, cfg=cfg, control=mcp)

    inj = s.inst("POST", "/inject", json={"tenant_id": ns, "equipment_id": "EQ-03",
                                          "kind": "temp_drift"})
    print(f"  [{elapsed()}] 주입 — {inj['note']}")
    before = {e["equipment_id"]: e for e in s.get(f"/api/v1/{ns}/state")["equipment"]}

    t0, hit, budget = time.time(), None, (240 if quick else 420)
    while time.time() - t0 < budget:
        found = [f for f in detector.run(ctx) if f["equipment_id"] == "EQ-03"]
        if found:
            hit = found[0]
            break
        time.sleep(10)
    check("오래 돌린 상태에서도 드리프트를 잡는다", hit is not None,
          f"{time.time() - t0:.0f}초 만에 — {hit['detail']}" if hit
          else f"{budget}초 안에 미탐 ★ 창 희석 결함")

    if hit:
        rec = looper.one_round(ctx)
        case = rec["cases"][0] if rec["cases"] else {}
        diag = case.get("diagnosis", {})
        acts = case.get("actions", [])
        check("진단이 강사 서버 중계로 실제 모델까지 간다 (조용한 규칙 대체가 아니다)",
              diag.get("backend") == "server", f"backend={diag.get('backend')}")
        check("근거에 작업지시 번호를 그대로 인용한다 (39/39 를 만든 그 문장)",
              any("WO-2026-0801" in str(e) for e in diag.get("evidence", []))
              or "WO-2026-0801" in str(diag.get("cause", "")),
              "; ".join(str(e)[:50] for e in diag.get("evidence", []))[:110])
        check("감속은 승인 없이 실행된다",
              any(x["command"] == "set_equipment_speed" and x["mode"] == "AUTO"
                  and x["status"] == "EXECUTED" for x in acts))
        check("로봇 파견은 승인을 거쳐 실행된다 (승인 화면이 실제로 뜬다)",
              any(x["command"] == "dispatch_robot" and x["mode"] == "APPROVED"
                  and x["status"] == "EXECUTED" for x in acts),
              ", ".join(f"{x['command']}:{x['mode']}" for x in acts) or "조치 없음")

        # 파견 직후에 잰다. 기다린 뒤에 재면 이미 도착해 IDLE 로 돌아가 있을 수 있다.
        로봇 = {r["robot_id"]: r for r in s.get(f"/api/v1/{ns}/state")["robots"]}
        amr = 로봇[cfg["act"]["maintenance_robot"]]
        check("AMR 이 실제로 EQ-03 로 향한다 — 마지막 장면",
              amr["target_node"] == "EQ-03",
              f"{amr['status']} → {amr['target_node']}")

        wait(0 if quick else 25, "감속이 온도에 닿기를")
        after = {e["equipment_id"]: e for e in s.get(f"/api/v1/{ns}/state")["equipment"]}
        check("공장이 실제로 바뀌었다 — 회전수가 내려갔다",
              after["EQ-03"]["target_rpm"] < before["EQ-03"]["target_rpm"],
              f"{before['EQ-03']['target_rpm']:.0f} → {after['EQ-03']['target_rpm']:.0f} rpm")
        if quick:
            skip("감속이 온도를 끌어내렸다 — 루프가 닫혔다", "--quick 이라 하강 대기를 생략")
        else:
            check("감속이 온도를 끌어내렸다 — 루프가 닫혔다",
                  after["EQ-03"]["temperature"] < hit["recent"],
                  f"{hit['recent']:.1f}℃ → {after['EQ-03']['temperature']:.1f}℃")
        cmds = s.get(f"/api/v1/{ns}/control/commands", limit=20)["commands"]
        check("모든 조치가 감사 로그에 남는다",
              any(c["command"] == "set_equipment_speed" for c in cmds), f"{len(cmds)}건")

    mcp.close()
    api.close()
    (LAB3 / "실행기록.jsonl").unlink(missing_ok=True)


# =============================================================================
# 39명 규모 — 돈이 드는 검사라 따로 켠다
# =============================================================================
def 부하(base: str, n: int, stagger: float) -> None:
    phase(f"39명 규모 — 동시 진단 {n}명 (실제 모델 호출 · 비용 발생)")
    ok, msg, out = run_script(SIM / "tools" / "부하테스트_진단.py",
                              ["--n", str(n), "--stagger", str(stagger), "--base", base], 900)
    check("전원이 진단을 받는다 (429 없이)", ok, msg)
    check("전원이 같은 장면을 본다 — WO 인용",
          f"{n}/{n}" in out or "39/39" in out,
          [line for line in out.splitlines() if "WO" in line][-1][:70]
          if any("WO" in line for line in out.splitlines()) else msg)


# =============================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="2일치 무인 리허설")
    ap.add_argument("--token", required=True, help="X-Instructor-Token")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--ns", default="S01", help="리허설에 쓸 개인 네임스페이스")
    ap.add_argument("--ns2", default="S02", help="격리 검사에 쓸 옆자리 네임스페이스")
    ap.add_argument("--quick", action="store_true", help="누적 대기를 줄인다(결함을 놓칠 수 있음)")
    ap.add_argument("--soak", type=float, default=None,
                    help="2일차~3일차 사이 추가 누적 시간(초). 기본은 창이 찰 만큼")
    ap.add_argument("--부하", action="store_true",
                    help="39명 동시 진단까지 검사한다 (실제 모델 호출 · 비용 발생)")
    ap.add_argument("--부하인원", type=int, default=39)
    args = ap.parse_args()

    print("=" * 78)
    print("2일치 무인 리허설 — 이틀 수업을 사람 없이 처음부터 끝까지 재생한다")
    print(f"  대상 {args.base_url} · 시작 {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("  ★ 시작할 때 한 번 말고는 초기화하지 않는다")
    print("  ★ 학생이 실행하는 것은 학생 환경(cp949)으로 실행한다")
    print("=" * 78)

    s = Sim(args.base_url, args.token)
    try:
        s.get("/api/v1/health")
    except Exception as exc:                                       # noqa: BLE001
        print(f"\n서버에 닿지 못했습니다 — {type(exc).__name__}: {exc}", file=sys.stderr)
        print("  특강/시뮬레이터 에서 python -m server.run 을 먼저 실행하세요.", file=sys.stderr)
        return 1

    있는것 = {t["tenant_id"] for t in s.get("/api/v1/tenants")["tenants"]}
    없는것 = [x for x in (args.ns, args.ns2) if x not in 있는것]
    if 없는것:
        print(f"\n네임스페이스가 없습니다: {', '.join(없는것)}", file=sys.stderr)
        print(f"  서버에 있는 것 {len(있는것)}개. .env 의 TENANT_MODE 를 확인하세요.",
              file=sys.stderr)
        return 1

    # 처음 한 번만 초기화한다. 이후로는 절대 하지 않는다.
    print(f"\n초기화(처음 한 번) — {args.ns}, {args.ns2}")
    for t in (args.ns, args.ns2):
        s.inst("POST", "/reset", params={"tenant_id": t})

    try:
        준비(s, args.ns)
        자리배정(s, args.ns)
        일일차_공장(s, args.ns, args.quick)
        일일차_이상감지()
        일일차_열기()
        이일차_도구(s)
        이일차_열기(s, args.ns)
        soak = args.soak if args.soak is not None else (0 if args.quick else 180)
        wait(soak, "실습이 진행되는 동안 데이터가 쌓이도록 (여기가 결함이 드러나는 자리)")
        keys = 이일차_제어(s, args.base_url, args.ns, args.ns2)
        이일차_폐루프(s, args.base_url, args.ns, keys, args.quick)
        if getattr(args, "부하"):
            부하(args.base_url, args.부하인원, 2.0)
        else:
            skip("39명 동시 진단", "--부하 를 안 켰다. 39/39·429 0건은 이 실행으로 확인되지 않았다")
    finally:
        phase("정리 — 2일차 상태로 되돌린다")
        run_script(SIM / "tools" / "제어개방.py", ["--end", "--base", args.base_url], 180)
        for t in (args.ns, args.ns2):
            try:
                s.inst("POST", "/reset", params={"tenant_id": t})
            except Exception:                                      # noqa: BLE001
                pass
        print(f"  [{elapsed()}] 되돌렸습니다")

    # ---- 요약 ---------------------------------------------------------------
    print("\n" + "=" * 78)
    print(f"요약   총 소요 {elapsed()}")
    print("=" * 78)
    by_phase: dict[str, list] = {}
    for d, name, ok, detail in results:
        by_phase.setdefault(d, []).append((name, ok, detail))
    for d, items in by_phase.items():
        bad = [i for i in items if not i[1]]
        print(f"  {'O' if not bad else 'X'} {d:<52} {len(items) - len(bad)}/{len(items)}")
        for name, _ok, detail in bad:
            print(f"      실패 — {name}" + (f" ({detail})" if detail else ""))

    if skipped:
        print(f"\n  건너뛴 검사 {len(skipped)}건 — 이 항목들은 **검증되지 않았습니다**")
        for _d, name, why in skipped:
            print(f"      · {name} ({why})")

    failed = [r for r in results if not r[2]]
    print("-" * 78)
    if failed:
        print(f"실패 {len(failed)}건 / 전체 {len(results)}건")
        return 1
    if skipped:
        print(f"통과 {len(results)}건 · **건너뜀 {len(skipped)}건** — 전체 검증이 아닙니다.")
        return 0
    print(f"전 항목 통과 — {len(results)}건. 이틀이 초기화 없이 연속으로 돌았습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
