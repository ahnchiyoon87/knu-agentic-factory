"""학생에게 나눠 줄 실습 저장소를 이 저장소에서 뽑아낸다.

왜 스크립트인가
  학생 저장소를 손으로 만들어 두면, 이쪽 구조가 바뀌었을 때 저쪽이 안 따라온다.
  실제로 한 번 그렇게 어긋났다 — 폴더를 1일차/2일차 로 재편했는데 학생 저장소는
  3일차·4일차 그대로였다. 그래서 **항상 여기서 다시 뽑는다.**

무엇이 들어가는가
  1일차/ · 2일차/        실습 코드와 실습가이드 (강의자료 PNG 는 뺀다 — 무겁고 강사 것)
  데이터/                7일치 센서 CSV. 실습이 이걸 읽는다
  README.md              학생이 저장소를 열었을 때 처음 보는 것

정답/ 은 **같이 나간다.**
  `점검.py --열기` 가 이걸 읽는다. 없으면 「완성본을 못 찾았습니다」로 끝나고,
  실습가이드에 적어 둔 이탈 방지 마지막 수단이 거짓말이 된다.
  3분 막혀서 이탈하는 쪽이 훔쳐보기보다 훨씬 비싸다는 판단이다.

사용법
    python 배포본만들기.py                      ../산출물/배포본/k-precision-lab 에 만든다
    python 배포본만들기.py --out D:/어디에
    python 배포본만들기.py --검증                만든 뒤 학생 조건으로 실제로 돌려 본다
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
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # 제작/검증도구/
REPO = ROOT.parents[1]                          # 경남대특강/ (저장소 루트)
BASE = REPO / "특강" / "학생배포"                  # 여기가 통째로 학생 저장소가 된다
DATA = ROOT / "센서데이터" / "데이터"

# 학생에게 안 나가는 것 — 이름이 아니라 이유로 적는다
제외_폴더 = {"강의자료", "__pycache__", ".git"}
# verify_lab.py — 코드 품질 게이트. 강사 것이다.
# 1일차/2일차 바로 밑의 README.md — 슬라이드 번호와 「강사가 손대는 자리」가 적힌
#   강사 문서다. 슬라이드 번호를 가리키는데 배포본에는 슬라이드가 없고,
#   맨 아래에서 `../당일/진행표.md` 를 보라고 한다 — 학생에겐 없는 파일이다.
#   학생 안내는 배포본 최상위 README.md 가 한다.
제외_파일 = {"verify_lab.py"}
제외_확장 = {".pyc", ".pyo", ".log", ".jsonl"}
# 학생이 실습 중에 만드는 것 — 배포본에 들어 있으면 안 된다.
# `.내번호` 는 **실제 접속 키**가 들어 있다. 검증이 만들고 그대로 두면
# 39명에게 남의 키가 배포된다. 실제로 한 번 그렇게 만들어졌다.
찌꺼기 = {"detect_내가짠것.py", "mcp_server_내가짠것.py", "실행기록.jsonl", ".내번호"}

README = """# K-정밀 실습 저장소

경남대 RISE 피지컬AI 사관학교 · 8월 Agentic AI 특강

이틀 동안 여러분은 **가상 공장의 이상을 잡는 코드를 직접 짜고,
그 코드를 AI 의 도구로 내놓아 설비를 실제로 움직이게** 합니다.

## 어디부터 여나

| 언제 | 읽을 것 | 열 폴더 |
|---|---|---|
| **1일차** | [`1일차/실습가이드.md`](1일차/실습가이드.md) | `1일차/실습` |
| **2일차 오전** | [`2일차/실습가이드.md`](2일차/실습가이드.md) | `2일차/실습/도구만들기` |
| **2일차 오후** | 같은 가이드 §2 | `2일차/실습/폐루프` |

**실습가이드 하나로 끝까지 갈 수 있습니다.** 막히는 자리마다 조치가 바로 아래 적혀 있습니다.

