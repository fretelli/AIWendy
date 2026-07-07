"""Tool executor: unified schema definitions + dispatch for REST and MCP."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger

logger = get_logger(__name__)

ToolHandler = Callable[[AsyncSession, UUID, dict[str, Any]], Awaitable[dict[str, Any]]]

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
    # AgentOS tools
    {
        "name": "run_daily_brief",
        "description": "Generate an AgentOS daily investment brief from read-only data sources",
        "parameters": {
            "type": "object",
            "properties": {
                "watchlist": {"type": "array", "items": {"type": "string"}, "description": "Symbols to include"},
                "symbols": {"type": "array", "items": {"type": "string"}, "description": "Alias for watchlist"},
            },
        },
    },
    {
        "name": "deep_research",
        "description": "Run structured AgentOS deep research for a symbol",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "market": {"type": "string", "description": "Optional market label"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "record_investment_decision",
        "description": "Record a human-in-the-loop investment decision journal entry",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "action": {"type": "string"},
                "thesis": {"type": "string"},
                "confidence": {"type": "number"},
                "human_decision": {"type": "string", "default": "pending"},
                "human_reason": {"type": "string"},
                "falsifiers": {"type": "array", "items": {}},
                "risk_plan": {"type": "object"},
                "position_plan": {"type": "object"},
            },
            "required": ["symbol", "action", "thesis"],
        },
    },
    {
        "name": "run_weekly_review",
        "description": "Generate pending AgentOS weekly review lessons from decision logs",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "query_tushare_data",
        "description": "Query allowlisted synchronized Tushare PostgreSQL tables without using a Tushare token",
        "parameters": {
            "type": "object",
            "properties": {
                "table": {"type": "string"},
                "filters": {"type": "object"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["table"],
        },
    },
    {
        "name": "query_research_reports",
        "description": "Search report-kb research reports for AgentOS research context",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
                "companies": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["query"],
        },
    },
    {
        "name": "backtest_hypothesis",
        "description": "Run a guarded AgentOS v1 backtest and persist the result",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "strategy": {"type": "string", "default": "ma_crossover"},
                "params": {"type": "object"},
                "hypothesis_id": {"type": "string"},
            },
            "required": ["symbol"],
        },
    },
]


async def _call_get_positions(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.trade_tools import get_positions

    return await get_positions(session, user_id, **args)


async def _call_get_pnl(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.settings_tools import get_pnl

    return await get_pnl(session, user_id, **args)


async def _call_query_trades(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.trade_tools import query_trades

    return await query_trades(session, user_id, **args)


async def _call_analyze_performance(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.analysis_tools import analyze_performance

    return await analyze_performance(session, user_id, **args)


async def _call_get_market_data(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.market_tools import get_market_data

    return await get_market_data(session, user_id, **args)


async def _call_analyze_market(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.analysis_tools import analyze_market

    return await analyze_market(session, user_id, **args)


async def _call_place_order(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.execution_tools import place_order

    return await place_order(session, user_id, **args)


async def _call_cancel_order(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.execution_tools import cancel_order

    return await cancel_order(session, user_id, **args)


async def _call_manage_journal(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.trade_tools import manage_journal

    return await manage_journal(session, user_id, **args)


async def _call_update_settings(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.settings_tools import update_settings

    return await update_settings(session, user_id, **args)


async def _call_generate_chart(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.market_tools import generate_chart

    return await generate_chart(session, user_id, **args)


async def _call_backtest_strategy(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.backtest_tools import backtest_strategy

    return await backtest_strategy(session, user_id, **args)


async def _call_replay_my_trades(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.backtest_tools import replay_my_trades

    return await replay_my_trades(session, user_id, **args)


async def _call_get_character(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.rpg_tools import get_character

    return await get_character(session, user_id, **args)


async def _call_get_achievements(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.rpg_tools import get_achievements_tool

    return await get_achievements_tool(session, user_id, **args)


async def _call_start_quest(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.rpg_tools import start_quest_tool

    return await start_quest_tool(session, user_id, **args)


async def _call_check_quest_progress(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.rpg_tools import check_quest_progress_tool

    return await check_quest_progress_tool(session, user_id, **args)


async def _call_get_leaderboard(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.rpg_tools import get_leaderboard_tool

    return await get_leaderboard_tool(session, user_id, **args)


async def _call_generate_trading_card(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.rpg_tools import generate_trading_card

    return await generate_trading_card(session, user_id, **args)


async def _call_sync_trades(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from tools.rpg_tools import sync_trades_tool

    return await sync_trades_tool(session, user_id, **args)


async def _call_run_daily_brief(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from services.agentos.service import AgentOSService

    svc = AgentOSService(session)
    brief = await svc.run_daily_brief(user_id, args.get("watchlist") or args.get("symbols") or [])
    return {"brief_id": str(brief.id), "summary": brief.summary, "signals": brief.signals}


async def _call_deep_research(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from services.agentos.service import AgentOSService

    svc = AgentOSService(session)
    memo = await svc.run_deep_research(user_id, args["symbol"], args.get("market"))
    return {
        "memo_id": str(memo.id),
        "symbol": memo.symbol,
        "title": memo.title,
        "recommendation": memo.recommendation,
        "bull_case": memo.bull_case,
        "bear_case": memo.bear_case,
        "red_team": memo.red_team,
        "risk_view": memo.risk_view,
        "falsifiers": memo.falsifiers,
    }


async def _call_record_investment_decision(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from services.agentos.service import AgentOSService

    svc = AgentOSService(session)
    decision = await svc.record_decision(user_id, args)
    return {"decision_id": str(decision.id), "status": decision.status, "human_decision": decision.human_decision}


async def _call_run_weekly_review(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from services.agentos.service import AgentOSService

    svc = AgentOSService(session)
    lessons = await svc.run_weekly_review(user_id)
    return {
        "lessons": [
            {"lesson_id": str(l.id), "title": l.title, "lesson": l.lesson, "approved": l.approved}
            for l in lessons
        ]
    }


async def _call_query_tushare_data(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from services.agentos.tushare_read import TushareReadService

    svc = TushareReadService(session)
    rows = await svc.query_table(args["table"], args.get("filters") or {}, args.get("limit", 50))
    return {"rows": rows, "tushare_token_required": False}


async def _call_query_research_reports(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from services.agentos.report_kb import ReportKBService

    svc = ReportKBService()
    rows = await svc.search_reports(
        args["query"],
        top_k=args.get("top_k", 5),
        companies=args.get("companies") or None,
    )
    return {"reports": rows}


async def _call_backtest_hypothesis(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from services.agentos.service import AgentOSService

    svc = AgentOSService(session)
    hypothesis_id = UUID(args["hypothesis_id"]) if args.get("hypothesis_id") else None
    run = await svc.record_backtest(
        user_id,
        symbol=args["symbol"],
        strategy=args.get("strategy", "ma_crossover"),
        params=args.get("params") or {},
        hypothesis_id=hypothesis_id,
    )
    return {
        "backtest_id": str(run.id),
        "metrics": run.metrics,
        "passed_gate": run.passed_gate,
        "notes": run.notes,
    }


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_positions": _call_get_positions,
    "get_pnl": _call_get_pnl,
    "query_trades": _call_query_trades,
    "analyze_performance": _call_analyze_performance,
    "get_market_data": _call_get_market_data,
    "analyze_market": _call_analyze_market,
    "place_order": _call_place_order,
    "cancel_order": _call_cancel_order,
    "manage_journal": _call_manage_journal,
    "update_settings": _call_update_settings,
    "generate_chart": _call_generate_chart,
    "backtest_strategy": _call_backtest_strategy,
    "replay_my_trades": _call_replay_my_trades,
    "get_character": _call_get_character,
    "get_achievements": _call_get_achievements,
    "start_quest": _call_start_quest,
    "check_quest_progress": _call_check_quest_progress,
    "get_leaderboard": _call_get_leaderboard,
    "generate_trading_card": _call_generate_trading_card,
    "sync_trades": _call_sync_trades,
    "run_daily_brief": _call_run_daily_brief,
    "deep_research": _call_deep_research,
    "record_investment_decision": _call_record_investment_decision,
    "run_weekly_review": _call_run_weekly_review,
    "query_tushare_data": _call_query_tushare_data,
    "query_research_reports": _call_query_research_reports,
    "backtest_hypothesis": _call_backtest_hypothesis,
}


def get_tool_names() -> set[str]:
    """Return the executable tool names."""
    return set(TOOL_HANDLERS)


async def execute_tool(
    name: str,
    args: dict[str, Any],
    session: AsyncSession,
    user_id: UUID,
) -> dict[str, Any]:
    """Execute a tool by name with given arguments."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}

    try:
        return await handler(session, user_id, args)
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
