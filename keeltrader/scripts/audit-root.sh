#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR/.." rev-parse --show-toplevel)"

cd "$REPO_ROOT"

for path in \
  .env.cloud.example \
  DATABASE_MIGRATION.md \
  EXCHANGE_SETTINGS_GUIDE.md \
  FRONTEND_SETUP_COMPLETE.md \
  MARKET_DATA_INTEGRATION.md \
  QUICK_START_EXCHANGES.md \
  package.json \
  package-lock.json; do
  if [ -e "$path" ]; then
    echo "[root-audit] obsolete root path still exists: $path" >&2
    exit 1
  fi
done

if [ "$(readlink keeltrader/README.md 2>/dev/null || true)" != "../README.md" ]; then
  echo "[root-audit] keeltrader/README.md must link to ../README.md" >&2
  exit 1
fi

if ! grep -q "自进化基本面投资研究 AgentOS" README.md; then
  echo "[root-audit] canonical README is missing the fundamental AgentOS description" >&2
  exit 1
fi

if grep -nEi "Wendy Rhodes|trading psychology|AI-powered performance coach" \
  README.md README.zh-CN.md CONTRIBUTING.md SECURITY.md .github/ISSUE_TEMPLATE/*; then
  echo "[root-audit] obsolete product positioning found in public repository surfaces" >&2
  exit 1
fi

git diff --check
"$REPO_ROOT/keeltrader/scripts/check-public-safety.sh"

echo "[root-audit] ok"
