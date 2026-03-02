"""Proxy helper — inject HTTP proxy into CCXT exchange configs.

Reads HTTPS_PROXY / HTTP_PROXY from environment and applies aiohttp_proxy
to CCXT config dicts. Centralises proxy logic to avoid duplication across
market / execution / portfolio tools.
"""

from __future__ import annotations

import os


def apply_proxy(config: dict) -> dict:
    """Inject aiohttp_proxy into a CCXT config dict if proxy env vars are set.

    Args:
        config: Existing CCXT exchange config dict (mutated in place).

    Returns:
        The same dict with ``aiohttp_proxy`` added when a proxy is available.
    """
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    if proxy:
        config["aiohttp_proxy"] = proxy
    return config
