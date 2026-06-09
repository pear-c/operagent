#!/bin/sh
# 베이스라인 트래픽: GET/POST를 섞어 약 10~20rps 발생.
# 메트릭이 0이 아니어야 에러율 rule(rate/rate)이 0/0=NaN이 되지 않고 "정상 대비 이상"으로 판정된다.
set -eu
BASE="http://demo-service:8080"

echo "[load-gen] 시작 — target=$BASE"
until curl -sf "$BASE/healthz" >/dev/null 2>&1; do
  echo "[load-gen] demo-service 대기..."
  sleep 2
done
echo "[load-gen] demo-service ready"

while true; do
  curl -sf "$BASE/api/orders" >/dev/null 2>&1 || true
  curl -sf -X POST "$BASE/api/orders" \
    -H 'Content-Type: application/json' \
    -d '{"item":"widget","qty":1}' >/dev/null 2>&1 || true
  sleep 0.1
done
