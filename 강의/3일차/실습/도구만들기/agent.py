"""3일차 오전 Step 2 — AI 에게 말로 시킨다.

    uv run agent.py                    기본 지시문으로 돌린다
    uv run agent.py --지시 "..."        내 문장으로 바꿔서
    uv run agent.py --설비 EQ-03        특정 설비만 보라고 힌트를 줄 때

여기서 무슨 일이 일어나는가
    ① 내가 만든 도구 두 개의 **이름·설명·인자**를 AI 에게 건넨다
    ② 지시 문장 하나를 준다 — **어떤 도구를 어떤 순서로 부를지는 말하지 않는다**
    ③ AI 가 스스로 「detect_anomaly 를 불러 줘」라고 답한다
    ④ 그 도구는 **내 컴퓨터에서** 실행된다. 결과를 다시 AI 에게 보낸다
    ⑤ AI 가 결과를 보고 다음 도구를 고른다. 다 됐다 싶으면 리포트를 쓴다

    ③~⑤ 를 도는 것이 오늘 오전에 배운 **ReAct** 다.

키는 내 코드에 없다
    AI 호출은 공장이 중계한다. 나는 공장에 붙을 뿐이다.
    도구는 내 컴퓨터에서 돌고, 공장은 「어느 도구를 부를지」만 전달한다.
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
import logging
import sys
from pathlib import Path

import httpx

# httpx 가 요청마다 「HTTP Request: POST ...」 를 찍는다. 오늘 화면에서 봐야 할 것은
# **AI 가 어느 도구를 불렀는가** 하나뿐이라 이 줄이 그것을 가린다.
logging.getLogger("httpx").setLevel(logging.WARNING)

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

# 내가 만든 도구를 그대로 가져온다. mcp_server.py 의 ★ 두 자리가 비어 있으면
# 도구가 조용히 None 을 돌려주므로, 돌리기 전에 `안채운도구()` 로 먼저 세운다.
sys.path.insert(0, str(ROOT))
try:
    from mcp_server import detect_anomaly, query_equipment, 안채운도구  # noqa: E402
except SyntaxError as e:
    # 채우다 만 문법 오류 — 역추적 대신 자리를 짚어 준다.
    sys.exit(f"mcp_server.py {e.lineno}행에 문법 오류가 있습니다 — {e.msg}\n"
             f"  괄호·따옴표·들여쓰기를 그 줄에서 확인하세요. uv run 확인.py 도 같이 짚어 줍니다.")

기본지시 = ("지난 주 설비 이상을 점검하고, 이상이 있으면 해당 설비의 정비 이력을 조회해 "
            "원인 추정과 권고 조치를 담은 진단 리포트를 작성하라.")

# AI 에게 건네는 도구 설명. **이 글을 보고 AI 가 무엇을 부를지 정한다.**
# 설명이 부실하면 엉뚱한 도구를 부르거나 아예 안 부른다 — 그것도 오늘 볼 장면이다.
도구목록 = [
    {"type": "function", "function": {
        "name": "detect_anomaly",
        "description": "설비 한 대의 센서 기록에서 이상 구간을 찾는다. "
                       "온도와 진동을 이동 윈도 z-score 로 판정한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "equipment_id": {"type": "string", "description": "EQ-01 ~ EQ-06"},
                "hours": {"type": "integer", "description": "몇 시간 전까지 볼지. 기본 168(7일)"},
            },
            "required": ["equipment_id"],
        },
    }},
    {"type": "function", "function": {
        "name": "query_equipment",
        "description": "설비 한 대의 최근 센서 요약과 **정비 이력**을 조회한다. "
                       "정비 이력에는 미완 작업지시와 비고가 들어 있다.",
        "parameters": {
            "type": "object",
            "properties": {
                "equipment_id": {"type": "string", "description": "EQ-01 ~ EQ-06"},
            },
            "required": ["equipment_id"],
        },
    }},
]

실행표 = {"detect_anomaly": detect_anomaly, "query_equipment": query_equipment}


def _서버() -> str:
    """공장 주소. mcp_server.py 와 같은 규칙으로 찾는다(환경변수가 우선)."""
    import os
    return str(os.environ.get("SHARED_API") or CFG["fallback"]["shared_api"]).rstrip("/")


def _번호() -> str:
    import os
    return str(os.environ.get("W6_TENANT") or CFG["fallback"]["tenant"]).strip()


def 부르기(messages: list[dict], 왕복: int) -> dict:
    """내 공장(컨테이너)을 거쳐 AI 에게 한 번 묻는다."""
    r = httpx.post(
        f"{_서버()}/api/v1/{_번호()}/agent",
        headers={"X-Access-Key": _접속키()},
        json={"messages": messages, "tools": 도구목록, "왕복": 왕복},
        timeout=90,
    )
    if r.status_code == 429:
        raise RuntimeError("1분 호출 한도를 넘었습니다 — 잠시 뒤 다시 돌리세요.")
    if r.status_code == 400:
        raise RuntimeError(r.json().get("detail", r.text))
    if r.status_code == 503:
        # 39명이 같은 열쇠를 쓴다 — 혼잡이면 공장이 이미 1분 가까이 기다렸다 온 것이다
        raise RuntimeError(r.json().get("detail", "AI 창구가 잠시 막혔습니다 — "
                                                  "1분쯤 뒤에 한 번 더 실행하세요."))
    r.raise_for_status()
    return r.json()


def _접속키() -> str:
    """config.json 에 미리 채워져 온다 — 전원이 같은 값이라 비밀이 아니다."""
    import os
    return (os.environ.get("W6_ACCESS_KEY")
            or str(CFG.get("fallback", {}).get("access_key", "")).strip())


def 도구확인() -> None:
    """★ 두 자리를 채웠는가. 안 채운 채 돌리면 AI 에게 빈 결과(null)가 그대로 간다.

    그러면 AI 는 「데이터가 없다」는 리포트를 그럴듯하게 써 내고, 학생은
    **자기 도구가 비어 있다는 사실 자체를 모른 채** 오전을 넘긴다.
    """
    빈것 = 안채운도구()
    if 빈것:
        sys.exit(f"{' · '.join(빈것)} 이(가) 아직 안 채워져 있습니다.\n"
                 "    mcp_server.py 에서 그 함수의 `...` 줄을 고칩니다.\n"
                 "    어느 자리인지 —  uv run 확인.py")


def 설정확인() -> None:
    안내 = ("    이 값들은 실습 저장소에 미리 채워져 옵니다. 지웠거나 고쳤으면\n"
            "    실습 저장소를 다시 내려받으세요. 안 되면 손 드세요.")
    if not _서버() or not _번호():
        sys.exit("config.json 이 비어 있습니다 — 공장 주소와 번호가 없습니다.\n" + 안내)
    if not _접속키():
        sys.exit("config.json 의 접속 키가 비어 있습니다.\n" + 안내)


def main() -> int:
    ap = argparse.ArgumentParser(description="AI 에게 말로 시킨다 (내 도구를 스스로 부른다)")
    ap.add_argument("--지시", default=기본지시, help="AI 에게 줄 문장 하나")
    ap.add_argument("--설비", default=None, help="특정 설비만 보라고 힌트를 줄 때 (예: EQ-03)")
    args = ap.parse_args()

    도구확인()
    설정확인()

    지시 = args.지시
    if args.설비:
        지시 += f" 대상 설비는 {args.설비} 이다."
    else:
        지시 += " 설비는 EQ-01 부터 EQ-06 까지 있다."

    messages = [
        {"role": "system",
         "content": "너는 공장 설비 진단자다. 반드시 **주어진 도구를 실제로 호출해서** "
                    "사실을 확인한 뒤에 답한다. 도구를 부르지 않고 추측으로 답하지 마라. "
                    "근거에는 조회한 작업지시 번호를 그대로 인용한다. "
                    "리포트만 쓰고 끝낸다 — 되묻거나 추가 제안을 덧붙이지 마라."},
        {"role": "user", "content": 지시},
    ]

    print("=" * 70)
    print("AI 에게 시킨 문장")
    print("=" * 70)
    print(f"  {지시}\n")
    print("  ※ 어떤 도구를 어떤 순서로 부를지는 말하지 않았습니다. AI 가 정합니다.\n")

    for 왕복 in range(6):
        try:
            답 = 부르기(messages, 왕복)
        except Exception as exc:                                    # noqa: BLE001
            print(f"\nAI 호출 실패 — {type(exc).__name__}: {exc}", file=sys.stderr)
            print("  주소·번호가 맞는지 보세요. 그래도 안 되면 손 드세요.", file=sys.stderr)
            return 1

        호출 = 답.get("tool_calls") or []
        if not 호출:
            print("=" * 70)
            print("진단 리포트")
            print("=" * 70)
            print(답.get("content") or "(내용 없음)")
            if 왕복 == 0:
                print("\n  ※ AI 가 도구를 한 번도 안 불렀습니다.")
                print("    도구 설명(agent.py 의 도구목록)이 무엇을 하는 도구인지"
                      " 분명히 말하고 있는지 보세요.")
            return 0

        # AI 가 「이 도구를 불러 줘」라고 한 것을 대화에 남긴다
        messages.append({
            "role": "assistant", "content": 답.get("content"),
            "tool_calls": [{"id": c["id"], "type": "function",
                            "function": {"name": c["name"], "arguments": c["arguments"]}}
                           for c in 호출],
        })

        for c in 호출:
            이름, 인자 = c["name"], json.loads(c["arguments"] or "{}")
            print(f"  도구 호출  {이름}({', '.join(f'{k}={v}' for k, v in 인자.items())})")
            fn = 실행표.get(이름)
            if fn is None:
                결과 = {"error": f"모르는 도구입니다: {이름}"}
            else:
                try:
                    결과 = fn(**인자)                     # ← 내 컴퓨터에서 실행된다
                except Exception as exc:                            # noqa: BLE001
                    결과 = {"error": f"{type(exc).__name__}: {exc}"}

            요약 = json.dumps(결과, ensure_ascii=False, default=str)
            print(f"      → {요약[:160]}{'…' if len(요약) > 160 else ''}")
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": 요약[:6000]})
        print()

    print("도구를 여러 번 불렀는데 리포트가 안 나왔습니다. 손 드세요.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
