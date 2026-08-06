# Lab 3-3 — MCP 도구화 + 진단 에이전트

경남대 RISE 피지컬AI 사관학교 8월 특강 · Day 3

> **왜 하는가** (교안 원문)
> 알고리즘이 혼자 돌면 스크립트, 에이전트가 도구로 쓰면 지능이 된다.

---

## 준비

```bash
pip install -r requirements.txt
```

`config.json` 의 `student_db` 에 내 Supabase 정보를 넣습니다(Day 2 에서 만든 것).

```bash
python mcp_server.py --check     # 서버 없이 도구만 호출해 본다
python mcp_server.py             # MCP 서버 실행
```

---

## 3단계

**Step 1 (25분)** — `mcp_server.py` 의 ★ **두 자리**를 Claude 와 함께 채웁니다.

| 도구 | 무엇 |
|---|---|
| `detect_anomaly` | **Lab 3-2 에서 내가 짠 `detect()`** 를 에이전트가 부를 수 있게 |
| `query_equipment` | 설비 조회 — 최근 센서 요약 + 정비 이력 |

서버 뼈대·전송 전환·데이터 가져오기는 **이미 되어 있습니다.** 도구 본문만 채우면 됩니다.

**Step 2 (30분)** — 에이전트에게 말로 지시합니다.

> 지난 주 설비 이상을 점검하고, 이상이 있으면 해당 설비의 정비 이력을 조회해
> 원인 추정과 권고 조치를 담은 진단 리포트를 작성하라.

에이전트가 방금 만든 도구들을 줄줄이 이어서 호출하며 리포트를 뽑아냅니다.

**Step 3 (15분)** — 그 리포트를 **Day 1 에 만든 대시보드**에 표시합니다.
3일치 작업이 한 화면에 합쳐집니다. 단, **에이전트는 아직 '제안'만 합니다.**
움직이는 건 내일입니다.

---

## 바꿔 끼우기 — `config.json` 한 곳

현장에서 급히 전환해야 할 때 **이 파일만** 보면 됩니다.

| 항목 | 기본 | 바꾸면 |
|---|---|---|
| `transport` | `stdio` — 내 컴퓨터에서만. 네트워크를 안 타므로 방화벽과 무관 | `http` — 강사가 띄운 공용 서버로 우회 |
| `data_source` | `student` — 내가 Day 2·Lab 3-1 에 만든 것 | `fallback` — 못 끝냈을 때 강사 우회 경로 |

**어느 쪽으로 두든 도구 이름과 응답 형태는 같습니다.** 분기는 `_fetch_*` 함수 안에만 있어서, 강사가 우회시켜도 내가 만든 에이전트 쪽은 고칠 게 없습니다.

`fallback` 일 때 데이터가 오는 곳:

| | 어디서 |
|---|---|
| 센서값 | 나눠받은 **W5 CSV 파일**을 직접 읽습니다 |
| 정비 이력 | **강사 시뮬레이터**의 공용 정비 이력 |

> 센서값을 강사 시뮬레이터에서 가져오지 않는 이유 — 시뮬레이터는 최근 1시간만 보관합니다.
> "지난 주"를 물으려면 7일치가 있는 쪽을 봐야 합니다.

---

## 도구가 돌려주는 것

```json
// detect_anomaly("EQ-03")
{ "equipment_id": "EQ-03", "sample_count": 10080, "anomaly_count": 97,
  "k": 3.0, "window": 60, "anomalies": [ ... ] }

// query_equipment("EQ-03")
{ "equipment_id": "EQ-03",
  "recent": { "temperature": {"avg": 62.02, "max": 64.39}, "missing_count": 0 },
  "maintenance": [
    { "work_order_no": "WO-2026-0801", "status": "IN_PROGRESS",
      "action": "냉각 계통 정기점검", "note": "부품 입고 지연으로 보류. 재개 일자 미정" } ],
  "open_work_orders": [ ... ] }
```

**정비 이력의 `note` 와 미완 작업지시가 진단의 실마리입니다.** 빠뜨리면 에이전트가 원인을 추정할 재료가 없습니다.

---

## 막혔을 때

| 증상 | 원인 | 조치 |
|---|---|---|
| `detect.py 를 불러오지 못했습니다` | Lab 3-2 TODO 가 안 채워짐 | Lab 3-2 를 먼저 끝내세요 |
| `NotImplementedError` | ★ 두 자리가 비어 있음 | `mcp_server.py` 를 채우세요 |
| 401 / 빈 결과 | `student_db` 의 url·key 오타 | Supabase 대시보드에서 다시 복사 |
| 서버가 안 붙음 | 방화벽·포트 | `transport` 를 `http` 로 바꾸고 강사 주소를 넣으세요 |
| Day 2 를 못 끝냄 | 정비 이력 테이블 없음 | `data_source` 를 `fallback` 으로 |

---

## 파일

```
mcp_server.py       ← ★ 두 자리를 채웁니다
config.json         ← 전환은 여기 한 곳
정답/               강사용
verify_lab.py       코드 쪽 검증용
```

> MCP SDK 는 **2.x 기준**으로 작성했습니다. 상위 버전에서 API 가 바뀔 수 있어
> `requirements.txt` 에 고정했습니다. Claude 가 `mcp.server.fastmcp` 를 쓰라고 하면
> 그건 1.x 문법입니다 — 템플릿의 `from mcp.server import MCPServer` 를 그대로 두세요.
