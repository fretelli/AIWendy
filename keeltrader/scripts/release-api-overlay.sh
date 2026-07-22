#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_SCOPE="release-api"
source "$ROOT_DIR/scripts/lib/release-common.sh"
load_release_env_file "$ROOT_DIR"
init_release_metadata "$ROOT_DIR"
API_DIR="$ROOT_DIR/apps/api"
OVERLAY_BASE_IMAGE="${KEELTRADER_API_OVERLAY_BASE_IMAGE:-}"
DEFAULT_BASE_IMAGE="keeltrader-api:base"
FALLBACK_BASE_IMAGE="keeltrader-api:latest"
RUN_TESTS=1
DEPLOY=1
FULL_BUILD=0
SMOKE_ONLY=0
TEST_ONLY=0
SMOKE_ATTEMPTS="${KEELTRADER_API_SMOKE_ATTEMPTS:-12}"
SMOKE_DELAY_SECONDS="${KEELTRADER_API_SMOKE_DELAY_SECONDS:-5}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"

usage() {
  cat <<'USAGE'
Usage: scripts/release-api-overlay.sh [options]

Build and release the KeelTrader API + Agent Platform worker using the local
overlay image path.

Options:
  --skip-tests   Skip pytest, but still build the production overlay and smoke.
  --test-only    Build the production overlay and one-shot test image, then run pytest without deploy or smoke.
  --no-deploy    Build and validate the image without tagging latest or restarting services.
  --full-build   Build keeltrader-api:base from apps/api/Dockerfile before overlay.
  --smoke-only   Run smoke checks only against the current Compose stack.
  -h, --help     Show this help.

Environment:
  KEELTRADER_RELEASE_ENV_FILE        Optional env file for release-only secrets/settings. Default: .env.release.local when present.
  KEELTRADER_API_OVERLAY_BASE_IMAGE  Explicit base image for overlay builds. Default: use keeltrader-api:base, fall back to keeltrader-api:latest.
  KEELTRADER_API_SMOKE_ATTEMPTS      Smoke attempts per check. Default: 12
  KEELTRADER_API_SMOKE_DELAY_SECONDS Delay between smoke attempts. Default: 5
  PIP_INDEX_URL                       Python package index for base/test image builds. Default: Aliyun PyPI mirror.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-tests)
      RUN_TESTS=0
      ;;
    --test-only)
      TEST_ONLY=1
      DEPLOY=0
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

if [ "$TEST_ONLY" -eq 1 ] && [ "$RUN_TESTS" -eq 0 ]; then
  die "--test-only cannot be combined with --skip-tests"
fi

if [ "$TEST_ONLY" -eq 1 ] && [ "$SMOKE_ONLY" -eq 1 ]; then
  die "--test-only cannot be combined with --smoke-only"
fi

build_api_base_image() {
  local image="$1"

  docker build --pull=false \
    -f "$API_DIR/Dockerfile" \
    --build-arg PIP_INDEX_URL="$PIP_INDEX_URL" \
    -t "$image" \
    "$ROOT_DIR"
}

build_images() {
  resolve_overlay_base_image "$OVERLAY_BASE_IMAGE" "$DEFAULT_BASE_IMAGE" "$FALLBACK_BASE_IMAGE" build_api_base_image

  log "Building API production overlay image without pulling base images from base: $OVERLAY_BASE_IMAGE"
  log "Build metadata: git_sha=$GIT_SHA build_time=$BUILD_TIME build_type=$BUILD_TYPE"
  docker build --pull=false \
    -f "$API_DIR/Dockerfile.overlay" \
    --build-arg OVERLAY_BASE_IMAGE="$OVERLAY_BASE_IMAGE" \
    --build-arg GIT_SHA="$GIT_SHA" \
    --build-arg BUILD_TIME="$BUILD_TIME" \
    --build-arg BUILD_TYPE="$BUILD_TYPE" \
    -t keeltrader-api:test-overlay \
    "$ROOT_DIR"

  expect_image_revision keeltrader-api:test-overlay "$GIT_SHA"
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
    --build-arg PIP_INDEX_URL="$PIP_INDEX_URL" \
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
  run docker compose up -d api agent-platform-worker opportunity-worker
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
  local key="$1"
  docker compose exec -T api python - "$key" <<'PY'
import asyncio
import os
import sys

import redis.asyncio as redis


async def main() -> int:
    client = redis.from_url(os.environ["REDIS_URL"])
    try:
        raw = await client.get(sys.argv[1])
    finally:
        await client.aclose()

    if not raw:
        return 1
    print(raw.decode() if isinstance(raw, bytes) else raw)
    return 0


raise SystemExit(asyncio.run(main()))
PY
}

expect_agent_platform_heartbeat() {
  local attempt

  for attempt in $(seq 1 "$SMOKE_ATTEMPTS"); do
    if heartbeat_present "keeltrader:agent-platform:heartbeat" >/dev/null 2>&1; then
      log "smoke ok: agent-platform-worker heartbeat"
      return
    fi

    if [ "$attempt" -lt "$SMOKE_ATTEMPTS" ]; then
      log "smoke waiting: agent-platform-worker heartbeat (attempt $attempt/$SMOKE_ATTEMPTS)"
      sleep "$SMOKE_DELAY_SECONDS"
    fi
  done

  die "Smoke failed: agent-platform-worker heartbeat missing"
}

expect_opportunity_heartbeat() {
  local attempt

  for attempt in $(seq 1 "$SMOKE_ATTEMPTS"); do
    if heartbeat_present "keeltrader:opportunity:heartbeat" >/dev/null 2>&1; then
      log "smoke ok: opportunity-worker heartbeat"
      return
    fi
    if [ "$attempt" -lt "$SMOKE_ATTEMPTS" ]; then
      log "smoke waiting: opportunity-worker heartbeat (attempt $attempt/$SMOKE_ATTEMPTS)"
      sleep "$SMOKE_DELAY_SECONDS"
    fi
  done
  die "Smoke failed: opportunity-worker heartbeat missing"
}

smoke() {
  log "Running smoke checks against local Docker Compose stack"

  expect_compose_service_running api
  expect_compose_service_running agent-platform-worker
  expect_compose_service_running opportunity-worker
  expect_container_code "api health" "200" "/api/health"
  expect_container_code "api liveness" "200" "/api/health/live"
  expect_container_code "agent platform health" "200" "/api/v1/agent/health"
  expect_agent_platform_heartbeat
  expect_opportunity_heartbeat
  if [ "$DEPLOY" -eq 1 ] && [ "$SMOKE_ONLY" -eq 0 ]; then
    expect_service_revision api "$GIT_SHA"
    expect_service_revision agent-platform-worker "$GIT_SHA"
    expect_service_revision opportunity-worker "$GIT_SHA"
  fi
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

  check_workspace_writable "$API_DIR/.release-write-check"
  build_images
  run_quality_checks
  if [ "$TEST_ONLY" -eq 1 ]; then
    log "Test-only complete."
    return
  fi

  deploy_api
  if [ "$DEPLOY" -eq 0 ]; then
    log "Validation complete; deployment and runtime smoke skipped."
    return
  fi
  smoke

  log "Release complete."
}

main "$@"
