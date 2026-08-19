# K-정밀 공장 — 학생 1인용. 이 컨테이너와 옆의 DB 컨테이너가 전부다.
#
#   빌드·기동   docker compose up -d       (첫 실행 때 스스로 빌드한다)
#
# 켜질 때마다 스키마를 스스로 맞춘다(migrate up — 이미 맞으면 그냥 지나간다).
# 학생이 DB 를 만지거나 마이그레이션을 알 필요가 없다.

FROM python:3.12-slim

WORKDIR /app

# 의존성 먼저 — 코드만 고쳤을 때 이 층이 캐시로 남는다
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 서버가 실제로 읽는 것만 담는다
COPY server/ server/
COPY web/    web/
COPY config/ config/
COPY db/     db/
COPY tools/migrate.py tools/migrate.py

EXPOSE 8000

# 스키마 맞추고 → 공장 기동
CMD ["sh", "-c", "python tools/migrate.py up && python -m server.run"]
