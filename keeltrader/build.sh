#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  ./build.sh [all|web|api] [release options]

Build validation uses the same overlay path as production release, but it does
not tag latest, restart services, or run production smoke checks.

Examples:
  ./build.sh
  ./build.sh web
  ./build.sh api --full-build
USAGE
}

target="${1:-all}"
if [ "$#" -gt 0 ]; then
  shift
fi

case "$target" in
  all)
    if [ "$#" -gt 0 ]; then
      usage >&2
      printf '\nExtra release options are only supported for web/api targets.\n' >&2
      exit 2
    fi
    "$ROOT_DIR/scripts/deploy.sh" web --test-only
    "$ROOT_DIR/scripts/deploy.sh" api --test-only
    ;;
  web)
    "$ROOT_DIR/scripts/deploy.sh" web --test-only "$@"
    ;;
  api|backend)
    "$ROOT_DIR/scripts/deploy.sh" api --test-only "$@"
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
