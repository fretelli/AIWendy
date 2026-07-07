#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
OVERLAY_BASE_IMAGE="${KEELTRADER_API_OVERLAY_BASE_IMAGE:-}"
DEFAULT_BASE_IMAGE="keeltrader-api:base"
FALLBACK_BASE_IMAGE="keeltrader-api:latest"
RUN_TESTS=1
DEPLOY=1
FULL_BUILD=0
SMOKE_ONLY=0
SMOKE_ATTEMPTS="${KEELTRADER_API_SMOKE_ATTEMPTS:-12}"
SMOKE_DELAY_SECONDS="${KEELTRADER_API_SMOKE_DELAY_SECONDS:-5}"

usage() {
  cat <<'USAGE'
Usage: scripts/release-api-overlay.sh [options]

Build and release the KeelTrader API + agent-engine services using the local
overlay image path.

Options:
  --skip-tests   Skip pytest, but still build the production overlay and smoke.
  --no-deploy    Build and validate the image without tagging latest or restarting services.
  --full-build   Build keeltrader-api:base from apps/api/Dockerfile before overlay.
  --smoke-only   Run smoke checks only against the current Compose stack.
  -h, --help     Show this help.

Environment:
  KEELTRADER_API_OVERLAY_BASE_IMAGE  Explicit base image for overlay builds. Default: use keeltrader-api:base, fall back to keeltrader-api:latest.
  KEELTRADER_API_SMOKE_ATTEMPTS      Smoke attempts per check. Default: 12
  KEELTRADER_API_SMOKE_DELAY_SECONDS Delay between smoke attempts. Default: 5
USAGE
}

log() {
  printf '[release-api] %s\n' "$*"
}

die() {
  printf '[release-api] ERROR: %s\n' "$*" >&2
  exit 1
}

run() {
  log "$*"
  "$@"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-tests)
      RUN_TESTS=0
      ;;
    --no-deploy)
      DEPLOY=0
      ;;
    --full-build)
      FULL_BUILD=1
      ;;
    --smoke-only)
      SMOKE_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
  shift
done

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

check_workspace_writable() {
  local probe="$API_DIR/.release-write-check"

  if ! ( : > "$probe" ) 2>/dev/null; then
    die "Workspace is not writable from this shell. Remount/fix the execution namespace first, then rerun this script."
  fi

  rm -f "$probe"
}

resolve_overlay_base_image() {
  if [ -n "$OVERLAY_BASE_IMAGE" ]; then
    if ! docker image inspect "$OVERLAY_BASE_IMAGE" >/dev/null 2>&1; then
      die "Explicit overlay base image not found: $OVERLAY_BASE_IMAGE"
    fi
    log "Using explicit overlay base image: $OVERLAY_BASE_IMAGE"
    return
  fi

  if [ "$FULL_BUILD" -eq 1 ]; then
    OVERLAY_BASE_IMAGE="$DEFAULT_BASE_IMAGE"
    log "Rebuilding overlay base image by request: $OVERLAY_BASE_IMAGE"
    docker build --pull=false \
      -f "$API_DIR/Dockerfile" \
      -t "$OVERLAY_BASE_IMAGE" \
      "$ROOT_DIR"
    return
  fi

  if docker image inspect "$DEFAULT_BASE_IMAGE" >/dev/null 2>&1; then
    OVERLAY_BASE_IMAGE="$DEFAULT_BASE_IMAGE"
    log "Using overlay base image: $OVERLAY_BASE_IMAGE"
    return
  fi

  if docker image inspect "$FALLBACK_BASE_IMAGE" >/dev/null 2>&1; then
    OVERLAY_BASE_IMAGE="$FALLBACK_BASE_IMAGE"
    log "Overlay base $DEFAULT_BASE_IMAGE not found; using $OVERLAY_BASE_IMAGE to avoid dependency-layer rebuild."
    return
  fi

  OVERLAY_BASE_IMAGE="$DEFAULT_BASE_IMAGE"
  log "No reusable overlay base image found; bootstrapping $OVERLAY_BASE_IMAGE without pulling base images."
  docker build --pull=false \
    -f "$API_DIR/Dockerfile" \
    -t "$OVERLAY_BASE_IMAGE" \
    "$ROOT_DIR"
}

build_images() {
  resolve_overlay_base_image

  log "Building API production overlay image without pulling base images from base: $OVERLAY_BASE_IMAGE"
  docker build --pull=false \
    -f "$API_DIR/Dockerfile.overlay" \
    --build-arg OVERLAY_BASE_IMAGE="$OVERLAY_BASE_IMAGE" \
    -t keeltrader-api:test-overlay \
    "$ROOT_DIR"
}

