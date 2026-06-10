#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

cleanup() {
  docker compose down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> docker compose build"
docker compose build

echo "==> docker compose up -d api"
docker compose up -d api

echo "==> waiting for health..."
ok=0
for _ in $(seq 1 30); do
  sleep 2
  if curl -fsS http://127.0.0.1:8000/health >/tmp/ibd_vn_analytics_health.json; then
    ok=1
    break
  fi
done

if [ "$ok" -ne 1 ]; then
  echo "FAIL: API health check timeout"
  docker compose logs api
  exit 1
fi

echo "OK: /health => $(cat /tmp/ibd_vn_analytics_health.json)"

echo "==> docker compose --profile test run --rm test"
docker compose --profile test run --rm test

echo "==> docker compose --profile cli run --rm cli"
docker compose --profile cli run --rm cli

echo "==> curl data-status"
curl -fsS http://127.0.0.1:8000/api/v1/data-status
echo

echo "ALL PASSED"
