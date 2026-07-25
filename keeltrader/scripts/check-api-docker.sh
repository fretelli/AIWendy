#!/usr/bin/env bash
set -Eeuo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
base_image="${KEELTRADER_API_TEST_BASE_IMAGE:-keeltrader-api:test-base}"
runner_image="${KEELTRADER_API_TEST_RUNNER_IMAGE:-keeltrader-api:test-runner}"
pip_index="${PIP_INDEX_URL:-https://pypi.org/simple/}"

docker build \
  -f "$root_dir/apps/api/Dockerfile" \
  --build-arg PIP_INDEX_URL="$pip_index" \
  -t "$base_image" \
  "$root_dir"

docker build \
  -f "$root_dir/apps/api/Dockerfile.test" \
  --build-arg API_UNDER_TEST_IMAGE="$base_image" \
  --build-arg PIP_INDEX_URL="$pip_index" \
  -t "$runner_image" \
  "$root_dir"

docker run --rm "$runner_image" pytest