run_quality_checks() {
  if [ "$RUN_TESTS" -eq 0 ]; then
    log "Skipping pytest by request."
    return
  fi

  log "Building one-shot API test image"
  docker build --pull=false \
    -f "$API_DIR/Dockerfile.test" \
    --build-arg API_UNDER_TEST_IMAGE=keeltrader-api:test-overlay \
    -t keeltrader-api:test-runner \
    "$ROOT_DIR"

  run docker run --rm keeltrader-api:test-runner pytest
}

deploy_api() {
  if [ "$DEPLOY" -eq 0 ]; then
    log "Skipping deploy by request."
    return
  fi

  run docker tag keeltrader-api:test-overlay keeltrader-api:latest
  run docker compose up -d api agent-engine
}

container_http_code() {
  local path="$1"

  docker compose exec -T api python - "$path" <<'PY'
import sys
import urllib.error
import urllib.request

path = sys.argv[1]
url = f"http://127.0.0.1:8000{path}"

try:
    with urllib.request.urlopen(url, timeout=5) as response:
        print(response.status)
except urllib.error.HTTPError as exc:
    print(exc.code)
except Exception as exc:
    print(f"error:{exc}")
    sys.exit(1)
PY
}

expect_container_code() {
  local label="$1"
  local expected="$2"
  local path="$3"
  local code
  local attempt

  for attempt in $(seq 1 "$SMOKE_ATTEMPTS"); do
    code="$(container_http_code "$path" 2>/dev/null || true)"

    case ",$expected," in
      *",$code,"*)
        log "smoke ok: $label -> $code"
        return
        ;;
    esac

    if [ "$attempt" -lt "$SMOKE_ATTEMPTS" ]; then
      log "smoke waiting: $label expected [$expected], got ${code:-exec-error} (attempt $attempt/$SMOKE_ATTEMPTS)"
      sleep "$SMOKE_DELAY_SECONDS"
    fi
  done

  die "Smoke failed: $label expected [$expected], got ${code:-exec-error}"
}

expect_compose_service_running() {
  local service="$1"
  local cid
  local running

  cid="$(docker compose ps -q "$service")"
  if [ -z "$cid" ]; then
    die "Smoke failed: $service has no container"
  fi

  running="$(docker inspect -f '{{.State.Running}}' "$cid")"
  if [ "$running" != "true" ]; then
    die "Smoke failed: $service is not running"
  fi

  log "smoke ok: $service running"
}

heartbeat_present() {
  docker compose exec -T api python - <<'PY'
import asyncio
import os
import sys

import redis.asyncio as redis


async def main() -> int:
    client = redis.from_url(os.environ["REDIS_URL"])
    try:
        raw = await client.get("keeltrader:agentos:heartbeat")
    finally:
        await client.aclose()

    if not raw:
        return 1
    print(raw.decode() if isinstance(raw, bytes) else raw)
    return 0


raise SystemExit(asyncio.run(main()))
PY
}

expect_agent_engine_heartbeat() {
  local attempt

  for attempt in $(seq 1 "$SMOKE_ATTEMPTS"); do
    if heartbeat_present >/dev/null 2>&1; then
      log "smoke ok: agent-engine heartbeat"
      return
    fi

    if [ "$attempt" -lt "$SMOKE_ATTEMPTS" ]; then
      log "smoke waiting: agent-engine heartbeat (attempt $attempt/$SMOKE_ATTEMPTS)"
      sleep "$SMOKE_DELAY_SECONDS"
    fi
  done

  die "Smoke failed: agent-engine heartbeat missing"
}

smoke() {
  log "Running smoke checks against local Docker Compose stack"

  expect_compose_service_running api
  expect_compose_service_running agent-engine
  expect_container_code "api health" "200" "/api/health"
  expect_container_code "api liveness" "200" "/api/health/live"
  expect_container_code "agentos health" "200" "/api/v1/agentos/health"
  expect_agent_engine_heartbeat
}

main() {
  require_command docker
  require_command mktemp

  cd "$ROOT_DIR"
  if [ "$SMOKE_ONLY" -eq 1 ]; then
    smoke
    log "Smoke complete."
    return
  fi

  check_workspace_writable
  build_images
  run_quality_checks
  deploy_api
  smoke

  log "Release complete."
}

main "$@"
