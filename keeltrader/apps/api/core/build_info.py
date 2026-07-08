"""Build metadata exposed by release images."""

from __future__ import annotations

import os

from config import get_settings


def get_build_info() -> dict[str, str]:
    """Return deploy traceability metadata from image environment variables."""
    settings = get_settings()
    return {
        "version": settings.app_version,
        "git_sha": os.getenv("KEELTRADER_GIT_SHA", "unknown"),
        "build_time": os.getenv("KEELTRADER_BUILD_TIME", "unknown"),
        "build_type": os.getenv("KEELTRADER_BUILD_TYPE", "unknown"),
    }