## 이틀 동안 무슨 일이 일어나나

```
1일차   내 공장을 열어 본다  →  이상을 잡는 코드를 직접 짠다
                                  (detect.py 의 빈칸 3개)
                                        │
                                        │  ← 어제 짠 그 코드를 그대로 씁니다
                                        ▼
2일차   오전  내 코드를 AI 가 부를 수 있는 도구로 내놓는다
        오후  AI 가 원인을 대고, 설비를 늦추고, 사람 승인을 받아
              로봇이 실제로 움직인다
```

**두 가지만 지키면 됩니다.**

1. **내 번호를 적어 두세요.** 1일차 맨 처음에 화면에 크게 뜹니다 (예: `S07`).
   자리를 옮기거나 컴퓨터를 바꿔도 그 번호 하나면 원래 공장으로 돌아옵니다.
2. **`1일차/실습` 폴더를 지우지 마세요.** 2일차가 그 안의 `detect.py` 를 그대로 불러 씁니다.

> **여러분이 GitHub 에 무언가를 올리는 순간은 이틀 내내 없습니다.**
> 이 폴더를 받아서 고치기만 합니다. 제출은 노션 링크입니다.

## 먼저 할 것 (1일차 시작 전)

```bash
cd 1일차/실습
pip install -r requirements.txt
python 내번호.py
```

`pandas` 를 깔고, **내 공장 하나를 받습니다.** 화면에 뜨는 번호를 적어 두세요.
2일차에 쓸 설정도 이때 자동으로 채워집니다 — 손으로 옮겨 적을 것이 없습니다.

> **번호를 잊었으면** `python 내번호.py` 를 그냥 다시 치세요. 같은 번호가 나옵니다.
> **자리를 옮겼으면** `python 내번호.py S07` 처럼 번호를 붙여 실행하세요.

## 막히면

각 실습 폴더에 `점검.py` 가 있습니다. **채우는 도중에도 돌아갑니다.**

```bash
python 점검.py            지금 어디까지 됐는지
python 점검.py --힌트 1    개념 힌트
python 점검.py --힌트 2    의사코드 힌트
python 점검.py --열기 1    시간이 없을 때, 그 함수 하나만 완성본으로
```

그래도 안 되면 **손만 드세요.** 앞에 나와서 발표하는 일은 이틀 내내 없습니다.

## 폴더

