#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  ./build.sh [all|web|api]

Build validation is self-contained and never deploys to a maintainer-operated
environment.

Examples:
  ./build.sh
  ./build.sh web
  ./build.sh api
USAGE
}

target="${1:-all}"
shift || true
if [ "$#" -gt 0 ]; then usage >&2; exit 2; fi

case "$target" in
  all)
    docker compose -f "$ROOT_DIR/docker-compose.selfhost.yml" build web
    "$ROOT_DIR/scripts/check-api-docker.sh"
    ;;
  web)
    docker compose -f "$ROOT_DIR/docker-compose.selfhost.yml" build web
    ;;
  api|backend)
    "$ROOT_DIR/scripts/check-api-docker.sh"
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    printf '\nUnsupported build target: %s\n' "$target" >&2
    exit 2
    ;;
esac
