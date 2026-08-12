# -*- coding: utf-8 -*-
"""진단 중계 39명 동시 부하 테스트 — 2일차 오후 폐루프의 실제 조건을 재현한다.

    python tools/부하테스트_진단.py                 39명 · 2초 간격 (본번과 같은 조건)
    python tools/부하테스트_진단.py --n 39 --stagger 0    최악(전원 동시)

무엇을 보는가
    ① 39건이 **전부** 성공했는가        — 한 명이라도 실패하면 그 학생만 규칙으로 떨어진다
    ② 응답 시간 (최소·중앙·p95·최대)   — 학생이 얼마나 기다리나
    ③ 429 가 몇 번 났는가              — 한도에 걸렸나
    ④ 실제 소비 토큰 (입력·출력)        — 견적이 맞았나, max_tokens 가 모자라지 않았나
    ⑤ 스키마 위반                      — 원인·근거·조치가 다 나왔나
    ⑥ **정비 이력 인용률**             — WO 번호를 근거로 댄 비율. 2일차 하이라이트가 여기서 갈린다
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
import asyncio
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

import asyncpg
import httpx

ROOT = Path(__file__).resolve().parents[1]

# 폐루프 진단 응답 스키마와 같은 모양 (학생 코드가 보내는 것과 동일)
SCHEMA = {
    "type": "object",
    "properties": {
        "cause": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "actions": {"type": "array", "items": {
            "type": "object",
            "properties": {"command": {"type": "string"}, "equipment_id": {"type": "string"},
                           "rpm": {"type": ["number", "null"]},
                           "robot_id": {"type": ["string", "null"]},
                           "target": {"type": ["string", "null"]},
                           "why": {"type": "string"}},
            "required": ["command", "equipment_id", "rpm", "robot_id", "target", "why"],
            "additionalProperties": False}},
        "summary": {"type": "string"},
    },
    "required": ["cause", "evidence", "severity", "actions", "summary"],
    "additionalProperties": False,
}

SYSTEM = ("너는 제조 설비 진단 담당이다. 준 자료 안에서만 판단한다. "
          "없는 사실을 지어내지 마라. 반드시 스키마대로 답한다.")

USER_TMPL = """설비 {eq} 의 온도가 서서히 오르고 있다.

[감지]
  최근 구간 앞 절반 평균 {a}℃ → 뒤 절반 평균 {b}℃ (차이 +{d}℃)
  이 변화는 지금 작아도 계속 오른다.

[최근 센서 요약 · 24시간]
  온도 평균 {a}℃ · 최대 {mx}℃ · 결측 0건

[정비 이력]
  WO-2026-0801 · 진행중 · 냉각 계통 정기점검
      비고: "부품 입고 지연으로 보류. 재개 일자 미정"

[쓸 수 있는 조치]
  set_equipment_speed(감속, 자동) · ack_alarm(자동)
  stop_equipment(사람 승인) · dispatch_robot(사람 승인)

