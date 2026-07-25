#!/bin/sh

set -e

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

is_truthy() {
  case "$(to_lower "${1:-}")" in
    1|true|yes|y|on) return 0 ;;
    *) return 1 ;;
  esac
}

run_migrations() {
  echo "[keeltrader] running alembic upgrade..."
  alembic -c /app/alembic.ini upgrade head
}

if is_truthy "${KEELTRADER_RUN_MIGRATIONS:-1}"; then
  run_migrations
fi

if is_truthy "${KEELTRADER_RELOAD:-0}"; then
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
