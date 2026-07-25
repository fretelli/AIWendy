#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
app_root="$(CDPATH= cd -- "${script_dir}/.." && pwd)"
api_root="${app_root}/apps/api"

echo "[api-static] parsing Python sources"
python3 - "$api_root" <<'PY'
from __future__ import annotations

import pathlib
import sys

root = pathlib.Path(sys.argv[1])
errors: list[str] = []

for path in sorted(root.rglob("*.py")):
    if any(part in {".mypy_cache", ".pytest_cache", "__pycache__"} for part in path.parts):
        continue
    try:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec", dont_inherit=True)
    except Exception as exc:  # noqa: BLE001 - static gate should report all parse failures.
        errors.append(f"{path.relative_to(root)}: {exc}")

if errors:
    print("Python source parse failures:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    raise SystemExit(1)
PY

echo "[api-static] checking route contracts"
if grep -R --line-number -E 'user_id:[[:space:]]*str[[:space:]]*=[[:space:]]*"default"' "${api_root}/routers"; then
  echo "Legacy default user_id found in API routers. Require explicit authenticated/query user ids." >&2
  exit 1
fi

legacy_router_pattern='(agents|analysis|dashboard|exchanges|journals|projects|tasks)'
if grep --line-number -E "from routers(\.${legacy_router_pattern}| import .*\b${legacy_router_pattern}\b)" "${api_root}/main.py"; then
  echo "Legacy router import found in main.py. Keep legacy routers unmounted unless route contracts are intentionally updated." >&2
  exit 1
fi

if grep --line-number -E "include_router\((agents|analysis|dashboard|exchanges|journals|projects|tasks)(_router|\.router)" "${api_root}/main.py"; then
  echo "Legacy router mount found in main.py. Keep legacy routers unmounted unless route contracts are intentionally updated." >&2
  exit 1
fi

echo "[api-static] checking script import path boundaries"
if grep -R --line-number "sys\.path" "${api_root}/scripts" --include '*.py' | grep -v '/_path_setup.py:'; then
  echo "Direct sys.path mutation found in scripts. Use scripts/_path_setup.py instead." >&2
  exit 1
fi

echo "[api-static] checking Alembic-only schema management"
if grep -R --line-number -E 'create_all|core\.bootstrap|core\.db_bootstrap' "${api_root}" --include '*.py' | grep -v '/tests/'; then
  echo "Runtime schema bootstrap found. Database schema changes must use Alembic." >&2
  exit 1
fi

echo "[api-static] ok"
