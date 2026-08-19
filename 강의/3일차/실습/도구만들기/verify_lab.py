"""3일차 오전 템플릿 검증 — 코드 쪽 품질 게이트.

3일차 오전이 요구하는 것이 이 템플릿 위에서 실제로 성립하는지 확인한다.

    Step 1 — MCP 도구 2개(detect_anomaly, query_equipment)로 내놓는다
    Step 2 — 에이전트가 도구를 줄줄이 호출해 원인 추정과 권고 조치를 담은 리포트를 쓴다
    강사노트 — 로컬 stdio 가 막히면 강사가 띄운 공용 서버로 우회할 경로

MCP 서버를 실제로 띄우고 클라이언트로 붙어 도구를 호출한다.
"함수가 있다"와 "에이전트가 부를 수 있다"는 다르다.

    uv run verify_lab.py
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

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "정답"))

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'통과' if ok else '실패'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def set_cfg(**kw) -> dict:
    p = ROOT / "config.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg.update(kw)
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


async def via_mcp(script: Path) -> tuple[list[str], dict, dict]:
    """MCP 서버를 띄우고 클라이언트로 붙어 도구를 호출한다."""
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    # MCP 는 자식 프로세스에 환경변수를 걸러서 넘긴다 — 필요한 것은 명시해야 전달된다
    child_env = {**os.environ}
    params = StdioServerParameters(command=sys.executable, args=[str(script)],
                                   cwd=str(ROOT), env=child_env)
    with open(ROOT / "_verify_server.log", "w", encoding="utf-8") as errlog:
        async with stdio_client(params, errlog=errlog) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = [t.name for t in (await s.list_tools()).tools]
                d = await s.call_tool("detect_anomaly", {"equipment_id": "EQ-03"})
                q = await s.call_tool("query_equipment", {"equipment_id": "EQ-03"})
                return tools, _payload(d), _payload(q)


def _payload(res) -> dict:
    """도구 결과를 꺼낸다. 에이전트가 실제로 받는 형태(JSON 텍스트)를 그대로 읽는다."""
    if getattr(res, "structured_content", None):
        return res.structured_content
    for c in res.content or []:
        text = getattr(c, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
    return {}


def main() -> int:
    print("=" * 74)
    print("3일차 오전 MCP 도구 템플릿 검증")
    print("=" * 74)

    # 원문 그대로 되돌린다. 다시 직렬화하면 들여쓰기·끝 개행이 달라져
    # 검증을 돌릴 때마다 학생 파일이 바뀐 것처럼 보인다.
    original = (ROOT / "config.json").read_text(encoding="utf-8")
    try:
        set_cfg(data_source="fallback", transport="stdio")

        # ---------------------------------------------------------- 1. 템플릿
        print("\n1. 템플릿 — 학생이 처음 열었을 때")
        import mcp_server
        # 채울 자리는 `raise` 가 아니라 **주석 블록**이다. 빈 함수는 조용히 None 을
        # 돌려주므로 「막혀 있는가」를 예외로는 못 본다 — 소스를 읽어 판정한다.
        빈것 = mcp_server.안채운도구()
        check("채울 자리 2곳이 빈 채로 나간다 (학생이 처음 여는 상태)",
              sorted(빈것) == ["detect_anomaly", "query_equipment"],
              f"{len(빈것)}/2 — {' · '.join(빈것) or '없음'}")
        서버소스 = (ROOT / "mcp_server.py").read_text(encoding="utf-8")
        check("빈칸 표식이 자리마다 하나씩 걸린다 (`빈칸 1` … `빈칸 4`)",
              all(서버소스.count(t) == 1
                  for t in ("빈칸 1", "빈칸 2", "빈칸 3", "빈칸 4")),
              " · ".join(f"{t}:{서버소스.count(t)}"
                         for t in ("빈칸 1", "빈칸 2", "빈칸 3", "빈칸 4")))
        check("`--check` 가 빈 도구를 「정상」이라 하지 않는다 (조용한 실패 금지)",
              "안채운도구()" in 서버소스 and "아직 안 채움" in 서버소스)
        check("2일차의 detect() 를 그대로 가져다 쓴다 — '내가 짠 알고리즘을 AI가 쓴다'",
              "from detect import detect" in (ROOT / "mcp_server.py").read_text(encoding="utf-8"))
        check("서버 뼈대·전송 전환은 이미 되어 있다 (학생은 본문만 채우면 된다)",
              "mcp.run(transport=" in (ROOT / "mcp_server.py").read_text(encoding="utf-8"))

        # ------------------------------------------------- 2. MCP 로 실제 호출
        print("\n2. MCP 서버를 띄우고 클라이언트로 붙어 본다 (참고 답안)")

        # 정비 이력·작업지시는 내 공장(docker)에서 온다. 공장이 꺼져 있으면 뒤 3항목이
        # 「실패」로 뜨는데, 그때 강사는 템플릿이 깨진 줄 안다. 먼저 짚어 준다.
        서버 = os.environ.get("SHARED_API", "http://127.0.0.1:8000").rstrip("/")
        try:
            httpx.get(f"{서버}/api/v1/health", timeout=3).raise_for_status()
        except Exception:                                              # noqa: BLE001
            print(f"  ※ 공장({서버})이 안 켜져 있습니다.")
            print("     정비 이력·작업지시를 못 읽어 아래 3항목이 실패로 나옵니다.")
            print("     템플릿 문제가 아닙니다 — 서버를 켜고 다시 돌리세요:")
            print("       cd 특강/시뮬레이터 && uv run python -m server.run")

        answer = ROOT / "정답" / "mcp_server_answer.py"
        tools, d, q = asyncio.run(via_mcp(answer))
        check("도구 2개가 등록된다", sorted(tools) == ["detect_anomaly", "query_equipment"],
              ", ".join(sorted(tools)))
        check("detect_anomaly 가 7일치를 실제로 검사한다", d.get("sample_count", 0) > 9000,
              f"{d.get('sample_count')}개 샘플 · 이상 {d.get('anomaly_count')}건")
        check("query_equipment 가 센서 요약과 정비 이력을 함께 준다",
              bool(q.get("recent")) and bool(q.get("maintenance")),
              f"정비 이력 {len(q.get('maintenance', []))}건")

        # -------------------------------------------- 3. 진단 재료가 되는가
        print("\n3. Step 2 의 '원인 추정과 권고 조치'가 가능한 재료인가")
        opens = q.get("open_work_orders", [])
        check("미완 작업지시가 드러난다 — 원인 추정의 실마리", bool(opens),
              opens[0]["action"] + " / " + (opens[0].get("note") or "") if opens else "없음")
        notes = " ".join((m.get("note") or "") for m in q.get("maintenance", []))
        check("정비 이력의 note 가 살아 있다", len(notes) > 20, notes[:60] + "…")

        # ------------------------------------------------------ 4. 우회 경로
        print("\n4. 강사 노트 — 우회 경로가 설정 한 곳으로 바뀌는가")
        cfg_txt = (ROOT / "config.json").read_text(encoding="utf-8")
        check("전송 전환이 config.json 안에 있다", '"transport"' in cfg_txt)
        check("데이터 출처 전환이 config.json 안에 있다", '"data_source"' in cfg_txt)
        src = (ROOT / "mcp_server.py").read_text(encoding="utf-8")
        check("도구 이름·응답 형태는 출처와 무관하다 — 학생 코드를 안 고쳐도 된다",
              src.count('CFG["data_source"]') == 2 and "def detect_anomaly" in src,
              "분기는 _fetch_* 안에만 있다")

        set_cfg(transport="http")
        check("http 로 바꿔도 서버가 기동 설정을 읽는다",
              json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["transport"] == "http")
        set_cfg(transport="stdio")

    finally:
        (ROOT / "config.json").write_text(original, encoding="utf-8")
        (ROOT / "_verify_server.log").unlink(missing_ok=True)

    print("\n" + "=" * 74)
    if failures:
        print(f"실패 {len(failures)}건: " + ", ".join(failures))
        return 1
    print("전 항목 통과 — 3일차 오전이 이 템플릿 위에서 성립합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
