#!/usr/bin/env bash

init_release_metadata() {
  local root_dir="$1"

  GIT_SHA="${KEELTRADER_GIT_SHA:-$(git -C "$root_dir" rev-parse HEAD 2>/dev/null || echo unknown)}"
  BUILD_TIME="${KEELTRADER_BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  BUILD_TYPE="${KEELTRADER_BUILD_TYPE:-overlay}"
}

load_release_env_file() {
  local root_dir="$1"
  local release_env_file="${KEELTRADER_RELEASE_ENV_FILE:-$root_dir/.env.release.local}"

  if [ -n "${KEELTRADER_RELEASE_ENV_FILE:-}" ] && [ ! -f "$release_env_file" ]; then
    die "Explicit release env file not found: $release_env_file"
  fi

  if [ -f "$release_env_file" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$release_env_file"
    set +a
    log "Loaded release env file: $release_env_file"
  fi
}

log() {
  printf '[%s] %s\n' "${RELEASE_SCOPE:-release}" "$*"
}

die() {
  printf '[%s] ERROR: %s\n' "${RELEASE_SCOPE:-release}" "$*" >&2
  exit 1
}

run() {
  log "$*"
  "$@"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

check_workspace_writable() {
  local probe="$1"

  if ! ( : > "$probe" ) 2>/dev/null; then
    die "Workspace is not writable from this shell. Remount/fix the execution namespace first, then rerun this script."
  fi

  rm -f "$probe"
}

image_revision() {
  local image="$1"

  docker image inspect -f '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$image"
}

image_build_type() {
  local image="$1"

  docker image inspect -f '{{ index .Config.Labels "com.keeltrader.build_type" }}' "$image"
}

resolve_overlay_base_image() {
  local explicit_image="$1"
  local default_image="$2"
  local fallback_image="$3"
  local build_base_image_func="$4"
  local fallback_build_type

  if [ -n "$explicit_image" ]; then
    if ! docker image inspect "$explicit_image" >/dev/null 2>&1; then
      die "Explicit overlay base image not found: $explicit_image"
    fi
    OVERLAY_BASE_IMAGE="$explicit_image"
    log "Using explicit overlay base image: $OVERLAY_BASE_IMAGE"
    return
  fi

  if [ "${FULL_BUILD:-0}" -eq 1 ]; then
    OVERLAY_BASE_IMAGE="$default_image"
    log "Rebuilding overlay base image by request: $OVERLAY_BASE_IMAGE"
    "$build_base_image_func" "$OVERLAY_BASE_IMAGE"
    return
  fi

  if docker image inspect "$default_image" >/dev/null 2>&1; then
    OVERLAY_BASE_IMAGE="$default_image"
    log "Using overlay base image: $OVERLAY_BASE_IMAGE"
    return
  fi

  if [ -n "$fallback_image" ] && docker image inspect "$fallback_image" >/dev/null 2>&1; then
    fallback_build_type="$(image_build_type "$fallback_image" 2>/dev/null || true)"
    if [ "$fallback_build_type" = "overlay" ]; then
      OVERLAY_BASE_IMAGE="$default_image"
      log "Fallback image $fallback_image is also an overlay; rebuilding $OVERLAY_BASE_IMAGE to avoid stacked overlay layers."
      "$build_base_image_func" "$OVERLAY_BASE_IMAGE"
      return
    fi

    OVERLAY_BASE_IMAGE="$fallback_image"
    log "Overlay base $default_image not found; using $OVERLAY_BASE_IMAGE to avoid dependency-layer rebuild."
    return
  fi

  OVERLAY_BASE_IMAGE="$default_image"
  log "No reusable overlay base image found; bootstrapping $OVERLAY_BASE_IMAGE without pulling base images."
  "$build_base_image_func" "$OVERLAY_BASE_IMAGE"
}

service_image_id() {
  local service="$1"
  local cid

  cid="$(docker compose ps -q "$service")"
  [ -n "$cid" ] || return 1
  docker inspect -f '{{.Image}}' "$cid"
}

expect_services_same_image() {
  local expected_id=""
  local service
  local actual_id

  for service in "$@"; do
    actual_id="$(service_image_id "$service" 2>/dev/null || true)"
    [ -n "$actual_id" ] || die "Running service has no image ID: $service"
    if [ -z "$expected_id" ]; then
      expected_id="$actual_id"
    elif [ "$actual_id" != "$expected_id" ]; then
      die "Running service image mismatch: $service uses $actual_id, expected $expected_id"
    fi
  done

  log "smoke ok: services share immutable image $expected_id ($*)"
}

ensure_compose_api_image_env() {
  if [ -z "${KEELTRADER_API_IMAGE:-}" ]; then
    KEELTRADER_API_IMAGE="$(docker inspect -f '{{.Config.Image}}' keeltrader-api 2>/dev/null || true)"
  fi
  [ -n "${KEELTRADER_API_IMAGE:-}" ] || die "KEELTRADER_API_IMAGE is required and no running API image could be resolved"
  export KEELTRADER_API_IMAGE
}

expect_image_revision() {
  local image="$1"
  local expected="$2"
  local actual

  actual="$(image_revision "$image" 2>/dev/null || true)"
  if [ "$actual" != "$expected" ]; then
    die "Image revision mismatch for $image: expected $expected, got ${actual:-missing}"
  fi

  log "smoke ok: $image revision $actual"
}

service_image_revision() {
  local service="$1"
  local cid
  local image_id

  cid="$(docker compose ps -q "$service")"
  [ -n "$cid" ] || return 1
  image_id="$(docker inspect -f '{{.Image}}' "$cid")"
  docker image inspect -f '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$image_id"
}

expect_service_revision() {
  local service="$1"
  local expected="$2"
  local actual

  actual="$(service_image_revision "$service" 2>/dev/null || true)"
  if [ "$actual" != "$expected" ]; then
    die "Running service revision mismatch for $service: expected $expected, got ${actual:-missing}"
  fi

  log "smoke ok: $service image revision $actual"
}
