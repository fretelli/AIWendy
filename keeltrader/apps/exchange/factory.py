"""Exchange adapter factory — create_adapter() with instance caching.

Centralises adapter creation so callers never need to know which concrete
adapter class to use.  Caching avoids repeated TCP handshakes for the same
exchange + credentials combination.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import ExchangeAdapter
from .ccxt_adapter import CcxtAdapter

logger = logging.getLogger(__name__)

# Adapter cache: cache_key → adapter instance
_adapter_cache: dict[str, ExchangeAdapter] = {}

# Known CCXT exchanges
_CCXT_EXCHANGES = {"binance", "okx", "bybit", "coinbase", "kraken"}


def create_adapter(
    exchange_name: str,
    api_key: str | None = None,
    api_secret: str | None = None,
    passphrase: str | None = None,
    trading_mode: str = "swap",
    is_testnet: bool = False,
    *,
    use_cache: bool = True,
    credentials_extra: dict[str, Any] | None = None,
) -> ExchangeAdapter:
    """Create or retrieve a cached ExchangeAdapter.

    Args:
        exchange_name: Exchange identifier ('binance', 'okx', 'ibkr', etc.)
        api_key: API key / username (None for public-data-only adapters)
        api_secret: API secret / password
        passphrase: Extra passphrase (OKX, etc.)
        trading_mode: 'spot', 'swap', 'stock', 'option', 'future'
        is_testnet: Whether to use testnet/sandbox
        use_cache: If True, reuse existing adapter for same credentials
        credentials_extra: IBKR-specific settings (gateway_host, port, client_id, etc.)

    Returns:
        An ExchangeAdapter instance ready for use.

    Raises:
        ValueError: If the exchange is not supported.
    """
    name = exchange_name.lower()

    if use_cache:
        cache_key = _build_cache_key(name, api_key, trading_mode, is_testnet)
        if cache_key in _adapter_cache:
            return _adapter_cache[cache_key]

    adapter: ExchangeAdapter

    if name in _CCXT_EXCHANGES:
        adapter = CcxtAdapter(
            exchange_name=name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            trading_mode=trading_mode,
            is_testnet=is_testnet,
        )
    elif name == "ibkr":
        from .ibkr_adapter import IbkrAdapter

        extra = credentials_extra or {}
        adapter = IbkrAdapter(
            gateway_host=extra.get("gateway_host", "127.0.0.1"),
            gateway_port=int(extra.get("gateway_port", 4001)),
            client_id=int(extra.get("client_id", 1)),
            trading_mode=trading_mode,
            username=api_key,  # IBKR: api_key stores username
            readonly=extra.get("readonly", True),
        )
    else:
        raise ValueError(f"Unsupported exchange: {exchange_name}")

    if use_cache:
        cache_key = _build_cache_key(name, api_key, trading_mode, is_testnet)
        _adapter_cache[cache_key] = adapter
        logger.debug("Cached adapter for %s", cache_key)

    return adapter


def clear_cache() -> None:
    """Clear the adapter cache (for testing or shutdown)."""
    _adapter_cache.clear()


def _build_cache_key(
    name: str,
    api_key: str | None,
    trading_mode: str,
    is_testnet: bool,
) -> str:
    key_prefix = api_key[:8] if api_key else "public"
    return f"{name}:{key_prefix}:{trading_mode}:{'test' if is_testnet else 'live'}"
