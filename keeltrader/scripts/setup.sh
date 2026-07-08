#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
NPM_CONFIG_REGISTRY="${NPM_CONFIG_REGISTRY:-https://registry.npmjs.org/}"

echo "============================================"
echo "KeelTrader Development Environment Setup"
echo "============================================"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

echo "Checking prerequisites..."
require_command node
require_command npm
require_command python3

if command -v docker >/dev/null 2>&1; then
  echo "Docker detected. Use scripts/deploy.sh or ./build.sh for container build validation."
else
  echo "Docker not found. Container build validation will be unavailable."
fi

cd "$ROOT_DIR"

echo "Setting up environment files..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Edit DATABASE_URL, REDIS_URL, JWT_SECRET, and model keys before running the API."
else
  echo ".env already exists."
fi

echo "Setting up API dependencies..."
cd "$ROOT_DIR/apps/api"
if [ ! -d venv ]; then
  python3 -m venv venv
  echo "Created apps/api/venv."
fi

# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip --index-url "$PIP_INDEX_URL"
python -m pip install -r requirements.txt --index-url "$PIP_INDEX_URL"
deactivate

echo "Setting up web dependencies..."
cd "$ROOT_DIR/apps/web"
npm ci --registry="$NPM_CONFIG_REGISTRY"

cat <<'NEXT'

============================================
Setup complete.
============================================

Next steps:
1. Edit .env and point DATABASE_URL/REDIS_URL at your actual services.
2. Run API locally:
   cd apps/api && source venv/bin/activate && uvicorn main:app --reload --port 8000
3. Run web locally:
   cd apps/web && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
4. For container build validation, run:
   ./build.sh

This setup script does not start PostgreSQL/Redis or run migrations.
Use make db-migrate only after DATABASE_URL points at the intended database.
NEXT
