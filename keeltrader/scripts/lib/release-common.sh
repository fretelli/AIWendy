#!/usr/bin/env bash

init_release_metadata() {
  local root_dir="$1"

  GIT_SHA="${KEELTRADER_GIT_SHA:-$(git -C "$root_dir" rev-parse HEAD 2>/dev/null || echo unknown)}"
  BUILD_TIME="${KEELTRADER_BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  BUILD_TYPE="${KEELTRADER_BUILD_TYPE:-overlay}"
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
