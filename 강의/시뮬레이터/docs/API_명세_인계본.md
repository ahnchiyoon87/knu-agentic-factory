# 팩토리 시뮬레이터 API 명세 — 강의자료 쪽 인계본

경남대 RISE 피지컬AI 사관학교 8월 특강 · 시뮬레이터 API

**용도** — 2일차 §1 Step 1 프롬프트 시드를 강의자료 쪽에서 작성하기 위한 API 사실 자료입니다.
교육 설계(어디까지 떠먹여 줄지, 어떤 문장으로 지시할지)는 이 문서에 넣지 않았습니다.

여기 적힌 값은 전부 **실제로 호출해 받은 응답**입니다. 추정치가 없습니다.

---

## 1. 학생별 네임스페이스를 어떻게 지정하는가

**경로에 넣습니다.** 헤더도 쿼리스트링도 아닙니다.

```
/api/v1/{네임스페이스}/state
```

| 구분 | 값 | 쓰는 날 |
|---|---|---|
| **내 공장** | `S01` (전원 동일 — DB 가 각자 것이라 부딪히지 않습니다) | 2일차 · 3일차 |

- 대문자 고정입니다. `s01` 은 404 입니다.
- 없는 네임스페이스는 `404` + `"'S99' 네임스페이스가 없습니다. /api/v1/tenants 에서 목록을 확인하세요."`
- 전체 목록: `GET /api/v1/tenants`
- 자기 공장 2D 화면: `http://localhost:8000`

배정이 없습니다 — 공장이 학생 PC 에서 하나씩 돌아 전원이 같은 `S01` 입니다.

---

## 2. 인증 — 읽기는 키가 없습니다

| 구간 | 인증 | 이유 |
|---|---|---|
| **읽기 API (2일차)** | **없음** | 2일차 Step 1 의 진입장벽을 없애기 위한 결정입니다. 네임스페이스 이름만 알면 읽힙니다 |
| 제어 API (3일차) | `X-Access-Key` 헤더 | 고정값 `local-lab-key` — 실제 서비스의 인증 형식을 유지하기 위한 것으로, config.json 에 미리 채워져 나갑니다 |
| 「이상 시작」·「제어 열기」 | 없음 (내 공장이라 잠글 상대가 없음) | 화면 버튼 · 제어열기.py |

**2일차 §1 시드에는 인증이 필요 없습니다.** `fetch(url)` 만으로 됩니다.

CORS 는 모든 출처를 허용합니다. 학생이 `index.html` 을 파일로 열어도(`file://`) 읽힙니다.

---

## 3. 엔드포인트

베이스 주소는 강사 PC 의 사설 IP 입니다 — 예: `http://192.168.0.10:8000`

### 2일차 §1 에 필요한 것

| 메서드 | 경로 | 무엇 |
|---|---|---|
| `GET` | `/api/v1/{ns}/state` | **설비 6대 + 로봇 2대 + 알람을 한 번에.** 시드는 이것만 쓰면 됩니다 |

### 그 외 읽기 (Step 2 카드에서 필요해질 수 있음)

| 메서드 | 경로 | 무엇 |
|---|---|---|
| `GET` | `/api/v1/{ns}/equipment` | 설비만 |
| `GET` | `/api/v1/{ns}/equipment/{설비ID}` | 설비 1대 |
| `GET` | `/api/v1/{ns}/robots` | 로봇만 |
| `GET` | `/api/v1/{ns}/alarms?state=OPEN` | 알람 (`OPEN`\|`ACKED`\|`ALL`) |
| `GET` | `/api/v1/{ns}/readings?equipment_id=EQ-03&minutes=30` | 센서 이력 (그래프용) |
| `GET` | `/api/v1/{ns}/robot-readings?robot_id=AMR-01&minutes=30` | 로봇 이동 이력 |
| `GET` | `/api/v1/layout` | 공장 배치도 · AMR 통로 좌표 |
| `GET` | `/api/v1/tenants` | 네임스페이스 목록 |
| `GET` | `/api/v1/health` | 서버 상태 (연결 확인용) |

OpenAPI 문서: `http://<주소>:8000/docs`

> **제어 API 4종은 2일차에 잠겨 있습니다.** 호출하면 `403` 과 함께
> *"제어 통로가 아직 잠겨 있습니다. 3일차 오후에 강사가 엽니다. …"* 가 돌아옵니다.
> 2일차 시드에 제어를 넣지 마십시오.

---

## 4. 권장 폴링 주기 — **2초**

교안 2일차 강사 노트가 *"시뮬레이터 API를 얼마나 자주 불러올지(폴링 주기)를 가이드에 고정해서 적어 두세요"* 라고 지시한 항목입니다.

