#!/usr/bin/env bash
set -Eeuo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$root_dir/docker-compose.selfhost.yml"
project_name="${KEELTRADER_SELFHOST_PROJECT:-keeltrader-selfhost-smoke}"
env_file="${KEELTRADER_SELFHOST_ENV_FILE:-$root_dir/.env}"
keep="${KEELTRADER_SELFHOST_KEEP:-0}"

[[ -f "$env_file" ]] || { echo "missing self-host env file: $env_file" >&2; exit 1; }
compose=(docker compose -p "$project_name" -f "$compose_file" --env-file "$env_file")

cleanup() {
  if [[ "$keep" != "1" ]]; then
    "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

"${compose[@]}" config --quiet
"${compose[@]}" up -d --build
"${compose[@]}" exec -T api alembic upgrade head

for _ in $(seq 1 30); do
  api_code="$("${compose[@]}" exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready', timeout=5).status)" 2>/dev/null || true)"
  web_code="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/api/health 2>/dev/null || true)"
  if [[ "$api_code" == "200" && "$web_code" == "200" ]]; then
    echo "[selfhost-smoke] API and Web are healthy"
    exit 0
  fi
  sleep 4
done

"${compose[@]}" ps >&2
"${compose[@]}" logs --tail=120 api web agent-platform-worker opportunity-worker >&2
echo "[selfhost-smoke] health deadline exceeded" >&2
exit 1
