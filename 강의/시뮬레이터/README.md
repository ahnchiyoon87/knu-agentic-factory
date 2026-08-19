# K-정밀 팩토리 시뮬레이터

경남대 RISE 피지컬AI 사관학교 **8월 Agentic AI 특강** (이틀 × 4시간 · 39명).
공장 한 채가 **학생 각자의 PC** 에서 docker compose 로 돈다 — 바깥에 서버가 없다.

하드웨어 없이 「인지 → 판단 → 행동 → 다시 인지」 폐루프를 성립시키는 장치다.
**이틀 실습 전체가 이 위에서 돈다.**

```
CNC 설비 6대 (EQ-01~EQ-06)  온도 · 진동 · rpm · 가동상태
AMR 2대 (AMR-01, AMR-02)    위치 · 배터리 · 적재상태
   ↓ 1초 주기 변동 · 배치 적재
Postgres  ← compose 안의 db 컨테이너 (각자 것)
   ↑
API 서버 (읽기 4종 + 제어 4종 + 「이상 시작」·「제어 열기」)
   ↑
2D 공장 뷰 (Konva.js)  ·  학생이 만드는 대시보드
```

---

## 빠른 시작

```bash
docker compose up -d          # 첫 실행 — 빌드 + 스키마 자동 적용까지 몇 분
# → http://localhost:8000
```

끄기는 `docker compose down`, 초기화는 `docker compose down -v`.
상세는 **[docs/운영.md](docs/운영.md)**, API 는 **[docs/API_명세_인계본.md](docs/API_명세_인계본.md)**,
프로젝트 전체 규칙은 저장소 루트 **핸드오프.md** 가 원본이다.