**시드에 `2000`ms 를 숫자로 박아 주십시오.** "적당히"나 "1~2초" 같은 표현은 피해 주십시오.

| 주기 | 39명 동시 실측 | 판단 |
|---|---|---|
| 1초 | p95 36ms · 에러 0% | 여유는 있으나 권장하지 않음 |
| **2초** | **p95 54ms · 에러 0%** | **권장** |
| 3~5초 | — | 강의장 리허설에서 병목이 나오면 이쪽으로 완화 |

- 서버가 값을 갱신하는 주기는 **1초**입니다. 2초 폴링이면 갱신 두 번에 한 번씩 봅니다.
- 1초 미만으로 내리면 39명 기준 서버 부담이 급증합니다. 시드에 "더 짧게 하지 마라"를 넣어 주십시오.
- 브라우저 캐시 때문에 값이 안 변해 보이는 사례가 있어 `fetch(url, {cache:'no-store'})` 를 권합니다.

---

## 5. 응답 구조

`GET /api/v1/{ns}/state` 하나로 전부 옵니다.

| 최상위 키 | 무엇 |
|---|---|
| `tenant_id` | 네임스페이스 |
| `server_time` | 공장의 시계 (ISO 8601) |
| `equipment` | **CNC 6대** 배열 |
| `robots` | **AMR 2대** 배열 |
| `alarms` | 현재 열린 알람 배열 (없으면 `[]`) |
| `clock` | 가상 시계 · 배속 |
| `control` | 제어 통로 4개와 잠금 상태 |

### `equipment[]` — CNC 6대

| 필드 | 형 | 설명 |
|---|---|---|
| `equipment_id` | string | `EQ-01` ~ `EQ-06` |
| `display_name` | string | 예: `CNC 선반 1호기` |
| `pos_x` `pos_y` | number | 공장 배치 좌표 (1000×600 논리 단위) |
| `temperature` | number \| **null** | ℃ |
| `vibration` | number \| **null** | mm/s |
| `rpm` | number \| **null** | 분당 회전수 |
| `run_state` | string | `RUN` \| `IDLE` \| `STOP` |
| `target_rpm` | number | 지시된 목표 rpm |
| `sensor_online` | boolean | `false` 면 센서 결측 중 |

### `robots[]` — AMR 2대

| 필드 | 형 | 설명 |
|---|---|---|
| `robot_id` | string | `AMR-01`, `AMR-02` |
| `display_name` | string | `정비 AMR`, `운반 AMR` |
| `pos_x` `pos_y` | number | 현재 좌표 |
| `battery` | number | % |
| `payload_state` | string | `EMPTY` \| `LOADED` |
| `status` | string | `IDLE` \| `MOVING` \| `CHARGING` |
| `target_node` | string \| null | 파견 목적지 |
| `eta_seconds` | number | 도착 예상 |

### `alarms[]`

`id` · `equipment_id` · `rule_code`(`TEMP_HIGH`\|`VIB_HIGH`\|`SENSOR_LOSS`) · `severity`(`INFO`\|`WARN`\|`CRITICAL`) · `message` · `value` · `threshold` · `state` · `raised_at`

---

## 6. 반드시 시드에 넣어야 할 것 — `null` 처리

**`temperature` · `vibration` · `rpm` 은 `null` 로 올 때가 있습니다.**
센서 결측 상태이며(7일치 데이터의 6일차 구간), 오류가 아니라 정상적인 값입니다. 이때 `sensor_online` 이 `false` 입니다.

처리하지 않으면 `toFixed()` 에서 예외가 나 **화면이 통째로 죽습니다.**
라이브에서 결측이 안 생기더라도, 시드에 넣어 두면 3일차까지 같은 대시보드를 씁니다.

결측 중 실제 응답:

```json
{ "equipment_id": "EQ-01", "temperature": null, "vibration": null,
  "rpm": null, "run_state": "RUN", "sensor_online": false }
```

---

## 7. 실제 응답 1건

`GET /api/v1/S01/state` — 2026-08-04 실측. 설비는 6대 중 2대만 실었습니다(나머지는 같은 형태).

