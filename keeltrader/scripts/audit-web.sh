#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"

NPM_AUDIT_REGISTRY="${NPM_AUDIT_REGISTRY:-https://registry.npmjs.org/}"
NPM_AUDIT_LEVEL="${NPM_AUDIT_LEVEL:-high}"
NPM_AUDIT_OMIT="${NPM_AUDIT_OMIT:-dev}"
NPM_AUDIT_FETCH_RETRIES="${NPM_AUDIT_FETCH_RETRIES:-3}"
NPM_AUDIT_FETCH_TIMEOUT="${NPM_AUDIT_FETCH_TIMEOUT:-300000}"

cd "$WEB_DIR"

exec npm audit \
  --audit-level="$NPM_AUDIT_LEVEL" \
  --omit="$NPM_AUDIT_OMIT" \
  --registry="$NPM_AUDIT_REGISTRY" \
  --fetch-retries="$NPM_AUDIT_FETCH_RETRIES" \
  --fetch-retry-mintimeout=10000 \
  --fetch-retry-maxtimeout="$NPM_AUDIT_FETCH_TIMEOUT" \
  --fetch-timeout="$NPM_AUDIT_FETCH_TIMEOUT"
