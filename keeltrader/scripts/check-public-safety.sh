#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

failures=0

check_pattern() {
  local label="$1"
  local pattern="$2"
  local matches
  matches="$(git grep -nIE "$pattern" -- . ':!docs/DEPLOYMENT_MODES.md' || true)"
  if [ -n "$matches" ]; then
    echo "[public-safety] ${label} found:" >&2
    printf '%s\n' "$matches" | awk -F: '{print "  - " $1 ":" $2}' >&2
    failures=1
  fi
}

check_pattern "private key material" 'BEGIN (RSA |OPENSSH |EC |DSA |)PRIVATE KEY|-----BEGIN'
check_pattern "AWS access key" '\b(AKIA|ASIA)[0-9A-Z]{16}\b'
check_pattern "GitHub token" '\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b|github_pat_[A-Za-z0-9_]{40,}\b'
check_pattern "OpenAI/LiteLLM-style secret key" '\bsk-[A-Za-z0-9_-]{12,}\b'
check_pattern "Google API key" '\bAIza[0-9A-Za-z_-]{20,}\b'
check_pattern "Slack token" '\bxox[baprs]-[A-Za-z0-9-]{20,}\b'
check_pattern "known development password" 'Admin[@]123|Test[@]1234|Cjd1989318'

python3 - <<'PY'
from __future__ import annotations

import ipaddress
import pathlib
import re
import subprocess
import sys

files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
matches: list[str] = []
for name in files:
    if name == "docs/DEPLOYMENT_MODES.md":
        continue
    path = pathlib.Path(name)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for lineno, line in enumerate(text.splitlines(), start=1):
        for raw in pattern.findall(line):
            try:
                ip = ipaddress.ip_address(raw)
            except ValueError:
                continue
            if ip.version == 4 and ip.is_global:
                matches.append(f"  - {name}:{lineno}")

if matches:
    print("[public-safety] public IPv4 address found:", file=sys.stderr)
    print("\n".join(matches), file=sys.stderr)
    raise SystemExit(1)
PY

if [ "$failures" -ne 0 ]; then
  echo "[public-safety] failed" >&2
  exit 1
fi

echo "[public-safety] ok"
