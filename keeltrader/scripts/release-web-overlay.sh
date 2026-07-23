#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_SCOPE="release-web"
source "$ROOT_DIR/scripts/lib/release-common.sh"
load_release_env_file "$ROOT_DIR"
init_release_metadata "$ROOT_DIR"
WEB_DIR="$ROOT_DIR/apps/web"
BASE_URL="${KEELTRADER_SMOKE_BASE_URL:-https://keeltrader.joyeeassets.com}"
OVERLAY_BASE_IMAGE="${KEELTRADER_WEB_OVERLAY_BASE_IMAGE:-}"
NPM_REGISTRY="${KEELTRADER_NPM_REGISTRY:-https://registry.npmmirror.com/}"
REQUIRE_AUTH_SMOKE="${KEELTRADER_REQUIRE_AUTH_SMOKE:-0}"
DEFAULT_BASE_IMAGE="keeltrader-web:base"
FALLBACK_BASE_IMAGE="keeltrader-web:latest"
RUN_TESTS=1
DEPLOY=1
FULL_BUILD=0
SMOKE_ONLY=0
TEST_ONLY=0
SMOKE_ATTEMPTS="${KEELTRADER_SMOKE_ATTEMPTS:-12}"
SMOKE_DELAY_SECONDS="${KEELTRADER_SMOKE_DELAY_SECONDS:-2}"

usage() {
  cat <<'USAGE'
Usage: scripts/release-web-overlay.sh [options]

Build and release the KeelTrader web service using the local overlay image path.

Options:
  --skip-tests   Skip lint/type-check/jest, but still run Next build and smoke checks.
  --test-only    Run checks, Next build, and overlay image build without deploy or smoke.
  --no-deploy    Build and validate the image without tagging latest or restarting web.
  --full-build   Rebuild keeltrader-web:base from apps/web/Dockerfile before overlay.
  --smoke-only   Run smoke checks only.
  -h, --help     Show this help.

Environment:
  KEELTRADER_SMOKE_BASE_URL       Base URL for smoke checks. Default: https://keeltrader.joyeeassets.com
  KEELTRADER_SMOKE_EMAIL          Optional login smoke email.
  KEELTRADER_SMOKE_PASSWORD       Optional login smoke password.
  KEELTRADER_REQUIRE_AUTH_SMOKE   Set to 1 to fail release when login smoke credentials are missing.
  KEELTRADER_RELEASE_ENV_FILE     Optional env file for release-only secrets. Default: .env.release.local when present.
  KEELTRADER_SMOKE_ATTEMPTS       Smoke attempts per check. Default: 12
  KEELTRADER_SMOKE_DELAY_SECONDS  Delay between smoke attempts. Default: 2
  KEELTRADER_NPM_REGISTRY         npm registry used for full/base Docker builds. Default: https://registry.npmmirror.com/
  KEELTRADER_WEB_OVERLAY_BASE_IMAGE  Explicit base image for overlay builds. Default: use keeltrader-web:base, fall back to keeltrader-web:latest.
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

http_code() {
  local method="$1"
  local url="$2"
  local output="$3"
  shift 3

  curl -ksS -X "$method" -o "$output" -w '%{http_code}' "$@" "$url"
}

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|y|Y|on|ON) return 0 ;;
    *) return 1 ;;
  esac
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

build_web_base_image() {
  local image="$1"

  docker build --pull=false \
    --build-arg NPM_CONFIG_REGISTRY="$NPM_REGISTRY" \
    --build-arg NEXT_PUBLIC_API_URL=http://api:8000 \
    --build-arg NEXT_PUBLIC_AUTH_REQUIRED=1 \
    --build-arg NEXT_PUBLIC_SITE_URL=https://keeltrader.joyeeassets.com \
    -t "$image" \
    "$WEB_DIR"
}

build_images() {
  resolve_overlay_base_image "$OVERLAY_BASE_IMAGE" "$DEFAULT_BASE_IMAGE" "$FALLBACK_BASE_IMAGE" build_web_base_image

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
  # Web releases must not pull, build, recreate, or retag API dependencies.
  run docker compose up -d --no-deps web
}

smoke() {
  log "Running smoke checks against $BASE_URL"

  expect_code "login page" "200" "GET" "/auth/login"
  expect_code "agent requires login" "302,303,307,308" "GET" "/agent"
  expect_code "agent API requires login" "401" "GET" "/api/proxy/v1/agent/health"
  expect_code "research hub removed" "404" "GET" "/research"
  if [ "$DEPLOY" -eq 1 ] && [ "$SMOKE_ONLY" -eq 0 ]; then
    expect_code "web health" "200" "GET" "/api/health"
    expect_service_revision web "$GIT_SHA"
  fi

  if [ -z "${KEELTRADER_SMOKE_EMAIL:-}" ] || [ -z "${KEELTRADER_SMOKE_PASSWORD:-}" ]; then
    if is_truthy "$REQUIRE_AUTH_SMOKE"; then
      die "Logged-in smoke required but KEELTRADER_SMOKE_EMAIL/PASSWORD are not set."
    fi
    log "Logged-in smoke incomplete: KEELTRADER_SMOKE_EMAIL/PASSWORD not set; release was not validated with an authenticated session."
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

  code="$(curl -ksS -b "$cookies" -o "$body" -w '%{http_code}' "$BASE_URL/agent")"
  if [ "$code" != "200" ]; then
    rm -f "$cookies" "$body"
    die "Smoke failed: logged-in /agent expected 200, got $code"
  fi

  code="$(curl -ksS -b "$cookies" -o "$body" -w '%{http_code}' "$BASE_URL/api/proxy/v1/agent/health")"
  if [ "$code" != "200" ]; then
    rm -f "$cookies" "$body"
    die "Smoke failed: logged-in Agent Platform health expected 200, got $code"
  fi

  code="$(curl -ksS -b "$cookies" -o "$body" -w '%{http_code}' "$BASE_URL/settings")"
  if [ "$code" != "404" ]; then
    rm -f "$cookies" "$body"
    die "Smoke failed: removed /settings expected 404, got $code"
  fi

  code="$(curl -ksS -b "$cookies" -o "$body" -w '%{http_code}' "$BASE_URL/api/proxy/v1/settings/risk")"
  if [ "$code" != "404" ]; then
    rm -f "$cookies" "$body"
    die "Smoke failed: removed settings API expected 404, got $code"
  fi

  local retired_path
  for retired_path in \
    /agent/today \
    /agent/theses \
    /api/proxy/v1/agent/theses \
    /api/proxy/v1/agent/events \
    /api/proxy/v1/agent/calendar; do
    code="$(curl -ksS -b "$cookies" -o "$body" -w '%{http_code}' "$BASE_URL$retired_path")"
    if [ "$code" != "404" ]; then
      rm -f "$cookies" "$body"
      die "Smoke failed: retired $retired_path expected 404, got $code"
    fi
  done

  rm -f "$cookies" "$body"
  log "smoke ok: logged-in Agent Platform; removed trading settings, Today, and Thesis surfaces"
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
  if [ "$TEST_ONLY" -eq 1 ]; then
    log "Test-only complete."
    return
  fi

  deploy_web
  smoke

  log "Release complete."
}

main "$@"
