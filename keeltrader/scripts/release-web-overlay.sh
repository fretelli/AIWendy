#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_SCOPE="release-web"
source "$ROOT_DIR/scripts/lib/release-common.sh"
init_release_metadata "$ROOT_DIR"
WEB_DIR="$ROOT_DIR/apps/web"
BASE_URL="${KEELTRADER_SMOKE_BASE_URL:-https://keeltrader.joyeeassets.com}"
OVERLAY_BASE_IMAGE="${KEELTRADER_WEB_OVERLAY_BASE_IMAGE:-}"
DEFAULT_BASE_IMAGE="keeltrader-web:base"
FALLBACK_BASE_IMAGE="keeltrader-web:latest"
RUN_TESTS=1
DEPLOY=1
FULL_BUILD=0
SMOKE_ONLY=0
SMOKE_ATTEMPTS="${KEELTRADER_SMOKE_ATTEMPTS:-12}"
SMOKE_DELAY_SECONDS="${KEELTRADER_SMOKE_DELAY_SECONDS:-2}"

usage() {
  cat <<'USAGE'
Usage: scripts/release-web-overlay.sh [options]

Build and release the KeelTrader web service using the local overlay image path.

Options:
  --skip-tests   Skip lint/type-check/jest, but still run Next build and smoke checks.
  --no-deploy    Build and validate the image without tagging latest or restarting web.
  --full-build   Rebuild keeltrader-web:base from apps/web/Dockerfile before overlay.
  --smoke-only   Run smoke checks only.
  -h, --help     Show this help.

Environment:
  KEELTRADER_SMOKE_BASE_URL       Base URL for smoke checks. Default: https://keeltrader.joyeeassets.com
  KEELTRADER_SMOKE_EMAIL          Optional login smoke email.
  KEELTRADER_SMOKE_PASSWORD       Optional login smoke password.
  KEELTRADER_SMOKE_ATTEMPTS       Smoke attempts per check. Default: 12
  KEELTRADER_SMOKE_DELAY_SECONDS  Delay between smoke attempts. Default: 2
  KEELTRADER_WEB_OVERLAY_BASE_IMAGE  Explicit base image for overlay builds. Default: use keeltrader-web:base, fall back to keeltrader-web:latest.
USAGE
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

http_code() {
  local method="$1"
  local url="$2"
  local output="$3"
  shift 3

  curl -ksS -X "$method" -o "$output" -w '%{http_code}' "$@" "$url"
}

expect_code() {
  local label="$1"
  local expected="$2"
  local method="$3"
  local path="$4"
  local output
  local code
  local attempt

  for attempt in $(seq 1 "$SMOKE_ATTEMPTS"); do
    output="$(mktemp)"
    code="$(http_code "$method" "$BASE_URL$path" "$output" 2>/dev/null || true)"
    rm -f "$output"

    case ",$expected," in
      *",$code,"*)
        log "smoke ok: $label -> $code"
        return
        ;;
    esac

    if [ "$attempt" -lt "$SMOKE_ATTEMPTS" ]; then
      log "smoke waiting: $label expected [$expected], got ${code:-curl-error} (attempt $attempt/$SMOKE_ATTEMPTS)"
      sleep "$SMOKE_DELAY_SECONDS"
    fi
  done

  die "Smoke failed: $label expected [$expected], got ${code:-curl-error}"
}

run_quality_checks() {
  if [ "$RUN_TESTS" -eq 0 ]; then
    log "Skipping lint/type-check/jest by request."
    return
  fi

  run npm run lint
  run npm run type-check
  run npm test -- --runInBand
}

run_next_build() {
  log "Building Next.js production output"
  NEXT_PUBLIC_API_URL=http://api:8000 \
    NEXT_PUBLIC_AUTH_REQUIRED=1 \
    npm run build
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
      --build-arg NEXT_PUBLIC_API_URL=http://api:8000 \
      --build-arg NEXT_PUBLIC_AUTH_REQUIRED=1 \
      --build-arg NEXT_PUBLIC_SITE_URL=https://keeltrader.joyeeassets.com \
      -t "$OVERLAY_BASE_IMAGE" \
      "$WEB_DIR"
    return
  fi

  if docker image inspect "$DEFAULT_BASE_IMAGE" >/dev/null 2>&1; then
    OVERLAY_BASE_IMAGE="$DEFAULT_BASE_IMAGE"
    log "Using overlay base image: $OVERLAY_BASE_IMAGE"
    return
  fi

  if docker image inspect "$FALLBACK_BASE_IMAGE" >/dev/null 2>&1; then
    local fallback_build_type
    fallback_build_type="$(image_build_type "$FALLBACK_BASE_IMAGE" 2>/dev/null || true)"
    if [ "$fallback_build_type" = "overlay" ]; then
      OVERLAY_BASE_IMAGE="$DEFAULT_BASE_IMAGE"
      log "Fallback image $FALLBACK_BASE_IMAGE is also an overlay; rebuilding $OVERLAY_BASE_IMAGE to avoid stacked overlay layers."
      docker build --pull=false \
        --build-arg NEXT_PUBLIC_API_URL=http://api:8000 \
        --build-arg NEXT_PUBLIC_AUTH_REQUIRED=1 \
        --build-arg NEXT_PUBLIC_SITE_URL=https://keeltrader.joyeeassets.com \
        -t "$OVERLAY_BASE_IMAGE" \
        "$WEB_DIR"
      return
    fi

    OVERLAY_BASE_IMAGE="$FALLBACK_BASE_IMAGE"
    log "Overlay base $DEFAULT_BASE_IMAGE not found; using $OVERLAY_BASE_IMAGE to avoid dependency-layer rebuild."
    return
  fi

  OVERLAY_BASE_IMAGE="$DEFAULT_BASE_IMAGE"
  log "No reusable overlay base image found; bootstrapping $OVERLAY_BASE_IMAGE without pulling base images."
  docker build --pull=false \
    --build-arg NEXT_PUBLIC_API_URL=http://api:8000 \
    --build-arg NEXT_PUBLIC_AUTH_REQUIRED=1 \
    --build-arg NEXT_PUBLIC_SITE_URL=https://keeltrader.joyeeassets.com \
    -t "$OVERLAY_BASE_IMAGE" \
    "$WEB_DIR"
}

