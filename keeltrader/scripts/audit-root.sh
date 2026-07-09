#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR/.." rev-parse --show-toplevel)"

NPM_AUDIT_REGISTRY="${NPM_AUDIT_REGISTRY:-https://registry.npmjs.org/}"
NPM_AUDIT_LEVEL="${NPM_AUDIT_LEVEL:-high}"
NPM_AUDIT_FETCH_RETRIES="${NPM_AUDIT_FETCH_RETRIES:-3}"
NPM_AUDIT_FETCH_TIMEOUT="${NPM_AUDIT_FETCH_TIMEOUT:-120000}"

cd "$REPO_ROOT"

exec npm audit \
  --audit-level="$NPM_AUDIT_LEVEL" \
  --registry="$NPM_AUDIT_REGISTRY" \
  --fetch-retries="$NPM_AUDIT_FETCH_RETRIES" \
  --fetch-retry-mintimeout=10000 \
  --fetch-retry-maxtimeout="$NPM_AUDIT_FETCH_TIMEOUT" \
  --fetch-timeout="$NPM_AUDIT_FETCH_TIMEOUT"

