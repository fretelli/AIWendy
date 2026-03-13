"""Tool executor: unified schema definitions + dispatch for REST and MCP."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger

logger = get_logger(__name__)

# Tool definitions shared between REST API and MCP Server
TOOL_DEFINITIONS = [
    {
        "name": "get_positions",
        "description": "Query current positions across all exchanges",
        "parameters": {
            "type": "object",
            "properties": {
                "exchange": {"type": "string", "description": "Exchange name (okx/bybit), leave empty for all"},
                "symbol": {"type": "string", "description": "Trading pair (e.g. BTC/USDT), leave empty for all"},
            },
        },
    },
    {
        "name": "get_pnl",
        "description": "Query PnL for a specified period",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Period: today/week/month/all", "default": "today"},
            },
        },
    },
    {
        "name": "query_trades",
        "description": "Query historical trade records",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair filter"},
                "days": {"type": "integer", "description": "Number of days to query", "default": 7},
                "limit": {"type": "integer", "description": "Number of results to return", "default": 50},
            },
        },
    },
    {
        "name": "analyze_performance",
        "description": "Analyze trading performance (win rate, profit factor, streaks, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to analyze", "default": 30},
                "symbol": {"type": "string", "description": "Filter by trading pair"},
            },
        },
    },
    {
        "name": "get_market_data",
        "description": "Get market data (candlesticks + real-time price)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair (e.g. BTC/USDT)"},
                "timeframe": {"type": "string", "description": "Candlestick timeframe", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of candlesticks", "default": 100},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "analyze_market",
        "description": "AI technical analysis (MA/RSI/volatility, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair"},
                "timeframe": {"type": "string", "description": "Analysis timeframe", "default": "4h"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "place_order",
        "description": "Place an order (requires user confirmation)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair"},
                "side": {"type": "string", "enum": ["buy", "sell"], "description": "Buy or sell"},
                "amount": {"type": "number", "description": "Quantity"},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
                "price": {"type": "number", "description": "Limit order price"},
                "stop_loss": {"type": "number", "description": "Stop loss price"},
                "take_profit": {"type": "number", "description": "Take profit price"},
                "exchange": {"type": "string", "description": "Exchange"},
                "confirmed": {"type": "boolean", "description": "Whether confirmed", "default": False},
            },
            "required": ["symbol", "side", "amount"],
        },
    },
    {
        "name": "cancel_order",
        "description": "Cancel an order",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID"},
                "symbol": {"type": "string", "description": "Trading pair"},
                "exchange": {"type": "string", "description": "Exchange"},
            },
            "required": ["order_id", "symbol"],
        },
    },
    {
        "name": "manage_journal",
        "description": "Manage trade journal (view/create/update)",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "get", "create"], "default": "list"},
                "journal_id": {"type": "string", "description": "Journal ID (required for get)"},
                "data": {"type": "object", "description": "Creation data"},
                "days": {"type": "integer", "default": 30},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "update_settings",
        "description": "Update risk parameters and push preferences",
        "parameters": {
            "type": "object",
            "properties": {
                "settings": {"type": "object", "description": "Settings key-value pairs to update"},
            },
            "required": ["settings"],
        },
    },
    {
        "name": "generate_chart",
        "description": "Generate chart data (candlestick + indicator overlay)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair"},
                "chart_type": {"type": "string", "default": "candlestick"},
                "timeframe": {"type": "string", "default": "1h"},
                "indicators": {"type": "array", "items": {"type": "string"}, "description": "Overlay indicators (e.g. ma20, rsi)"},
                "days": {"type": "integer", "default": 7},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "backtest_strategy",
        "description": "Backtest a trading strategy (MA crossover, RSI reversal, breakout)",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading pair"},
                "strategy": {"type": "string", "description": "Strategy name: ma_crossover/rsi/breakout"},
                "params": {"type": "object", "description": "Strategy parameters"},
                "days": {"type": "integer", "default": 90},
                "timeframe": {"type": "string", "default": "1d"},
            },
            "required": ["symbol", "strategy"],
        },
    },
    {
        "name": "replay_my_trades",
        "description": "Trade replay what-if analysis",
        "parameters": {
            "type": "object",
            "properties": {
                "journal_id": {"type": "string", "description": "Journal ID to replay"},
                "days": {"type": "integer", "description": "Replay period in days", "default": 7},
                "what_if": {"type": "object", "description": "What-if scenario (exit_price/position_size)"},
            },
        },
    },
    # RPG tools
    {
        "name": "get_character",
        "description": "Get your RPG trading character (level, rank, attributes)",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_achievements",
        "description": "Get achievements list (unlocked and locked)",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filter by category: trading/discipline/milestones/streaks"},
            },
        },
    },
    {
        "name": "start_quest",
        "description": "Start a quest by ID",
        "parameters": {
            "type": "object",
            "properties": {
                "quest_id": {"type": "string", "description": "Quest ID to start"},
            },
            "required": ["quest_id"],
        },
    },
    {
        "name": "check_quest_progress",
        "description": "Check progress on active quests",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_leaderboard",
        "description": "Get the trading leaderboard",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Period: weekly/monthly", "default": "weekly"},
            },
        },
    },
    {
        "name": "generate_trading_card",
        "description": "Generate a shareable trading card (character or weekly stats)",
        "parameters": {
            "type": "object",
            "properties": {
                "card_type": {"type": "string", "description": "Card type: character/weekly", "default": "character"},
            },
        },
    },
    {
        "name": "sync_trades",
        "description": "Sync trades and recalculate RPG character attributes",
        "parameters": {"type": "object", "properties": {}},
    },
]


async def execute_tool(
    name: str,
    args: dict[str, Any],
    session: AsyncSession,
    user_id: UUID,
) -> dict[str, Any]:
    """Execute a tool by name with given arguments."""
    try:
        if name == "get_positions":
            from tools.trade_tools import get_positions
            return await get_positions(session, user_id, **args)

        elif name == "get_pnl":
            from tools.settings_tools import get_pnl
            return await get_pnl(session, user_id, **args)

        elif name == "query_trades":
            from tools.trade_tools import query_trades
            return await query_trades(session, user_id, **args)

        elif name == "analyze_performance":
            from tools.analysis_tools import analyze_performance
            return await analyze_performance(session, user_id, **args)

        elif name == "get_market_data":
            from tools.market_tools import get_market_data
            return await get_market_data(session, user_id, **args)

        elif name == "analyze_market":
            from tools.analysis_tools import analyze_market
            return await analyze_market(session, user_id, **args)

        elif name == "place_order":
            from tools.execution_tools import place_order
            return await place_order(session, user_id, **args)

        elif name == "cancel_order":
            from tools.execution_tools import cancel_order
            return await cancel_order(session, user_id, **args)

        elif name == "manage_journal":
            from tools.trade_tools import manage_journal
            return await manage_journal(session, user_id, **args)

        elif name == "update_settings":
            from tools.settings_tools import update_settings
            return await update_settings(session, user_id, **args)

        elif name == "generate_chart":
            from tools.market_tools import generate_chart
            return await generate_chart(session, user_id, **args)

        elif name == "backtest_strategy":
            from tools.backtest_tools import backtest_strategy
            return await backtest_strategy(session, user_id, **args)

        elif name == "replay_my_trades":
            from tools.backtest_tools import replay_my_trades
            return await replay_my_trades(session, user_id, **args)

        # RPG tools
        elif name == "get_character":
            from tools.rpg_tools import get_character as rpg_get_character
            return await rpg_get_character(session, user_id, **args)

        elif name == "get_achievements":
            from tools.rpg_tools import get_achievements_tool
            return await get_achievements_tool(session, user_id, **args)

        elif name == "start_quest":
            from tools.rpg_tools import start_quest_tool
            return await start_quest_tool(session, user_id, **args)

        elif name == "check_quest_progress":
            from tools.rpg_tools import check_quest_progress_tool
            return await check_quest_progress_tool(session, user_id, **args)

        elif name == "get_leaderboard":
            from tools.rpg_tools import get_leaderboard_tool
            return await get_leaderboard_tool(session, user_id, **args)

        elif name == "generate_trading_card":
            from tools.rpg_tools import generate_trading_card
            return await generate_trading_card(session, user_id, **args)

        elif name == "sync_trades":
            from tools.rpg_tools import sync_trades_tool
            return await sync_trades_tool(session, user_id, **args)

        else:
            return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        logger.error("tool_execution_failed", tool=name, error=str(e), exc_info=True)
        return {"error": f"Tool execution failed: {str(e)}"}


def get_openai_tools() -> list[dict]:
    """Convert tool definitions to OpenAI function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in TOOL_DEFINITIONS
    ]
