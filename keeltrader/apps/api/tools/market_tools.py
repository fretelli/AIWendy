"""Market data tools: get_market_data, generate_chart."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from tools.trade_tools import _get_active_connections, _build_adapter

logger = get_logger(__name__)


async def get_market_data(
    session: AsyncSession,
    user_id: UUID,
    symbol: str,
    timeframe: str = "1h",
    limit: int = 100,
) -> dict[str, Any]:
    """获取行情数据（K线 + ticker）。"""
    connections = await _get_active_connections(session, user_id)
    if not connections:
        # Try public data with unauthenticated adapter
        try:
            from apps.exchange.ccxt_adapter import CcxtAdapter
            adapter = CcxtAdapter(exchange_name="okx")
            ticker = await adapter.fetch_ticker(symbol)
            ohlcv = await adapter.fetch_ohlcv(symbol, timeframe, limit)
            await adapter.close()
            return {
                "symbol": symbol,
                "ticker": {
                    "last": ticker.last,
                    "bid": ticker.bid,
                    "ask": ticker.ask,
                    "high_24h": ticker.high_24h,
                    "low_24h": ticker.low_24h,
                    "volume_24h": ticker.volume_24h,
                    "change_pct_24h": ticker.change_pct_24h,
                },
                "ohlcv": ohlcv,
                "timeframe": timeframe,
            }
        except Exception as e:
            return {"error": f"无法获取 {symbol} 行情: {str(e)}"}

    conn = connections[0]
    adapter = _build_adapter(conn)
    try:
        ticker = await adapter.fetch_ticker(symbol)
        ohlcv = await adapter.fetch_ohlcv(symbol, timeframe, limit)

        return {
            "symbol": symbol,
            "exchange": conn.exchange_type.value,
            "ticker": {
                "last": ticker.last,
                "bid": ticker.bid,
                "ask": ticker.ask,
                "high_24h": ticker.high_24h,
                "low_24h": ticker.low_24h,
                "volume_24h": ticker.volume_24h,
                "change_pct_24h": ticker.change_pct_24h,
            },
            "ohlcv": ohlcv,
            "timeframe": timeframe,
        }
    except Exception as e:
        return {"error": f"获取行情失败: {str(e)}"}
    finally:
        await adapter.close()


async def generate_chart(
    session: AsyncSession,
    user_id: UUID,
    symbol: str,
    chart_type: str = "candlestick",
    timeframe: str = "1h",
    indicators: Optional[list[str]] = None,
    days: int = 7,
) -> dict[str, Any]:
    """生成图表数据（前端渲染）。"""
    limit = {"1m": 60 * 24, "5m": 288, "15m": 96, "1h": 24, "4h": 6, "1d": 1}.get(timeframe, 24) * days
    limit = min(limit, 1000)

    market_data = await get_market_data(session, user_id, symbol, timeframe, limit)
    if "error" in market_data:
        return market_data

    ohlcv = market_data.get("ohlcv", [])
    if not ohlcv:
        return {"error": "无行情数据"}

    chart_data = {
        "symbol": symbol,
        "type": chart_type,
        "timeframe": timeframe,
        "candles": [
            {
                "time": c[0],
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5] if len(c) > 5 else 0,
            }
            for c in ohlcv
        ],
    }

    # Calculate requested indicators
    if indicators:
        closes = [c[4] for c in ohlcv if len(c) >= 5]
        import numpy as np
        closes_arr = np.array(closes)

        indicator_data = {}
        for ind in indicators:
            if ind.startswith("ma") and ind[2:].isdigit():
                period = int(ind[2:])
                if len(closes) >= period:
                    ma = []
                    for i in range(len(closes)):
                        if i >= period - 1:
                            ma.append(float(np.mean(closes_arr[i - period + 1: i + 1])))
                        else:
                            ma.append(None)
                    indicator_data[ind] = ma

            elif ind == "rsi":
                if len(closes) >= 15:
                    rsi_values = _calc_rsi(closes_arr)
                    indicator_data["rsi"] = [float(v) if v is not None else None for v in rsi_values]

        chart_data["indicators"] = indicator_data

    return chart_data


def _calc_rsi(closes, period=14):
    """Calculate RSI values."""
    import numpy as np
    deltas = np.diff(closes)
    rsi_values = [None] * period

    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

    return rsi_values
