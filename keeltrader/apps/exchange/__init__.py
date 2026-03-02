"""Exchange adapter abstraction layer.

Provides a unified interface for interacting with different exchanges
(CCXT-based crypto exchanges, IBKR, etc.) through the Adapter pattern.
"""

from .base import ExchangeAdapter, UnifiedBalance, UnifiedOrder, UnifiedPosition
from .factory import create_adapter

__all__ = [
    "ExchangeAdapter",
    "UnifiedBalance",
    "UnifiedOrder",
    "UnifiedPosition",
    "create_adapter",
]
