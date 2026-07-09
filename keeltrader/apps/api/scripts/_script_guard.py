"""Runtime guardrails for legacy one-off maintenance scripts."""

from __future__ import annotations

import os
import sys

ALLOW_LEGACY_SCRIPT_ENV = "KEELTRADER_ALLOW_LEGACY_SCRIPT"
PRODUCTION_ENVIRONMENTS = {"prod", "production"}


def require_non_production_script(script_name: str) -> None:
    """Block legacy schema/data scripts in production unless explicitly allowed."""
    environment = (
        os.environ.get("ENVIRONMENT")
        or os.environ.get("KEELTRADER_ENV")
        or os.environ.get("APP_ENV")
        or ""
    ).strip().lower()

    if environment not in PRODUCTION_ENVIRONMENTS:
        return

    if os.environ.get(ALLOW_LEGACY_SCRIPT_ENV) == "1":
        return

    print(
        f"Refusing to run legacy script {script_name!r} while ENVIRONMENT={environment!r}.",
        file=sys.stderr,
    )
    print(
        f"Set {ALLOW_LEGACY_SCRIPT_ENV}=1 only after taking a database backup "
        "and confirming the script is intended for this production environment.",
        file=sys.stderr,
    )
    raise SystemExit(2)