build_images() {
  resolve_overlay_base_image

  log "Building overlay image without pulling base images from base: $OVERLAY_BASE_IMAGE"
  log "Build metadata: git_sha=$GIT_SHA build_time=$BUILD_TIME build_type=$BUILD_TYPE"
  docker build --pull=false \
    -f "$WEB_DIR/Dockerfile.overlay" \
    --build-arg OVERLAY_BASE_IMAGE="$OVERLAY_BASE_IMAGE" \
    --build-arg GIT_SHA="$GIT_SHA" \
    --build-arg BUILD_TIME="$BUILD_TIME" \
    --build-arg BUILD_TYPE="$BUILD_TYPE" \
    -t keeltrader-web:test-overlay \
    "$WEB_DIR"

  expect_image_revision keeltrader-web:test-overlay "$GIT_SHA"
}

deploy_web() {
  if [ "$DEPLOY" -eq 0 ]; then
    log "Skipping deploy by request."
    return
  fi

  run docker tag keeltrader-web:test-overlay keeltrader-web:latest
  run docker compose up -d web
}

smoke() {
  log "Running smoke checks against $BASE_URL"

  expect_code "login page" "200" "GET" "/auth/login"
  expect_code "agentos requires login" "302,303,307,308" "GET" "/agentos"
  expect_code "agentos API requires login" "401" "GET" "/api/proxy/v1/agentos/health"
  expect_code "research API requires login" "401" "GET" "/api/research/health"
  if [ "$DEPLOY" -eq 1 ] && [ "$SMOKE_ONLY" -eq 0 ]; then
    expect_code "web health" "200" "GET" "/api/health"
    expect_service_revision web "$GIT_SHA"
  fi

  if [ -z "${KEELTRADER_SMOKE_EMAIL:-}" ] || [ -z "${KEELTRADER_SMOKE_PASSWORD:-}" ]; then
    log "Skipping logged-in smoke checks; KEELTRADER_SMOKE_EMAIL/PASSWORD not set."
    return
  fi

  local cookies
  local body
  local code
  cookies="$(mktemp)"
  body="$(mktemp)"

  local payload
  payload="$(node -e 'process.stdout.write(JSON.stringify({email: process.env.KEELTRADER_SMOKE_EMAIL, password: process.env.KEELTRADER_SMOKE_PASSWORD}))')"

  code="$(curl -ksS \
    -X POST \
    -c "$cookies" \
    -H 'content-type: application/json' \
    -o "$body" \
    -w '%{http_code}' \
    --data "$payload" \
    "$BASE_URL/api/proxy/v1/auth/login")"

  if [ "$code" != "200" ]; then
    rm -f "$cookies" "$body"
    die "Smoke failed: login API expected 200, got $code"
  fi

  code="$(curl -ksS -b "$cookies" -o "$body" -w '%{http_code}' "$BASE_URL/agentos")"
  if [ "$code" != "200" ]; then
    rm -f "$cookies" "$body"
    die "Smoke failed: logged-in /agentos expected 200, got $code"
  fi

  code="$(curl -ksS -b "$cookies" -o "$body" -w '%{http_code}' "$BASE_URL/api/proxy/v1/agentos/health")"
  if [ "$code" != "200" ]; then
    rm -f "$cookies" "$body"
    die "Smoke failed: logged-in AgentOS health expected 200, got $code"
  fi

  rm -f "$cookies" "$body"
  log "smoke ok: logged-in AgentOS"
}

main() {
  require_command npm
  require_command node
  require_command docker
  require_command curl
  require_command mktemp

  cd "$ROOT_DIR"
  if [ "$SMOKE_ONLY" -eq 1 ]; then
    smoke
    log "Smoke complete."
    return
  fi

  check_workspace_writable "$WEB_DIR/.release-write-check"

  cd "$WEB_DIR"
  run_quality_checks
  run_next_build

  cd "$ROOT_DIR"
  build_images
  deploy_web
  smoke

  log "Release complete."
}

main "$@"
