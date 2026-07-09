"""Tool executor for read-only fundamental AgentOS workflows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from services.tool_definitions import TOOL_DEFINITIONS

logger = get_logger(__name__)

ToolHandler = Callable[[AsyncSession, UUID, dict[str, Any]], Awaitable[dict[str, Any]]]


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

    del args
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

    del user_id
    svc = TushareReadService(session)
    rows = await svc.query_table(args["table"], args.get("filters") or {}, args.get("limit", 50))
    return {"rows": rows, "tushare_token_required": False}


async def _call_query_research_reports(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from services.agentos.report_kb import ReportKBService

    del session, user_id
    svc = ReportKBService()
    rows = await svc.search_reports(
        args["query"],
        top_k=args.get("top_k", 5),
        companies=args.get("companies") or None,
    )
    return {"reports": rows}


async def _call_record_fundamental_validation(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    from services.agentos.service import AgentOSService

    svc = AgentOSService(session)
    hypothesis_id = UUID(args["hypothesis_id"]) if args.get("hypothesis_id") else None
    params = {
        "conclusion": args.get("conclusion", "observe"),
        "evidence": args.get("evidence") or [],
        "risks": args.get("risks") or [],
        "notes": args.get("notes"),
    }
    run = await svc.record_validation(
        user_id,
        symbol=args["symbol"],
        strategy="fundamental_validation",
        params=params,
        hypothesis_id=hypothesis_id,
    )
    return {
        "validation_id": str(run.id),
        "metrics": run.metrics,
        "passed_gate": run.passed_gate,
        "notes": run.notes,
    }


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "run_daily_brief": _call_run_daily_brief,
    "deep_research": _call_deep_research,
    "record_investment_decision": _call_record_investment_decision,
    "run_weekly_review": _call_run_weekly_review,
    "query_tushare_data": _call_query_tushare_data,
    "query_research_reports": _call_query_research_reports,
    "record_fundamental_validation": _call_record_fundamental_validation,
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
