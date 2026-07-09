"""Shared import path setup for legacy direct-run scripts."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_api_import_path() -> None:
    """Allow scripts to import API modules from source and overlay images."""
    api_root = Path(__file__).resolve().parent.parent
    api_root_value = str(api_root)
    if api_root_value not in sys.path:
        sys.path.insert(0, api_root_value)
