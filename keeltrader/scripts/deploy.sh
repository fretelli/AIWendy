#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  scripts/deploy.sh web [release-web-overlay options]
  scripts/deploy.sh api [release-api-overlay options]
  scripts/deploy.sh production web|api [release-overlay options]

This repository is deployed on the local Docker Compose host. The old
Vercel/Railway/Fly.io deployment path is intentionally disabled.

Examples:
  scripts/deploy.sh web
  scripts/deploy.sh api
  scripts/deploy.sh web --no-deploy
  scripts/deploy.sh api --skip-tests
USAGE
}

environment="production"
service="${1:-web}"

if [ "$service" = "production" ] || [ "$service" = "staging" ]; then
  environment="$service"
  shift || true
  service="${1:-web}"
else
  shift || true
fi

case "$service" in
  web)
    if [ "$environment" != "production" ]; then
      printf 'Unsupported environment for local Docker deploy: %s\n' "$environment" >&2
      exit 2
    fi
    exec "$ROOT_DIR/scripts/release-web-overlay.sh" "$@"
    ;;
  api|backend)
    if [ "$environment" != "production" ]; then
      printf 'Unsupported environment for local Docker deploy: %s\n' "$environment" >&2
      exit 2
    fi
    exec "$ROOT_DIR/scripts/release-api-overlay.sh" "$@"
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    printf '\nUnsupported service: %s\n' "$service" >&2
    exit 2
    ;;
esac
