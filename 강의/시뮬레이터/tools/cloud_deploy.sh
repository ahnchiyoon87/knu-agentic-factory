#!/usr/bin/env bash
# 클라우드 VM 배포 스크립트 — 배포_기동_절차서.md §13 을 한 번에.
#
#   bash tools/cloud_deploy.sh                # 전체: VM 생성 → 프로비저닝 → 헬스체크
#   bash tools/cloud_deploy.sh --status       # 상태·주소 확인만
#   bash tools/cloud_deploy.sh --destroy      # 특강 후 정리 (VM·IP·방화벽 삭제)
#
# 전제: gcloud auth login 완료, 기본 프로젝트 설정됨 (gcloud config set project <ID>)
# 재실행 안전: 이미 있는 리소스는 건너뛴다.

set -euo pipefail

NAME=knu-factory
ZONE=asia-northeast3-a
REGION=asia-northeast3
MACHINE=e2-small
FW=allow-factory-8000
ADDR=knu-factory-ip
HERE="$(cd "$(dirname "$0")/.." && pwd)"   # 특강/시뮬레이터/

say(){ echo; echo "══ $1"; }

if [[ "${1:-}" == "--destroy" ]]; then
  say "정리 — VM·고정IP·방화벽 삭제"
  gcloud compute instances delete "$NAME" --zone="$ZONE" --quiet || true
  gcloud compute addresses delete "$ADDR" --region="$REGION" --quiet || true
  gcloud compute firewall-rules delete "$FW" --quiet || true
  echo "삭제 완료 — 과금 리소스 없음"
  exit 0
fi

if [[ "${1:-}" == "--status" ]]; then
  IP=$(gcloud compute addresses describe "$ADDR" --region="$REGION" --format='value(address)' 2>/dev/null || echo "없음")
  echo "고정 IP: $IP"
  gcloud compute instances describe "$NAME" --zone="$ZONE" --format='value(status)' 2>/dev/null || echo "VM: 없음"
  [[ "$IP" != "없음" ]] && curl -s -m 5 "http://$IP:8000/api/v1/health" | head -c 200 && echo
  exit 0
fi

say "0. API 활성화 (최초 1회, 몇 분 걸릴 수 있음)"
gcloud services enable compute.googleapis.com

say "1. 고정 IP"
gcloud compute addresses describe "$ADDR" --region="$REGION" >/dev/null 2>&1 \
  || gcloud compute addresses create "$ADDR" --region="$REGION"
IP=$(gcloud compute addresses describe "$ADDR" --region="$REGION" --format='value(address)')
echo "   → $IP"

say "2. 방화벽 8000"
gcloud compute firewall-rules describe "$FW" >/dev/null 2>&1 \
  || gcloud compute firewall-rules create "$FW" --allow=tcp:8000 --direction=INGRESS

say "3. VM ($MACHINE, 서울)"
gcloud compute instances describe "$NAME" --zone="$ZONE" >/dev/null 2>&1 \
  || gcloud compute instances create "$NAME" \
       --zone="$ZONE" --machine-type="$MACHINE" \
       --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
       --address="$IP"

say "4. SSH 준비 대기"
for i in $(seq 1 12); do
  gcloud compute ssh "$NAME" --zone="$ZONE" --command="true" 2>/dev/null && break
  sleep 10
done

say "5. 프로비저닝 (패키지·코드·가상환경) — 재실행 안전"
gcloud compute ssh "$NAME" --zone="$ZONE" --command='
  set -e
  sudo apt-get update -qq && sudo apt-get install -y -qq python3.12-venv git > /dev/null
  if [ ! -d knu-agentic-factory ]; then
    git clone -q https://github.com/ahnchiyoon87/knu-agentic-factory.git
  else
    cd knu-agentic-factory && git pull -q && cd ~
  fi
  APP=~/knu-agentic-factory/특강/시뮬레이터
  cd "$APP"
  [ -d .venv ] || python3.12 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
'

say "6. .env 업로드"
# Windows 의 pscp 는 경로에 한글이 있으면 열지 못한다 → 양쪽 다 ASCII 경로로 보내고 원격에서 옮긴다
TMP_LOCAL="${TMPDIR:-/tmp}/factory_env_tmp"
cp "$HERE/.env" "$TMP_LOCAL"
gcloud compute scp "$TMP_LOCAL" "$NAME":"/home/$USER/env_upload" --zone="$ZONE" --quiet
rm -f "$TMP_LOCAL"
gcloud compute ssh "$NAME" --zone="$ZONE" --quiet --command='
  APP=$HOME/knu-agentic-factory/특강/시뮬레이터
  mv ~/env_upload "$APP/.env" && chmod 600 "$APP/.env" && echo "   .env 배치 완료"
'

say "7. 상시 기동 등록 (systemd)"
gcloud compute ssh "$NAME" --zone="$ZONE" --quiet --command='
  APP=$HOME/knu-agentic-factory/특강/시뮬레이터
  sudo tee /etc/systemd/system/factory.service > /dev/null <<UNIT
[Unit]
Description=K-Precision Factory Simulator
After=network-online.target

[Service]
User=$USER
WorkingDirectory=$APP
ExecStart=$APP/.venv/bin/python -m uvicorn server.app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
Environment=PYTHONUTF8=1

[Install]
WantedBy=multi-user.target
UNIT
  sudo systemctl daemon-reload
  sudo systemctl enable --now factory
  sleep 10
  systemctl is-active factory
'

say "8. 헬스체크 (외부 접속)"
sleep 5
curl -s -m 15 "http://$IP:8000/api/v1/health" | head -c 300 && echo

say "완료"
echo "  학생 화면   http://$IP:8000/view?tenant=S01"
echo "  강사 콘솔   http://$IP:8000/console"
echo "  키 배포표(예비 수단)  uv run tools/키배포표.py --base http://$IP:8000"
echo "  ⚠ 로컬 서버와 동시에 켜지 말 것 (절차서 §13-5). 잠재우기: gcloud compute ssh $NAME --zone=$ZONE --command='sudo systemctl stop factory'"
