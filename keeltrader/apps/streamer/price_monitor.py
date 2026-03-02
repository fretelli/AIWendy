"""Price monitor — alert rule engine for market data streams."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PriceAlert:
    """A price alert rule."""

    symbol: str
    condition: str  # above, below, cross_above, cross_below, pct_change
    threshold: float
    user_id: str | None = None
    label: str = ""
    triggered: bool = False
    last_price: float = 0.0


class PriceMonitor:
    """Evaluates price data against alert rules and generates events."""

    def __init__(self) -> None:
        self._alerts: list[PriceAlert] = []
        self._prices: dict[str, float] = {}  # symbol -> last price
        self._prev_prices: dict[str, float] = {}  # symbol -> previous price

    def add_alert(self, alert: PriceAlert) -> None:
        self._alerts.append(alert)

    def remove_alerts(self, symbol: str) -> None:
        self._alerts = [a for a in self._alerts if a.symbol != symbol]

    @property
    def watched_symbols(self) -> set[str]:
        return {a.symbol for a in self._alerts}

    def update_price(self, symbol: str, price: float) -> list[dict[str, Any]]:
        """Update price and check all alerts for this symbol.

        Returns list of triggered alert event payloads.
        """
        self._prev_prices[symbol] = self._prices.get(symbol, price)
        self._prices[symbol] = price

        triggered = []
        for alert in self._alerts:
            if alert.symbol != symbol or alert.triggered:
                continue

            if self._check_condition(alert, price):
                alert.triggered = True
                alert.last_price = price
                triggered.append({
                    "symbol": symbol,
                    "alert_type": alert.condition,
                    "threshold": alert.threshold,
                    "price": price,
                    "label": alert.label,
                    "user_id": alert.user_id,
                })
                logger.info(
                    "Price alert triggered: %s %s %.2f (price=%.2f)",
                    symbol, alert.condition, alert.threshold, price,
                )

        return triggered

    def _check_condition(self, alert: PriceAlert, price: float) -> bool:
        prev = self._prev_prices.get(alert.symbol, price)

        if alert.condition == "above":
            return price >= alert.threshold
        elif alert.condition == "below":
            return price <= alert.threshold
        elif alert.condition == "cross_above":
            return prev < alert.threshold <= price
        elif alert.condition == "cross_below":
            return prev > alert.threshold >= price
        elif alert.condition == "pct_change":
            if prev == 0:
                return False
            pct = abs((price - prev) / prev) * 100
            return pct >= alert.threshold
        return False

    def add_default_alerts(self, symbol: str) -> None:
        """Add default monitoring alerts for a symbol (major level changes)."""
        price = self._prices.get(symbol)
        if not price:
            return

        # Alert on ±5% move from current price
        self.add_alert(PriceAlert(
            symbol=symbol,
            condition="pct_change",
            threshold=5.0,
            label=f"{symbol} ±5% move",
        ))
