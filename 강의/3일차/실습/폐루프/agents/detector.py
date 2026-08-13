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
# ★ 여기를 채우세요
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

    ★ 1번을 빠뜨리면 실습 중반부터 드리프트가 안 잡힙니다.
      루프를 오래 돌릴수록 창이 길어지는데, 드리프트는 그 안에서 짧은 구간일 뿐입니다.
      긴 창에 묻히면 앞뒤 평균 차이가 희석돼 임계를 못 넘습니다.
      **실측** — 창을 안 자르면 12분 뒤부터 차이가 +0.50℃ 로 주저앉아 미탐이 됩니다.
      최근 600샘플(=가상 10시간)만 보면 +1.2℃ 로 확실히 잡힙니다.

    주의
      · 온도가 내려가는 것은 이상이 아닙니다. 조치가 먹힌 것입니다
      · 배속이 1이면 이 드리프트는 원래 안 잡힙니다(샘플 간격이 가상 1초).
        강사에게 배속을 올려 달라고 하세요
      · detail 은 사람이 읽습니다. "EQ-03 최근 63.9℃ (기준 62.0℃, +1.9℃)" 처럼
    ──────────────────────────────────────────────────────────────────
    """
    # TODO: 여기를 채우세요
    raise NotImplementedError("judge 를 완성하세요")


# =============================================================================
# 오케스트레이터가 부르는 자리 — 이미 되어 있습니다.
# =============================================================================
def run(ctx) -> list[dict]:
    """감시 대상 설비를 훑어 이상 목록을 만든다."""
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
        except NotImplementedError:
            raise
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
