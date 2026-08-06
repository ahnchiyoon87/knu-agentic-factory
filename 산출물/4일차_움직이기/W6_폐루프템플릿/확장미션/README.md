# 확장 미션 — 폐루프에 **새 에이전트 1개**를 추가한다

기본 미션(감지 → 진단 → 조치)이 돌기 시작하면, 여기부터입니다.

> **오늘의 증명은 "돌았다"가 아니라 "내가 확장할 수 있다"입니다.**

평가는 **폐루프가 실제로 도는지 40점 / 스펙 문서화 30점 / 창의성 30점** 입니다.
확장 미션은 **가점**입니다 — 기본 미션이 먼저입니다.
`스펙_템플릿.md` 를 채우면 30점짜리 항목이 같이 해결됩니다.

---

## 붙이는 법 — 세 줄

**1.** `agents/` 안에 파일을 만듭니다.

```python
# agents/shift_report.py
ROLE = "교대 리포트"

def run(ctx, record):
    ...
    return {"무엇이든": "돌려주면 실행기록에 남습니다"}
```

**2.** `agents/__init__.py` 아래쪽에 등록합니다.

```python
from . import shift_report
EXTRA = [shift_report]
```

**3.** 끝입니다. `python loop.py --once` 를 다시 돌리면 매 회차 끝에 불립니다.

`loop.py` 는 **고치지 않습니다.** 오케스트레이터는 등록표만 봅니다 — 그게 이 패턴의 요점입니다.

---

## 손에 쥐는 것

| | 무엇 |
|---|---|
| `ctx.api` | 공장을 **읽는** 창구 — `state()` `readings()` `maintenance()` `alarms()` |
| `ctx.control` | 공장을 **움직이는** 통로 — MCP 도구 4개 |
| `ctx.cfg` | `config.json` 전부 |
| `ctx.log(문장)` | 화면과 기록에 동시에 남습니다 |
| `record` | **그 회차에 일어난 전부** (아래) |

```python
record = {
  "round": 3, "at": "2026-08-...",
  "findings": [ {"equipment_id": "EQ-03", "kind": "DRIFT", "delta": 1.9, ...} ],
  "cases": [
    { "finding":   {...},
      "diagnosis": {"cause": ..., "evidence": [...], "severity": "LOW|MEDIUM|HIGH",
                    "actions": [...], "summary": ..., "backend": "claude"},
      "actions":   [{"command": "set_equipment_speed", "target": "EQ-03",
                     "status": "EXECUTED|DENIED|FAILED", "mode": "AUTO|APPROVED", ...}] }
  ]
}
```

지난 회차까지 보려면 `실행기록.jsonl` 을 읽으십시오. 한 줄에 한 회차입니다.

---

## 다섯 갈래 — 교안 원문과, 무엇으로 만드는가

### A. 예방정비 스케줄러
> **이상이 얼마나 자주 났는지와 가동시간을 근거로 정비 작업지시를 자동으로 발행**

| 필요한 것 | 어디서 |
|---|---|
| 이상 발생 빈도 | `실행기록.jsonl` 의 `findings` 를 설비별로 세면 됩니다 |
| 가동시간 | `ctx.api.readings(eq, minutes=N)` 의 `run_state` 가 `RUN` 인 샘플 수 |
| 기존 작업지시 | `ctx.api.maintenance(eq)` — 이미 발행된 것과 겹치지 않게 |

붙는 자리: `EXTRA`. **주의** — "발행"은 우리 팀 기록(파일·표)에 남기는 것으로 충분합니다.
시뮬레이터에는 작업지시를 만드는 통로가 없습니다(정비 이력은 읽기 전용입니다).

### B. AMR 작업 할당 — Routing 패턴
> **정비나 운반 요청이 들어오면 배터리와 거리를 따져 가장 적합한 로봇을 배차**

| 필요한 것 | 어디서 |
|---|---|
| 배터리 | `ctx.api.state()["robots"][i]["battery"]` |
| 현재 위치 | 같은 곳의 `pos_x`, `pos_y` · 지금 하는 일은 `status`, `target_node` |
| 설비 위치 | `GET /api/v1/layout` 의 `equipment[].pos_x/pos_y` |
| 배차 | `ctx.control.dispatch_robot(robot_id, target)` |

붙는 자리: **조치 에이전트를 우리 것으로 교체**하는 편이 낫습니다.
진단이 `dispatch_robot` 을 낼 때 로봇을 고르는 일이라, 회차 끝(`EXTRA`)에서는 이미 늦습니다.

> 파견은 **승인 대상**입니다. `hitl.ask()` 를 반드시 거치게 하십시오.

### C. 안전 인터록 — Parallelization 패턴
> **이상 등급이 '심각'이면 옆에 붙은 설비들까지 연달아 감속시키고 전체 승인을 요청**

| 필요한 것 | 어디서 |
|---|---|
| 이상 등급 | `diagnosis["severity"] == "HIGH"` |
| **옆에 붙은 설비** | `GET /api/v1/layout` 의 좌표로 계산합니다 (아래) |
| 연달아 감속 | `ctx.control.set_equipment_speed()` 를 여러 대에 |

공장은 3열 × 2행입니다. 좌표로 이웃이 나옵니다.

```
EQ-01(150,140)  EQ-02(400,140)  EQ-03(650,140)
EQ-04(150,400)  EQ-05(400,400)  EQ-06(650,400)
```

> **여기가 이 미션의 핵심 논점입니다.** 감속은 원래 자동입니다.
> 그런데 교안은 인터록의 연쇄 감속에 **"전체 승인을 요청"** 하라고 합니다.
> 한 대 감속과 여러 대 동시 감속은 되돌리기 난이도가 다르기 때문입니다.
> `hitl.ask()` 를 **묶음 단위로** 한 번 부르십시오. 그 판단을 데모에서 설명하면 창의성 점수가 붙습니다.

붙는 자리: **조치 앞**. `agents/__init__.py` 의 `ACT` 를 우리 것으로 바꾸고,
그 안에서 원래 조치를 부르기 전에 검사하는 것이 가장 짧은 길입니다.

### D. 교대 리포트
> **교대 시점마다 지난 8시간의 이상과 조치를 요약한 리포트를 자동 작성**

| 필요한 것 | 어디서 |
|---|---|
| 지난 8시간 | `실행기록.jsonl` 의 `at`(회차 시각)으로 자릅니다 |
| **공장 시각** | `ctx.api.state()["clock"]` — 배속이 걸려 있으면 실제 8분이 공장 8시간입니다 |
| 이상·조치 | 그 구간 `record` 들의 `findings` / `cases` |

붙는 자리: `EXTRA`. `예시_교대리포트.py` 가 **한 회차분** 최소 형태입니다.
여기서 시작해 **8시간 구간 누적**으로 키우면 교안 요구를 채웁니다.

### 자유 주제
강사 승인이 필요합니다.

---

## 승인 규칙은 확장해도 그대로입니다

새 에이전트가 `ctx.control.stop_equipment(...)` 를 **직접** 부르면 승인 관문을 건너뜁니다.
되돌릴 수 없는 행동은 반드시 `hitl.ask()` 를 거치게 하십시오.

```python
import hitl

d = hitl.ask("dispatch_robot", "AMR-02", "AMR-02 → EQ-05 로 이동", "적재 대기 해소")
if d.allowed:
    ctx.control.dispatch_robot("AMR-02", "EQ-05")
```

---

`예시_교대리포트.py` 에 D 의 최소 형태가 있습니다. `agents/` 로 복사해 쓰십시오.
