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

if [ "$(to_lower "${ENVIRONMENT:-development}")" = "production" ]; then
  run_migrations
elif is_truthy "${KEELTRADER_AUTO_INIT_DB:-1}"; then
  run_migrations
  echo "[keeltrader] auto-init db schema..."
  python scripts/bootstrap_projects.py
  python scripts/init_db_simple.py
  python scripts/add_journal_tables.py
fi

if [ "$(to_lower "${ENVIRONMENT:-development}")" = "production" ]; then
  if is_truthy "${KEELTRADER_AUTO_INIT_TEST_USERS:-0}"; then
    echo "[keeltrader] ignoring KEELTRADER_AUTO_INIT_TEST_USERS in production"
  fi
elif is_truthy "${KEELTRADER_AUTO_INIT_TEST_USERS:-0}"; then
  echo "[keeltrader] auto-init test users..."
  python scripts/init_user_simple.py
fi

if is_truthy "${KEELTRADER_RELOAD:-0}"; then
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
