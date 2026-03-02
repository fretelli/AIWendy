"""IBKR contract parsing — bidirectional conversion between unified symbols and IB Contracts.

Unified symbol formats:
  - Stock:  "AAPL"                    -> Stock("AAPL", "SMART", "USD")
  - Option: "AAPL 250321C200"         -> Option("AAPL", "20250321", 200, "C", "SMART")
  - Future: "ES 202506"              -> Future("ES", "202506", "CME")
  - Crypto: "BTC/USDT"               -> NOT handled here (use CcxtAdapter)

This module depends on ib_async which is only installed when IBKR profile is active.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Lazy import — ib_async may not be installed
_ib_async = None


def _get_ib_async():
    global _ib_async
    if _ib_async is None:
        try:
            import ib_async
            _ib_async = ib_async
        except ImportError:
            raise ImportError(
                "ib_async is required for IBKR support. "
                "Install with: pip install ib_async>=1.0.0"
            )
    return _ib_async


# Common futures exchange mappings
FUTURES_EXCHANGE_MAP = {
    "ES": "CME",
    "NQ": "CME",
    "YM": "CBOT",
    "RTY": "CME",
    "CL": "NYMEX",
    "GC": "COMEX",
    "SI": "COMEX",
    "ZB": "CBOT",
    "ZN": "CBOT",
    "ZF": "CBOT",
    "ZT": "CBOT",
    "6E": "CME",
    "6J": "CME",
    "6B": "CME",
    "VX": "CFE",
}

# Option symbol regex: "AAPL 250321C200" or "AAPL 250321P150.5"
_OPTION_RE = re.compile(
    r"^([A-Z]+)\s+(\d{6})([CP])([\d.]+)$"
)

# Future symbol regex: "ES 202506"
_FUTURE_RE = re.compile(
    r"^([A-Z0-9]+)\s+(\d{6})$"
)


@dataclass
class ParsedContract:
    """Intermediate representation before conversion to IB Contract."""

    asset_class: str  # "stock", "option", "future"
    symbol: str
    exchange: str = "SMART"
    currency: str = "USD"
    # Option fields
    expiry: str | None = None  # YYYYMMDD
    strike: float | None = None
    right: str | None = None  # "C" or "P"
    # Future fields
    last_trade_date: str | None = None  # YYYYMM


def parse_symbol(symbol: str, default_asset_class: str = "stock") -> ParsedContract:
    """Parse a unified symbol string into a ParsedContract.

    Args:
        symbol: Unified symbol string (e.g., "AAPL", "AAPL 250321C200", "ES 202506")
        default_asset_class: Assumed asset class if format is ambiguous

    Returns:
        ParsedContract with parsed fields
    """
    symbol = symbol.strip()

    # Try option format: "AAPL 250321C200"
    m = _OPTION_RE.match(symbol)
    if m:
        underlying, date_str, right, strike_str = m.groups()
        # Convert YYMMDD -> YYYYMMDD
        expiry = f"20{date_str}"
        return ParsedContract(
            asset_class="option",
            symbol=underlying,
            expiry=expiry,
            strike=float(strike_str),
            right=right,
        )

    # Try future format: "ES 202506"
    m = _FUTURE_RE.match(symbol)
    if m:
        underlying, last_trade = m.groups()
        exchange = FUTURES_EXCHANGE_MAP.get(underlying, "CME")
        return ParsedContract(
            asset_class="future",
            symbol=underlying,
            exchange=exchange,
            last_trade_date=last_trade,
        )

    # Default: stock
    return ParsedContract(
        asset_class=default_asset_class,
        symbol=symbol.upper(),
    )


def to_ib_contract(parsed: ParsedContract) -> Any:
    """Convert a ParsedContract to an ib_async Contract object.

    Returns:
        ib_async.Stock, ib_async.Option, or ib_async.Future
    """
    ib = _get_ib_async()

    if parsed.asset_class == "stock":
        return ib.Stock(parsed.symbol, parsed.exchange, parsed.currency)

    if parsed.asset_class == "option":
        return ib.Option(
            parsed.symbol,
            parsed.expiry,
            parsed.strike,
            parsed.right,
            parsed.exchange,
            currency=parsed.currency,
        )

    if parsed.asset_class == "future":
        return ib.Future(
            parsed.symbol,
            parsed.last_trade_date,
            parsed.exchange,
            currency=parsed.currency,
        )

    raise ValueError(f"Unknown asset class: {parsed.asset_class}")


def symbol_to_contract(symbol: str, asset_class: str = "stock") -> Any:
    """Convenience: parse symbol string directly to IB Contract."""
    parsed = parse_symbol(symbol, default_asset_class=asset_class)
    return to_ib_contract(parsed)


def contract_to_symbol(contract: Any) -> str:
    """Convert an IB Contract back to unified symbol string."""
    ib = _get_ib_async()

    if isinstance(contract, ib.Stock):
        return contract.symbol

    if isinstance(contract, ib.Option):
        # YYYYMMDD -> YYMMDD
        expiry = contract.lastTradeDateOrContractMonth
        if len(expiry) == 8:
            expiry = expiry[2:]
        return f"{contract.symbol} {expiry}{contract.right}{contract.strike:g}"

    if isinstance(contract, ib.Future):
        return f"{contract.symbol} {contract.lastTradeDateOrContractMonth}"

    return str(contract.symbol)


def detect_asset_class(symbol: str) -> str:
    """Detect asset class from symbol format without creating a Contract."""
    if _OPTION_RE.match(symbol.strip()):
        return "option"
    if _FUTURE_RE.match(symbol.strip()):
        return "future"
    if "/" in symbol:
        return "crypto"
    return "stock"