```
1일차/실습/          detect.py 의 세 함수를 채웁니다
2일차/실습/도구만들기/  내 알고리즘을 MCP 도구로 내놓습니다
2일차/실습/폐루프/     감지·진단·조치 에이전트를 채웁니다
데이터/              7일치 센서 데이터 (60,480행). 실습 코드가 읽습니다
```
"""


def 복사(src: Path, dst: Path) -> int:
    """제외 규칙을 지키며 통째로 옮긴다. 옮긴 파일 수를 돌려준다."""
    n = 0
    for p in src.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(src)
        if 제외_폴더 & set(rel.parts):
            continue
        if rel.name in 제외_파일 or rel.name in 찌꺼기 or p.suffix in 제외_확장:
            continue
        if rel.name == "README.md" and len(rel.parts) == 1:
            continue                                    # 일차 폴더 바로 밑 = 강사 것
        t = dst / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, t)
        n += 1
    return n


def 비우기(out: Path) -> None:
    """내용만 비우고 `.git` 은 남긴다.

    학생 저장소로 한 번 push 하고 나면 여기에 `.git` 이 생긴다.
    통째로 지우면 이력과 리모트가 날아가서 다시 push 를 못 한다.
    남겨 두면 **다시 뽑고 commit 만 하면** 되므로 동기화가 한 번에 끝난다.
    (윈도우는 .git 안 객체가 읽기 전용이라 그냥 지우면 PermissionError 가 난다)
    """
    def 읽기전용해제(func, path, _exc):
        os.chmod(path, 0o700)
        func(path)

    for p in out.iterdir():
        if p.name == ".git":
            continue
        if p.is_dir():
            shutil.rmtree(p, onexc=읽기전용해제)
        else:
            p.unlink()


def 설정되돌리기(out: Path) -> None:
    """검증이 채운 번호·키를 빈 칸으로 되돌린다.

    `내번호.py` 검증이 config.json 에 **진짜 접속 키**를 써 넣는다.
    그대로 두면 39명에게 남의 키가 배포된다. 학생이 처음 여는 상태로 되돌린다.
    """
    import json as _json

    폐루프 = out / "2일차" / "실습" / "폐루프" / "config.json"
    if 폐루프.is_file():
        c = _json.loads(폐루프.read_text(encoding="utf-8"))
        c["tenant"], c["access_key"], c["base_url"] = "", "", ""
        폐루프.write_text(_json.dumps(c, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")

    도구 = out / "2일차" / "실습" / "도구만들기" / "config.json"
    if 도구.is_file():
        c = _json.loads(도구.read_text(encoding="utf-8"))
        c.setdefault("fallback", {})
        # 셋 다 `내번호.py` 가 채운다. 예시 주소·남의 번호를 남기면
        # 안 돌린 학생이 조용히 그 값으로 진행한다 (S01 은 실재하는 남의 번호다).
        c["fallback"]["tenant"] = ""
        c["fallback"]["shared_api"] = ""
        도구.write_text(_json.dumps(c, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")


def 청소(out: Path) -> None:
    """실행이 남긴 것을 치운다. 배포본은 학생이 처음 여는 상태여야 한다."""
    설정되돌리기(out)
    for p in out.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    for 이름 in 찌꺼기:
        for p in out.rglob(이름):
            p.unlink(missing_ok=True)
    for pat in ("*.pyc", "*.log"):
        for p in out.rglob(pat):
            p.unlink(missing_ok=True)


def _토큰() -> str:
    """강사 토큰은 시뮬레이터 .env 에만 있다."""
    env = REPO / "특강" / "시뮬레이터" / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("INSTRUCTOR_TOKEN="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("INSTRUCTOR_TOKEN", "")


def 학생환경() -> dict[str, str]:
    """UTF-8 강제 환경변수를 벗긴다 — 학생 PC 에는 없다."""
    return {k: v for k, v in os.environ.items()
            if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}


def _서버주소() -> str:
    """검증에서 학생 스크립트에 넘길 강사 서버 주소."""
    return (os.environ.get("SHARED_API")
            or _설정("BASE_URL")
            or "http://127.0.0.1:8000").rstrip("/")


def _설정(이름: str) -> str:
    env = REPO / "특강" / "시뮬레이터" / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{이름}="):
                return line.split("=", 1)[1].strip()
    return ""


def 검증(out: Path) -> int:
    """만든 배포본을 학생 조건으로 실제로 돌려 본다. 읽어서는 모른다."""
    print("\n" + "=" * 70)
    print("배포본 검증 — 학생 조건(cp949)으로 실제 실행")
    print("=" * 70)
    실패 = []

    def 돌린다(cwd: Path, args: list[str], 이름: str, 있어야: str) -> str:
        """돌리고 판정한다. 뒤에서 쓸 수 있게 **출력을 돌려준다.**"""
        try:
            p = subprocess.run([sys.executable, *args], cwd=str(cwd),
                               capture_output=True, timeout=600, env=학생환경())
        except subprocess.TimeoutExpired:
            print(f"  [실패] {이름} — 10분 안에 안 끝남")
            실패.append(이름)
            return ""
        txt = p.stdout.decode("utf-8", errors="replace") + \
            p.stderr.decode("utf-8", errors="replace")
        if "UnicodeEncodeError" in txt:
            print(f"  [실패] {이름} — ★ cp949 에서 죽었다 (UTF-8 가드 확인)")
            실패.append(이름)
            return txt
        if "Traceback (most recent call last)" in txt:
            print(f"  [실패] {이름} — 학생 화면에 역추적이 뜬다")
            print("        " + txt.strip().splitlines()[-1][:90])
            실패.append(이름)
            return txt
        if 있어야 not in txt:
            print(f"  [실패] {이름} — 나와야 할 안내가 없다: {있어야!r}")
            실패.append(이름)
            return txt
        print(f"  [통과] {이름}")
        return txt

    SHARED = _서버주소()
    lab1 = out / "1일차" / "실습"
    lab2 = out / "2일차" / "실습" / "도구만들기"
    lab3 = out / "2일차" / "실습" / "폐루프"

    # ★ 학생 여정의 맨 처음 — 여기서 막히면 나머지가 전부 의미 없다
    out_내번호 = 돌린다(lab1, ["내번호.py", "--서버", SHARED],
                       "★ python 내번호.py — 내 공장을 받는다", "당신의 공장은")
    받은번호 = ""
    for 줄 in out_내번호.splitlines():
        if "당신의 공장은" in 줄:
            부분 = [x for x in 줄.split() if x.startswith("S") and len(x) == 3]
            받은번호 = 부분[0] if 부분 else ""
    돌린다(lab1, ["내번호.py", "--서버", SHARED],
           "다시 쳐도 같은 번호다 (수시로 확인 가능)",
           f"★ {받은번호} ★" if 받은번호 else "당신의 공장은")
    if 받은번호:
        돌린다(lab1, ["내번호.py", 받은번호, "--서버", SHARED],
               "★ 번호로 되찾는다 (자리를 옮겼을 때)", "되찾았습니다")

    돌린다(lab1, ["run.py"], "빈 뼈대로 run.py — 무엇을 채울지 알려 준다", "TODO")
    돌린다(lab1, ["점검.py"], "점검.py — 어디가 막혔는지 짚어 준다", "다음에 볼 곳")
    돌린다(lab1, ["점검.py", "--힌트", "1"], "점검.py --힌트 1", "힌트 1 · TODO")
    돌린다(lab2, ["점검.py"], "도구만들기 점검.py", "config.json")

    # ★ 이탈 방지 마지막 수단이 배포본에서 실제로 되는가 — 정답/ 이 빠지면 여기서 걸린다
    detect_원본 = (lab1 / "detect.py").read_bytes()
    mcp_원본 = (lab2 / "mcp_server.py").read_bytes()
    try:
        for n in ("1", "2", "3"):
            돌린다(lab1, ["점검.py", "--열기", n], f"1일차 --열기 {n} (정답/ 이 같이 왔는가)",
                   "완성본으로 채웠습니다")
        돌린다(lab1, ["점검.py"], "--열기 뒤 점검이 3/3", "3개 중 3개 통과")
        돌린다(lab1, ["run.py"], "★ --열기 뒤 run.py 가 끝까지 간다", "분명하게 잡은 것")

        for n in ("1", "2"):
            돌린다(lab2, ["점검.py", "--열기", n], f"2일차 오전 --열기 {n}",
                   "완성본으로 채웠습니다")
        돌린다(lab2, ["mcp_server.py", "--check"], "★ --열기 뒤 도구 2개가 실제로 돈다",
               "sample_count")
        # 2일차 오전의 마지막 장면 — AI 가 **스스로** 내 도구를 골라 부르는가.
        # 실제 모델을 부른다(비용). 이게 안 되면 오전 22분이 통째로 빈다.
        txt = 돌린다(lab2, ["agent.py", "--설비", "EQ-03"],
                    "★ AI 가 내 도구를 스스로 부른다 (2일차 오전 하이라이트)",
                    "도구 호출  detect_anomaly")
        if "WO-2026-0801" not in txt:
            print("  [실패] AI 리포트가 작업지시 번호를 인용하지 않았다")
            실패.append("AI 리포트 WO 인용")
        else:
            print("  [통과] AI 리포트가 WO-2026-0801 을 근거로 인용한다")
    finally:
        (lab1 / "detect.py").write_bytes(detect_원본)
        (lab2 / "mcp_server.py").write_bytes(mcp_원본)
        (lab1 / "detect_내가짠것.py").unlink(missing_ok=True)
        (lab2 / "mcp_server_내가짠것.py").unlink(missing_ok=True)

    # 2일차 오후 — 내번호.py 가 이미 채워 놨으므로 바로 붙어야 한다.
    # (제어는 아직 안 열렸을 수 있으니 「연결」 줄만 본다)
    돌린다(lab3, ["loop.py", "--check"], "폐루프 — 내번호.py 가 채운 설정으로 바로 붙는다",
           "연결")
    돌린다(lab3, ["control_mcp.py", "--check"], "제어 도구도 같은 설정으로 붙는다",
           "set_equipment_speed")

    # 설정을 비워 보고, 안 채운 학생에게 무엇을 하라고 하는지 본다
    폐루프cfg = lab3 / "config.json"
    원래cfg = 폐루프cfg.read_bytes()
    try:
        import json as _json
        c = _json.loads(원래cfg.decode("utf-8"))
        c["tenant"], c["access_key"] = "", ""
        폐루프cfg.write_text(_json.dumps(c, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        # 빈 칸을 짚는 데서 그치면 안 된다 — 「무엇을 하라」까지 나와야 한다.
        # 예전에는 「쪽지 보고 채우세요」였는데 쪽지는 없어졌다. 그 자리를 못 빠져나온다.
        돌린다(lab3, ["loop.py", "--check"], "설정이 비면 어느 줄이 비었는지 짚어 준다",
               "python 내번호.py")
        돌린다(lab3, ["control_mcp.py", "--check"],
               "제어 도구도 같은 안내를 낸다 (cp949 포함)",
               "python 내번호.py")
    finally:
        폐루프cfg.write_bytes(원래cfg)

    # 마지막 수단 — 파일을 안 고치므로 되돌릴 것이 없다.
    # 세 자리 다 막힌 학생이 마지막 장면까지 갈 수 있어야 한다.
    돌린다(lab3, ["loop.py", "--열기", "1", "--check"], "2일차 오후 --열기 1 (감지만)",
           "완성본으로 채웠습니다")
    돌린다(lab3, ["loop.py", "--열기", "전부", "--check"],
           "★ --열기 전부 (세 자리 다 막힌 학생도 갈 수 있는가)", "세 자리를 다 열었습니다")

    # 이틀을 잇는 고리 — 2일차 오전이 1일차 폴더를 그대로 불러 쓴다.
    # 저장소를 다시 받거나 폴더를 지운 학생에게 역추적이 뜨면 그 자리에서 끝난다.
    어제 = out / "1일차"
    치운곳 = out / "_1일차_잠시치움"
    어제.rename(치운곳)
    try:
        돌린다(lab2, ["점검.py"], "1일차 폴더가 없을 때 — 점검이 사람 말로 알려 준다",
               "실습 저장소의 `1일차` 폴더가 그대로 있어야 합니다")
        돌린다(lab2, ["mcp_server.py", "--check"],
               "1일차 폴더가 없을 때 — 도구도 역추적 없이 세운다",
               "1일차에 만든 detect.py 를 못 찾았습니다")
    finally:
        치운곳.rename(어제)

    # 검증이 쓴 배정을 되돌린다 — 당일 번호를 미리 소모하면 안 된다
    if 받은번호:
        try:
            import httpx
            httpx.post(f"{SHARED}/api/instructor/unclaim",
                       params={"tenant_id": 받은번호},
                       headers={"X-Instructor-Token": _토큰()}, timeout=15)
            print(f"  (검증이 쓴 배정 {받은번호} 을 되돌렸습니다)")
        except Exception:                                          # noqa: BLE001
            print(f"  ※ 배정 {받은번호} 을 못 되돌렸습니다 — "
                  f"python tools/자리배정.py --풀기 {받은번호}")

    # 검증이 남긴 것을 치운다 — 배포본에 __pycache__ 가 섞여 나가면 안 된다
    청소(out)
    # ── 학생에게 나가면 안 되는 것이 섞이지 않았는가 ────────────────────────
    #    한 번 실제로 섞였다 — 동작보장_최소경로.md 뒤에 강사 절이 붙어
    #    `loop.py --use-answers`(세 자리 전부 정답)가 학생 눈에 노출됐다.
    import re as _re
    금지파일 = ("verify_lab.py", ".env", "배정장부", "폐루프_강사우회", ".내번호")
    # 변수 **이름**(OPENAI_API_KEY 같은)은 정상이다. 걸러야 하는 것은 **실제 값**이다.
    비밀값 = [
        (_re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "OpenAI 키 값"),
        (_re.compile(r"postgres(?:ql)?://[^\s\"']+:[^\s\"'@]+@"), "DB 접속 문자열"),
        (_re.compile(r"INSTRUCTOR_TOKEN\s*=\s*\S+"), "강사 토큰"),
        (_re.compile(r"--use-answers"), "정답 일괄 실행법"),
        # 학생 접속 키는 32자리 16진수다. 배포본에 진짜 값이 박혀 있으면 안 된다.
        (_re.compile(r'"access_key"\s*:\s*"[0-9a-f]{24,}"'), "학생 접속 키 값"),
    ]
    # 의도해서 남겨 둔 것 — 여기 없는 것은 전부 실패로 본다.
    #   loop.py 의 `--use-answers` 는 강사가 라이브 시연에 쓰는 경로다.
    #   argparse.SUPPRESS 로 도움말에서 감췄고, 학생 문서 어디에도 안 적혀 있다.
    #   결과만 보면 학생에게 이미 열어 둔 `--열기 전부` 와 같은 자리까지 간다
    #   (막힌 학생을 위한 의도된 탈출구). 그래서 소스에 이름이 남는 것은 허용한다.
    #   강사본과 배포본을 두 벌로 나누면 반드시 어긋나므로 파일을 쪼개지 않는다.
    허용 = {("2일차/실습/폐루프/loop.py", "정답 일괄 실행법")}

    샌것 = []
    for p in out.rglob("*"):
        if not p.is_file() or ".git" in p.parts:
            continue
        if any(g in p.name for g in 금지파일) or "강의자료" in str(p):
            샌것.append(f"파일 {p.relative_to(out)}")
        # ★ 예전에는 .md/.json/.txt 만 봤다. 그러면 **.py 에 박힌 진짜 키를 못 잡는다.**
        #    학생이 여는 것은 대부분 .py 다. 읽히는 것은 전부 본다.
        if p.suffix in (".md", ".json", ".txt", ".py", ".html", ".bat", ".cfg", ".ini"):
            try:
                내용 = p.read_text(encoding="utf-8")
            except Exception:                                      # noqa: BLE001
                continue
            rel = p.relative_to(out).as_posix()
            for 패턴, 이름 in 비밀값:
                if 패턴.search(내용) and (rel, 이름) not in 허용:
                    샌것.append(f"{rel} 안에 {이름}")
    if 샌것:
        print(f"  [실패] ★ 학생에게 나가면 안 되는 것이 섞였다 — {len(샌것)}건")
        for s in 샌것[:6]:
            print(f"          {s}")
        실패.append("강사 것이 배포본에 섞임")
    else:
        print("  [통과] 강사 것·비밀정보가 배포본에 섞이지 않았다")

    # ── 폐지된 개념이 문장으로 남아 있지 않은가 ──────────────────────────
    #    실행 게이트는 「돌아가는 것」만 보장한다. 「쪽지 보고 채우세요」 「막힘 티켓」
    #    처럼 실행에 영향 없는 죽은 개념은 26항목·리허설 75항목을 다 통과하고도
    #    살아남았다 — 실제로 최소경로 카드에서 그렇게 발견됐다. 설계 전환 때
    #    폐지된 말이 학생 눈에 닿으면 존재하지 않는 것을 찾게 되므로 상시 검사한다.
    금칙어 = ("쪽지", "막힘 티켓", "확장 미션", "확장미션", "인쇄", "덱B", "넷째 날")
    죽은말 = []
    for p in out.rglob("*"):
        if not p.is_file() or ".git" in p.parts:
            continue
        if p.suffix in (".md", ".json", ".txt", ".py", ".html", ".bat", ".cfg", ".ini"):
            try:
                내용 = p.read_text(encoding="utf-8")
            except Exception:                                      # noqa: BLE001
                continue
            for 낱말 in 금칙어:
                if 낱말 in 내용:
                    죽은말.append(f"{p.relative_to(out).as_posix()} 안에 「{낱말}」")
    if 죽은말:
        print(f"  [실패] ★ 폐지된 개념이 학생 자료에 남아 있다 — {len(죽은말)}건")
        for s in 죽은말[:6]:
            print(f"          {s}")
        실패.append("폐지된 개념 잔존")
    else:
        print("  [통과] 폐지된 개념(쪽지·티켓·확장 미션·인쇄 등)이 학생 자료에 없다")

    print("-" * 70)
    if 실패:
        print(f"실패 {len(실패)}건 — " + ", ".join(실패))
        return 1
    print("배포본이 학생 조건에서 그대로 돕니다.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="학생 배포본 만들기")
    ap.add_argument("--out", default=str(REPO / "제작" / "산출물" / "배포본" / "k-precision-lab"))
    ap.add_argument("--검증", action="store_true", help="만든 뒤 학생 조건으로 돌려 본다")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    if not (DATA / "sensor_readings_7days.csv").is_file():
        print(f"센서 데이터가 없습니다: {DATA}", file=sys.stderr)
        return 1

    if out.exists():
        print(f"기존 배포본을 비웁니다 — {out}")
        비우기(out)
    out.mkdir(parents=True, exist_ok=True)

    n1 = 복사(BASE / "1일차", out / "1일차")
    n2 = 복사(BASE / "2일차", out / "2일차")

    (out / "데이터").mkdir()
    n3 = 0
    for name in ("sensor_readings_7days.csv", "labels_rowwise.csv",
                 "labels_intervals.csv", "생성정보.json"):
        shutil.copy2(DATA / name, out / "데이터" / name)
        n3 += 1

    (out / "README.md").write_text(README, encoding="utf-8")
    # 줄 끝 주석을 붙이지 말 것 — .gitignore 는 그것을 패턴의 일부로 읽는다
    (out / ".gitignore").write_text(
        "__pycache__/\n*.py[cod]\n*.log\n실행기록.jsonl\n"
        "detect_내가짠것.py\nmcp_server_내가짠것.py\n"
        "# 내 번호와 접속 키가 들어 있다. 올리지 말 것\n.내번호\n", encoding="utf-8")

    크기 = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"만들었습니다 — {out}")
    print(f"  1일차 {n1}개 · 2일차 {n2}개 · 데이터 {n3}개 · 합계 {크기 / 1e6:.1f}MB")
    print("  정답/ 포함 (점검.py --열기 가 이걸 읽습니다)")

    if args.검증:
        return 검증(out)
    print("\n  학생 조건으로 실제로 돌려 보려면 —  python 배포본만들기.py --검증")
    return 0


if __name__ == "__main__":
    sys.exit(main())
