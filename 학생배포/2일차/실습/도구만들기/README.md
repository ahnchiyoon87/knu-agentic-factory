# 2일차 오전 — 내 코드를 MCP 도구로 내놓기

경남대 RISE 피지컬AI 사관학교 8월 특강 · 2일차

> **왜 하는가** (교안 원문)
> 알고리즘이 혼자 돌면 스크립트, 에이전트가 도구로 쓰면 지능이 된다.

---

## 준비

```bash
pip install -r requirements.txt
```

`config.json` 의 `data_source` 가 `fallback` 인지 확인하고, `fallback` 안의
`shared_api` 와 `tenant` 는 **`1일차/실습` 의 `python 내번호.py` 가 자동으로 채웁니다.**

```bash
python mcp_server.py --check     # 서버 없이 도구만 호출해 본다
python mcp_server.py             # MCP 서버 실행
```

---

## 3단계

**Step 1 (25분)** — `mcp_server.py` 의 ★ **두 자리**를 채웁니다.
막히면 `python 점검.py --힌트 1` → `--힌트 2` → `--열기 1`.

| 도구 | 무엇 |
|---|---|
| `detect_anomaly` | **1일차에 내가 짠 `detect()`** 를 에이전트가 부를 수 있게 |
| `query_equipment` | 설비 조회 — 최근 센서 요약 + 정비 이력 |

서버 뼈대·전송 전환·데이터 가져오기는 **이미 되어 있습니다.** 도구 본문만 채우면 됩니다.

**Step 2 (30분)** — 에이전트에게 말로 지시합니다.

> 지난 주 설비 이상을 점검하고, 이상이 있으면 해당 설비의 정비 이력을 조회해
> 원인 추정과 권고 조치를 담은 진단 리포트를 작성하라.

에이전트가 방금 만든 도구들을 줄줄이 이어서 호출하며 리포트를 뽑아냅니다.

**여기까지는 에이전트가 '제안'만 합니다.** 리포트가 “속도를 낮추라”고 권고해도
공장은 그대로 돕니다. **움직이는 것은 오후 실습입니다.**

---

## 바꿔 끼우기 — `config.json` 한 곳

현장에서 급히 전환해야 할 때 **이 파일만** 보면 됩니다.

| 항목 | 기본 | 바꾸면 |
|---|---|---|
| `data_source` | **`fallback` — 이번 특강의 정상 경로(기본값)** | `student` — 개인 DB 를 따로 만든 경우에만 |

**어느 쪽으로 두든 도구 이름과 응답 형태는 같습니다.** 분기는 `_fetch_*` 함수 안에만 있어서,
출처가 바뀌어도 내가 만든 도구 쪽은 고칠 게 없습니다.

`fallback` 일 때 데이터가 오는 곳:

| | 어디서 |
|---|---|
| 센서값 | 나눠받은 **7일치 CSV 파일**을 직접 읽습니다 |
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
| `detect.py 를 불러오지 못했습니다` | 1일차 TODO 가 안 채워짐 | `1일차/실습` 을 먼저 끝내세요 |
| `NotImplementedError` | ★ 두 자리가 비어 있음 | `mcp_server.py` 를 채우세요 |
| 401 / 빈 결과 | `shared_api` 주소 오타 | `1일차/실습` 에서 `python 내번호.py` 를 다시 치세요 |
| 서버가 안 붙음 | 방화벽·포트 | `python mcp_server.py --check` 로 도구만 먼저 확인 → 손 들기 |
| 정비 이력이 빈 배열로 옴 | `shared_api` 가 `127.0.0.1` | `1일차/실습` 에서 `python 내번호.py` |

---

## 파일

```
mcp_server.py       ← ★ 두 자리를 채웁니다
점검.py              막혔을 때 — 어디까지 됐는지 짚어 줍니다
config.json         ← 전환은 여기 한 곳
정답/               시간이 다 됐을 때 `점검.py --열기` 가 읽는 완성본
```

> MCP SDK 는 **2.x 기준**으로 작성했습니다. 상위 버전에서 API 가 바뀔 수 있어
> `requirements.txt` 에 고정했습니다. `mcp.server.fastmcp` 는 1.x 문법이라 쓰지 않습니다 —
> 템플릿의 `from mcp.server import MCPServer` 를 그대로 두세요.
