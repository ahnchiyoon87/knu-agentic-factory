"""감지 에이전트 — 폐루프의 첫 번째 책임.

    "무엇이 이상한가"만 답한다. 원인도 조치도 여기서 말하지 않는다.

한 가지만 합니다. 그래야 나중에 이 자리만 바꿔 끼울 수 있습니다.
"""

from __future__ import annotations

ROLE = "감지"


# =============================================================================
# 데이터 가져오기 — 이미 되어 있습니다.
# =============================================================================
def _temps(rows: list[dict]) -> list[float | None]:
    """온도만 시간순으로 뽑는다. 결측은 None 그대로 둔다 — 그 자체가 정보다."""
    return [None if r.get("temperature") is None else float(r["temperature"]) for r in rows]


def _mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


# =============================================================================
# ★ 채우는 자리
# =============================================================================
def judge(values: list[float | None], cfg: dict) -> dict | None:
    """온도 시계열 하나를 보고 이상인지 판정한다.

    Args:
        values: 오래된 것부터 정렬된 온도. 결측 자리는 None
        cfg: config.json 의 detect 블록
             drift_delta_c   이 정도(℃) 넘게 올랐으면 드리프트로 본다
             window_samples  한쪽 창에 쓸 샘플 수 (앞뒤 합쳐 이것의 2배만 본다)
             min_samples     이보다 적으면 판정하지 않는다

    Returns:
        정상이면 None
        이상이면 {"kind": "DRIFT", "delta": 1.9, "recent": 63.9, "baseline": 62.0,
                  "detail": "사람이 읽을 한 줄"}

    ──────────────────────────────────────────────────────────────────
    어제 만든 것을 그대로 쓰면 이 드리프트는 안 잡힙니다.

    2일차의 이동창 z-score 는 "창 안에서 튀는 값"을 찾습니다.
    드리프트는 창까지 같이 올라가기 때문에 창 기준으로는 늘 평범합니다.
    시간당 0.5℃ 는 샘플당 0.008℃ — 노이즈(σ 0.35℃)에 묻힙니다.
    어제 k 를 낮춰 봐도 못 잡았고, 오탐만 늘었습니다.

    그래서 오늘은 기준을 바꿉니다. 창 안이 아니라 **창 밖과 비교**합니다.

    할 일은 네 가지입니다.
      1. 결측(None)을 빼고, **가장 최근 window_samples 의 2배**만 남긴다
      2. 남은 값이 min_samples 보다 적으면 None (판정하지 않는다)
      3. 앞뒤로 반씩 나눠, 뒤쪽 평균에서 앞쪽 평균을 뺀다
      4. 그 차이가 drift_delta_c 를 넘으면 DRIFT 로 돌려준다

    ★ 1번을 빠뜨리면 **조치가 먹힌 뒤에도 계속 울립니다.**
      드리프트는 12분치 안에서 짧은 구간일 뿐이라, 긴 창에 묻히면 앞뒤 평균 차이가
      희석되고 — 더 나쁜 것은 **이상이 끝나고 온도가 내려간 뒤에도 그 구간이 창에 남아
      계속 이상이라고 판정한다**는 점입니다. 그러면 감속이 먹혔는지를 화면에서 확인할 수 없습니다.

      **실측** (배속 ×120 · 임계 0.4℃)

          이상이 끝나고        창을 자르면        안 자르면
          ─────────────────────────────────────────────────
          0분                 +1.20℃ 잡음       +0.51℃ 잡음
          180분               조용해짐           +0.52℃ 계속 울림
          300분               조용해짐           +0.52℃ 계속 울림

      자르면 신호가 **+1.2℃ 로 또렷해지고**, 이상이 끝나면 **스스로 조용해집니다.**

    주의
      · 온도가 내려가는 것은 이상이 아닙니다. 조치가 먹힌 것입니다
      · 배속이 1이면 이 드리프트는 원래 안 잡힙니다(샘플 간격이 가상 1초).
        강사에게 배속을 올려 달라고 하세요
      · detail 은 사람이 읽습니다. "EQ-03 최근 63.9℃ (기준 62.0℃, +1.9℃)" 처럼
    ──────────────────────────────────────────────────────────────────
    """
    vals = [v for v in values if v is not None]

    # ── 빈칸 1 ───────────────────────────────────────────────────────────────
    #   ★ 최근 것만 남긴다 — window_samples 의 2배까지.
    #     안 자르면 이상이 끝나 온도가 내려간 뒤에도 그 구간이 남아 계속 울린다
    #     (실측 : 300분 뒤에도 +0.52℃ 로 울렸다). 그러면 감속이 먹혔는지 확인할 수 없다.
    #   쓸 것 :  int(cfg.get("window_samples", 300)) * 2      vals[-cap:]
    cap = ...
    vals = ...

    if len(vals) < int(cfg["min_samples"]):
        return None

    # 창 안이 아니라 창 밖과 비교한다.
    # 드리프트는 창까지 같이 올라가므로 z-score 로는 안 잡힌다 (어제의 결론).
    half = len(vals) // 2

    # ── 빈칸 2 ───────────────────────────────────────────────────────────────
    #   앞 절반의 평균(기준)과 뒤 절반의 평균(최근)을 낸다.
    #   쓸 것 :  vals[:half]   vals[half:]   sum(...)   len(...)
    baseline = ...
    recent = ...

    delta = recent - baseline

    if delta < float(cfg["drift_delta_c"]):
        return None                      # 내려가는 것은 이상이 아니다. 조치가 먹힌 것이다

    return {
        "kind": "DRIFT",
        "delta": round(delta, 2),
        "recent": round(recent, 2),
        "baseline": round(baseline, 2),
        "detail": f"최근 {recent:.1f}℃ (기준 {baseline:.1f}℃, +{delta:.1f}℃ 상승)",
    }


# =============================================================================
# 오케스트레이터가 부르는 자리 — 이미 되어 있습니다.
# =============================================================================
def run(ctx) -> list[dict]:
    """감시 대상 설비를 훑어 이상 목록을 만든다."""
    from agents import 확인
    확인("judge")          # 안 채웠으면 여기서 멈춘다 — 조용히 「이상 없음」으로 끝내지 않는다

    cfg = ctx.cfg["detect"]
    minutes = ctx.cfg["watch"]["minutes"]
    findings: list[dict] = []

    for eq in ctx.cfg["watch"]["equipment"]:
        try:
            rows = ctx.api.readings(eq, minutes=minutes)
        except Exception as exc:                                   # noqa: BLE001
            ctx.log(f"  {eq} 읽기 실패 — {type(exc).__name__}: {exc}")
            continue
        if not rows:
            continue

        try:
            verdict = judge(_temps(rows), cfg)
        except Exception as exc:                                   # noqa: BLE001
            ctx.log(f"  {eq} 판정 실패 — {type(exc).__name__}: {exc}")
            continue

        if verdict:
            findings.append({
                "equipment_id": eq,
                "metric": "temperature",
                "sample_count": len(rows),
                "current_rpm": rows[-1].get("rpm"),
                "run_state": rows[-1].get("run_state"),
                **verdict,
            })

    return findings
