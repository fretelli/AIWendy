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
  echo "[keeltrader] bootstrapping database tables..."
  python scripts/bootstrap_projects.py
  if [ $? -eq 0 ]; then
    echo "[keeltrader] bootstrap complete, running alembic upgrade..."
    alembic -c /app/alembic.ini upgrade head 2>&1 || echo "[keeltrader] alembic upgrade had warnings (may be OK if bootstrap handled schema)"
  fi
}

if is_truthy "${KEELTRADER_AUTO_INIT_DB:-1}"; then
  run_migrations
  echo "[keeltrader] auto-init db schema..."
  python scripts/init_db_simple.py
  python scripts/add_journal_tables.py
fi

if is_truthy "${KEELTRADER_AUTO_INIT_TEST_USERS:-0}"; then
  echo "[keeltrader] auto-init test users..."
  python scripts/init_user_simple.py
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