```json
{
  "tenant_id": "S01",
  "server_time": "2026-08-04T13:52:53.594206+00:00",
  "equipment": [
    {
      "equipment_id": "EQ-01",
      "display_name": "CNC 선반 1호기",
      "pos_x": 150.0,
      "pos_y": 140.0,
      "temperature": 62.164,
      "vibration": 1.934,
      "rpm": 1797.4,
      "run_state": "RUN",
      "target_rpm": 1800.0,
      "sensor_online": true
    },
    {
      "equipment_id": "EQ-02",
      "display_name": "CNC 선반 2호기",
      "pos_x": 400.0,
      "pos_y": 140.0,
      "temperature": 67.842,
      "vibration": 2.219,
      "rpm": 1998.6,
      "run_state": "RUN",
      "target_rpm": 2000.0,
      "sensor_online": true
    }
  ],
  "robots": [
    {
      "robot_id": "AMR-01",
      "display_name": "정비 AMR",
      "pos_x": 880.0,
      "pos_y": 520.0,
      "battery": 100.0,
      "payload_state": "EMPTY",
      "status": "IDLE",
      "target_node": null,
      "eta_seconds": 0.0
    },
    {
      "robot_id": "AMR-02",
      "display_name": "운반 AMR",
      "pos_x": 880.0,
      "pos_y": 120.0,
      "battery": 100.0,
      "payload_state": "EMPTY",
      "status": "IDLE",
      "target_node": null,
      "eta_seconds": 0.0
    }
  ],
  "alarms": [],
  "clock": {
    "time_scale": 1.0,
    "virtual_time": "2026-08-04T13:52:53.594206+00:00",
    "real_time": "2026-08-04T13:52:53.722841+00:00",
    "real_tick_seconds": 1.0,
    "virtual_step_seconds": 1.0
  },
  "control": {
    "unlocked": false,
    "opens_on": "3일차 오후",
    "channels": [
      { "name": "set_equipment_speed", "label": "설비 속도 조절",
        "signature": "set_equipment_speed(id, rpm)" },
      { "name": "stop_equipment", "label": "설비 정지",
        "signature": "stop_equipment(id)" },
      { "name": "dispatch_robot", "label": "로봇 파견",
        "signature": "dispatch_robot(robot_id, target)" },
      { "name": "ack_alarm", "label": "알람 확인 처리",
        "signature": "ack_alarm(id)" }
    ]
  }
}
```

---

## 8. 참고 — 값의 성질

시드 문구를 정할 때 알고 계시면 좋은 사실입니다.

- **설비마다 정상 온도가 다릅니다.** EQ-04 56℃ ~ EQ-05 75℃. 하나의 임계값으로 6대를 다 덮을 수 없습니다
- 값에는 가우시안 노이즈가 있습니다(온도 σ=0.35℃). 매 초 조금씩 흔들립니다
- 온도는 rpm 의 함수입니다. 3일차에 감속하면 온도가 실제로 내려갑니다
- `clock.time_scale` 이 1보다 크면 강사가 배속 시연 중입니다. 2일차 학생 실습은 항상 `1` 입니다

---

## 9. Step 2 요구사항 카드 5장 — API 대응

> ⚠ **과거 기록** — 요구사항 카드는 4일 과정·팀 단위 시절 것으로 **개인 단위 전환 때 폐지**됐습니다.
> API 가 왜 이 모양인지의 이력으로만 남깁니다.

카드 4·5 에 대응 API 가 **없는 것은 의도된 것**입니다(교안이 뒷날 스펙으로 다시 풀게 설계).

| # | 카드 | 필요한 API |
|---|---|---|
| 1 | 온도 임계 알람 표시 | `state` 의 `temperature` |
| 2 | 설비별 이력 그래프 | `readings?equipment_id=&minutes=` |
| 3 | AMR 경로 표시 | `layout` + `state` 의 `pos_x/pos_y` |
| 4 | 알람 담당자 배정 | **없음** — 학생이 만듭니다 |
| 5 | 야간모드/권한 분리 | **없음** |

---

## 10. 연결이 안 될 때 (강사 트러블슈팅)

| 증상 | 원인 | 조치 |
|---|---|---|
| `Failed to fetch` | 주소·포트 오타 또는 서버 미기동 | 브라우저로 `/api/v1/health` 를 직접 열어 확인 |
| `404 네임스페이스가 없습니다` | 소문자 등 오타 | 대문자 `S01` 형식 |
| 값이 안 변함 | 브라우저 캐시 | `{cache:'no-store'}` |
| 전부 `null` | 센서 결측 주입 중 | (이번 특강 버튼은 드리프트만 겁니다) |
| `403` | 제어 API 호출 | 2일차 에는 잠겨 있음. 읽기만 쓸 것 |

---

**변경 이력** — API 가 바뀌면 이 문서를 갱신해 다시 드립니다.
현재 기준: `clock` · `control` 필드 포함 (2일차 공장 화면의 시계·제어 통로 칸 대응으로 추가됨).