원인이 정비 보류·지연이면 감속과 함께 로봇 파견 요청까지 낼 것.
파견은 사람이 승인하므로 요청을 망설이지 말 것.
근거(evidence)에는 **작업지시 번호를 그대로 인용**할 것."""


def _env() -> tuple[str, str]:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())
    return os.environ["SUPABASE_DB_URL"], os.environ.get("BASE_URL", "http://127.0.0.1:8000")


async def 키가져오기(dsn: str, n: int) -> list[tuple[str, str]]:
    con = await asyncpg.connect(dsn, timeout=20)
    rows = await con.fetch(
        "select tenant_id, access_key from tenant "
        "where tenant_type='individual' order by tenant_id limit $1", n)
    await con.close()
    return [(r["tenant_id"], r["access_key"]) for r in rows]


async def 한명(client: httpx.AsyncClient, base: str, tid: str, key: str,
             delay: float, max_tokens: int) -> dict:
    await asyncio.sleep(delay)
    eq = "EQ-03"
    body = {"system": SYSTEM,
            "user": USER_TMPL.format(eq=eq, a=62.0, b=62.4, d=0.4, mx=62.9),
            "schema": SCHEMA, "max_tokens": max_tokens}
    t0 = time.perf_counter()
    try:
        r = await client.post(f"{base}/api/v1/{tid}/diagnose",
                              headers={"X-Access-Key": key}, json=body, timeout=120)
        dt = time.perf_counter() - t0
        if r.status_code != 200:
            return {"tid": tid, "ok": False, "sec": dt, "code": r.status_code,
                    "err": r.text[:160]}
        out = r.json()
        본문 = json.dumps(out, ensure_ascii=False)
        필수 = ("cause", "evidence", "severity", "actions", "summary")
        return {"tid": tid, "ok": True, "sec": dt, "code": 200,
                "스키마": all(k in out for k in 필수),
                "WO인용": bool(re.search(r"WO-2026-0801", 본문)),
                "파견요청": "dispatch_robot" in 본문,
                "감속": "set_equipment_speed" in 본문,
                "출력자수": len(본문)}
    except Exception as exc:                                        # noqa: BLE001
        return {"tid": tid, "ok": False, "sec": time.perf_counter() - t0,
                "code": 0, "err": f"{type(exc).__name__}: {exc}"[:160]}


async def main() -> int:
    ap = argparse.ArgumentParser(description="진단 중계 부하 테스트")
    ap.add_argument("--n", type=int, default=39)
    ap.add_argument("--stagger", type=float, default=2.0, help="한 명씩 벌리는 간격(초)")
    ap.add_argument("--max-tokens", type=int, default=1500)
    ap.add_argument("--base", default=None)
    args = ap.parse_args()

    dsn, base = _env()
    base = (args.base or base).rstrip("/")
    사람 = await 키가져오기(dsn, args.n)
    if len(사람) < args.n:
        print(f"테넌트가 {len(사람)}개뿐입니다.")
        return 2

    print("=" * 66)
    print(f"진단 중계 부하 테스트   {len(사람)}명 · {args.stagger:g}초 간격 · "
          f"max_tokens {args.max_tokens}")
    print(f"대상 {base}")
    print("=" * 66)

    t0 = time.perf_counter()
    async with httpx.AsyncClient() as client:
        결과 = await asyncio.gather(*[
            한명(client, base, tid, key, i * args.stagger, args.max_tokens)
            for i, (tid, key) in enumerate(사람)])
    전체 = time.perf_counter() - t0

    성공 = [r for r in 결과 if r["ok"]]
    실패 = [r for r in 결과 if not r["ok"]]
    초 = sorted(r["sec"] for r in 성공)

    print(f"\n① 성공   {len(성공)} / {len(결과)}")
    if 실패:
        print("   실패한 것:")
        for r in 실패[:10]:
            print(f"     {r['tid']}  {r['code']}  {r.get('err','')}")
        코드 = {}
        for r in 실패:
            코드[r["code"]] = 코드.get(r["code"], 0) + 1
        print("   코드별:", 코드)

    if 초:
        def p(q): return 초[min(int(len(초) * q), len(초) - 1)]
        print(f"\n② 응답   최소 {초[0]:.1f}s · 중앙 {statistics.median(초):.1f}s · "
              f"p95 {p(0.95):.1f}s · 최대 {초[-1]:.1f}s")
    print(f"   전체 소요 {전체:.0f}s")

    n429 = sum(1 for r in 실패 if r["code"] == 429)
    print(f"\n③ 429    {n429}건")

    if 성공:
        스키마 = sum(1 for r in 성공 if r["스키마"])
        wo = sum(1 for r in 성공 if r["WO인용"])
        파견 = sum(1 for r in 성공 if r["파견요청"])
        감속 = sum(1 for r in 성공 if r["감속"])
        평균자수 = statistics.mean(r["출력자수"] for r in 성공)
        print(f"\n⑤ 스키마 준수        {스키마}/{len(성공)}")
        print(f"⑥ WO-2026-0801 인용  {wo}/{len(성공)}   ← 2일차 하이라이트")
        print(f"   감속 요청          {감속}/{len(성공)}")
        print(f"   로봇 파견 요청      {파견}/{len(성공)}   ← 승인 화면이 뜨는 조건")
        print(f"\n④ 응답 평균 {평균자수:.0f}자 (JSON 기준)")

    print("\n" + "=" * 66)
    문제 = []
    if 실패:
        문제.append(f"{len(실패)}명 실패")
    if 성공 and sum(1 for r in 성공 if r["WO인용"]) < len(성공) * 0.9:
        문제.append("WO 인용률 90% 미만 — 하이라이트가 갈린다")
    if 성공 and sum(1 for r in 성공 if r["파견요청"]) < len(성공) * 0.9:
        문제.append("파견 요청률 90% 미만 — 승인 화면이 안 뜨는 학생이 생긴다")
    print("판정  " + ("합격 — 39명 전원 같은 장면을 봅니다" if not 문제
                    else "재검토 필요: " + " · ".join(문제)))
    print("=" * 66)
    return 1 if 문제 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
