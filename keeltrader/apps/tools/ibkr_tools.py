"""IBKR-specific tools — contract search, option chains, Greeks, margin, market hours.

These tools are registered for guardian and executor agents when the user
has an IBKR connection configured.  They use ib_async via the IbkrAdapter.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from pydantic_ai import RunContext

from ..agents.base import AgentDependencies

logger = logging.getLogger(__name__)

# Lazy import ib_async (same pattern as ibkr_adapter.py)
_ib_async = None


def _get_ib():
    global _ib_async
    if _ib_async is None:
        import ib_async
        _ib_async = ib_async
    return _ib_async


async def _get_ibkr_connection(deps: AgentDependencies):
    """Get an ib_async IB connection from agent dependencies."""
    ib = _get_ib()
    conn = ib.IB()

    host = deps.extra.get("ibkr_gateway_host", "keeltrader-ib-gateway")
    port = int(deps.extra.get("ibkr_gateway_port", 4001))
    client_id = int(deps.extra.get("ibkr_client_id", 10))  # Separate client_id for tools

    if not conn.isConnected():
        await conn.connectAsync(host=host, port=port, clientId=client_id, readonly=True)

    return conn


async def search_contracts(
    ctx: RunContext[AgentDependencies],
    pattern: str,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
) -> list[dict[str, Any]]:
    """Search for IBKR contracts matching a pattern.

    Args:
        pattern: Symbol or partial name to search (e.g., "AAPL", "Apple")
        sec_type: Security type — STK (stock), OPT (option), FUT (future)
        exchange: Exchange (default SMART for best routing)
        currency: Currency filter (default USD)

    Returns:
        List of matching contracts with details.
    """
    conn = await _get_ibkr_connection(ctx.deps)
    try:
        matches = await conn.reqMatchingSymbolsAsync(pattern)
        if not matches:
            return []

        results = []
        for desc in matches[:10]:  # Limit to 10 results
            contract = desc.contract
            results.append({
                "symbol": contract.symbol,
                "secType": contract.secType,
                "exchange": contract.primaryExchange or contract.exchange,
                "currency": contract.currency,
                "conId": contract.conId,
                "description": getattr(desc, "contractDescs", [""])[0]
                if hasattr(desc, "contractDescs") else "",
                "derivativeSecTypes": list(desc.derivativeSecTypes)
                if hasattr(desc, "derivativeSecTypes") else [],
            })

        return results
    finally:
        conn.disconnect()


async def get_option_chain(
    ctx: RunContext[AgentDependencies],
    symbol: str,
    exchange: str = "SMART",
) -> dict[str, Any]:
    """Get the option chain for a stock.

    Args:
        symbol: Underlying stock symbol (e.g., "AAPL")
        exchange: Exchange (default SMART)

    Returns:
        Dict with expirations and strikes available.
    """
    ib = _get_ib()
    conn = await _get_ibkr_connection(ctx.deps)
    try:
        # Create and qualify the underlying contract
        stock = ib.Stock(symbol, exchange, "USD")
        qualified = await conn.qualifyContractsAsync(stock)
        if not qualified:
            return {"error": f"无法找到标的 {symbol}"}

        stock = qualified[0]

        # Request option chain parameters
        chains = await conn.reqSecDefOptParamsAsync(
            stock.symbol, "", stock.secType, stock.conId
        )

        if not chains:
            return {"error": f"{symbol} 没有可用的期权链"}

        # Find the SMART exchange chain (or first available)
        chain = None
        for c in chains:
            if c.exchange == "SMART":
                chain = c
                break
        if chain is None:
            chain = chains[0]

        return {
            "symbol": symbol,
            "exchange": chain.exchange,
            "expirations": sorted(list(chain.expirations))[:12],  # Next 12 expirations
            "strikes": sorted(list(chain.strikes)),
            "multiplier": chain.multiplier,
            "tradingClass": chain.tradingClass,
            "total_expirations": len(chain.expirations),
            "total_strikes": len(chain.strikes),
        }
    finally:
        conn.disconnect()


async def get_option_greeks(
    ctx: RunContext[AgentDependencies],
    symbol: str,
    expiration: str,
    strike: float,
    right: str = "C",
) -> dict[str, Any]:
    """Get option Greeks (delta, gamma, theta, vega, IV) for a specific contract.

    Args:
        symbol: Underlying symbol (e.g., "AAPL")
        expiration: Expiration date (YYYYMMDD format, e.g., "20250321")
        strike: Strike price
        right: "C" for call, "P" for put

    Returns:
        Dict with Greeks and pricing info.
    """
    ib = _get_ib()
    conn = await _get_ibkr_connection(ctx.deps)
    try:
        contract = ib.Option(symbol, expiration, strike, right, "SMART")
        qualified = await conn.qualifyContractsAsync(contract)
        if not qualified:
            return {"error": f"无法找到期权合约 {symbol} {expiration} {strike}{right}"}

        contract = qualified[0]

        # Request market data with Greeks
        ticker = conn.reqMktData(contract, genericTickList="106", snapshot=True)

        # Wait for data
        for _ in range(30):  # 3 seconds max
            await asyncio.sleep(0.1)
            if ticker.modelGreeks is not None or ticker.lastGreeks is not None:
                break

        greeks = ticker.modelGreeks or ticker.lastGreeks

        result: dict[str, Any] = {
            "symbol": symbol,
            "expiration": expiration,
            "strike": strike,
            "right": right,
            "last": float(ticker.last) if ticker.last is not None else None,
            "bid": float(ticker.bid) if ticker.bid is not None else None,
            "ask": float(ticker.ask) if ticker.ask is not None else None,
            "volume": int(ticker.volume) if ticker.volume is not None else None,
            "openInterest": int(ticker.callOpenInterest if right == "C" else ticker.putOpenInterest)
            if (ticker.callOpenInterest or ticker.putOpenInterest) else None,
        }

        if greeks:
            result["greeks"] = {
                "delta": round(greeks.delta, 4) if greeks.delta is not None else None,
                "gamma": round(greeks.gamma, 6) if greeks.gamma is not None else None,
                "theta": round(greeks.theta, 4) if greeks.theta is not None else None,
                "vega": round(greeks.vega, 4) if greeks.vega is not None else None,
                "impliedVol": round(greeks.impliedVol, 4) if greeks.impliedVol is not None else None,
                "undPrice": round(greeks.undPrice, 2) if greeks.undPrice is not None else None,
                "optPrice": round(greeks.optPrice, 2) if greeks.optPrice is not None else None,
            }
        else:
            result["greeks"] = None
            result["warning"] = "Greeks 数据暂未返回，可能需要市场数据订阅"

        return result
    finally:
        conn.disconnect()


async def get_margin_requirements(
    ctx: RunContext[AgentDependencies],
    symbol: str,
    sec_type: str = "STK",
    action: str = "BUY",
    quantity: float = 100,
) -> dict[str, Any]:
    """Query margin requirements for a proposed order (what-if).

    Args:
        symbol: Symbol (e.g., "AAPL", "ES")
        sec_type: Security type — STK, OPT, FUT
        action: "BUY" or "SELL"
        quantity: Number of shares/contracts

    Returns:
        Dict with initial and maintenance margin requirements.
    """
    ib = _get_ib()
    conn = await _get_ibkr_connection(ctx.deps)
    try:
        # Build contract based on sec_type
        if sec_type == "STK":
            contract = ib.Stock(symbol, "SMART", "USD")
        elif sec_type == "FUT":
            contract = ib.Future(symbol, exchange="CME")
        else:
            return {"error": f"不支持的证券类型 {sec_type}（请使用 get_option_greeks 查询期权）"}

        qualified = await conn.qualifyContractsAsync(contract)
        if not qualified:
            return {"error": f"无法找到合约 {symbol}"}
        contract = qualified[0]

        # Create a what-if order for margin check
        order = ib.Order(
            action=action,
            totalQuantity=quantity,
            orderType="MKT",
            whatIf=True,
        )

        trade = conn.placeOrder(contract, order)
        await asyncio.sleep(2)

        status = trade.orderStatus
        if status and hasattr(status, "initMarginBefore"):
            return {
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "initMarginBefore": status.initMarginBefore,
                "maintMarginBefore": status.maintMarginBefore,
                "initMarginChange": status.initMarginChange,
                "maintMarginChange": status.maintMarginChange,
                "initMarginAfter": status.initMarginAfter,
                "maintMarginAfter": status.maintMarginAfter,
                "equityWithLoanBefore": status.equityWithLoanBefore,
                "equityWithLoanAfter": status.equityWithLoanAfter,
            }
        else:
            return {
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "warning": "保证金数据暂未返回",
            }
    finally:
        conn.disconnect()


async def get_market_hours(
    ctx: RunContext[AgentDependencies],
    exchange: str = "NYSE",
) -> dict[str, Any]:
    """Get current market hours and status for US equity markets.

    Args:
        exchange: Exchange name — NYSE, NASDAQ, CME, CBOE

    Returns:
        Dict with market status, hours, and next open/close times.
    """
    _ET = timezone(timedelta(hours=-5))
    now_et = datetime.now(_ET)
    weekday = now_et.weekday()

    # Regular trading hours (NYSE/NASDAQ)
    if exchange in ("NYSE", "NASDAQ", "SMART"):
        hours = {
            "exchange": exchange,
            "timezone": "US/Eastern",
            "current_time_et": now_et.strftime("%Y-%m-%d %H:%M:%S ET"),
            "pre_market": "04:00 - 09:30 ET",
            "regular": "09:30 - 16:00 ET",
            "after_hours": "16:00 - 20:00 ET",
        }

        current_mins = now_et.hour * 60 + now_et.minute

        if weekday >= 5:
            hours["status"] = "closed"
            hours["reason"] = "周末休市"
            days_until_monday = (7 - weekday) % 7
            if days_until_monday == 0:
                days_until_monday = 1
            hours["next_open"] = f"下周一 09:30 ET（{days_until_monday} 天后）"
        elif current_mins < 240:  # Before 04:00
            hours["status"] = "closed"
            hours["reason"] = "尚未到盘前时段"
        elif current_mins < 570:  # 04:00 - 09:30
            hours["status"] = "pre_market"
            hours["reason"] = "盘前交易时段"
            hours["regular_open_in"] = f"{(570 - current_mins)} 分钟"
        elif current_mins < 960:  # 09:30 - 16:00
            hours["status"] = "open"
            hours["reason"] = "正常交易时段"
            hours["close_in"] = f"{(960 - current_mins)} 分钟"
        elif current_mins < 1200:  # 16:00 - 20:00
            hours["status"] = "after_hours"
            hours["reason"] = "盘后交易时段"
        else:
            hours["status"] = "closed"
            hours["reason"] = "已收盘"

        return hours

    elif exchange == "CME":
        # CME futures: nearly 24h (Sun 17:00 - Fri 16:00 CT, with daily break 16:00-17:00 CT)
        return {
            "exchange": "CME",
            "timezone": "US/Central",
            "current_time_et": now_et.strftime("%Y-%m-%d %H:%M:%S ET"),
            "regular": "周日 17:00 CT - 周五 16:00 CT",
            "daily_break": "16:00 - 17:00 CT",
            "status": "open" if weekday < 5 else "closed",
            "note": "期货几乎 24 小时交易，每日 16:00-17:00 CT 短暂休息",
        }

    return {"exchange": exchange, "error": "不支持的交易所"}
