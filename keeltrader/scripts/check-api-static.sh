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

echo "[api-static] checking legacy script production guards"
guarded_scripts=(
  "bootstrap_projects.py"
  "init_database.py"
  "init_db_simple.py"
  "migrate_to_multi_tenant.py"
  "create_user_sessions_table.py"
  "add_api_keys_columns.py"
  "add_journal_tables.py"
)

for script in "${guarded_scripts[@]}"; do
  path="${api_root}/scripts/${script}"
  if ! grep -q "require_non_production_script" "$path"; then
    echo "Missing production guard in ${path}" >&2
    exit 1
  fi
done

echo "[api-static] ok"
