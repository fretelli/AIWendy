"""Tool executor: unified schema definitions + dispatch for REST and MCP."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from services.tool_definitions import TOOL_DEFINITIONS

logger = get_logger(__name__)

ToolHandler = Callable[[AsyncSession, UUID, dict[str, Any]], Awaitable[dict[str, Any]]]


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
