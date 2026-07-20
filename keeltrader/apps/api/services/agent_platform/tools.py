"""Research-only tool registry owned by the durable Agent Platform."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agent_platform.models import AgentArtifact
from services.agent_platform.report_kb import ReportKBService
from services.agent_platform.tushare import TushareReadService

ToolHandler = Callable[[AsyncSession, UUID, dict[str, Any]], Awaitable[dict[str, Any]]]

TOOL_DEFINITIONS = [
    {"name": "query_research_reports", "description": "Search the internal report knowledge base",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 5}, "companies": {"type": "array", "items": {"type": "string"}}}, "required": ["query"]}},
    {"name": "query_tushare_data", "description": "Read an allowlisted synchronized Tushare table",
     "parameters": {"type": "object", "properties": {"table": {"type": "string"}, "filters": {"type": "object"}, "limit": {"type": "integer", "default": 50}}, "required": ["table"]}},
    {"name": "run_daily_brief", "description": "Build a fundamental research brief",
     "parameters": {"type": "object", "properties": {"watchlist": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "deep_research", "description": "Build a structured company research memo",
     "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}, "market": {"type": "string"}}, "required": ["symbol"]}},
    {"name": "record_investment_decision", "description": "Create a human-approved research decision log",
     "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}, "action": {"type": "string"}, "thesis": {"type": "string"}, "confidence": {"type": "number"}, "falsifiers": {"type": "array", "items": {}}, "risk_plan": {"type": "object"}}, "required": ["symbol", "action", "thesis"]}},
    {"name": "run_weekly_review", "description": "Review approved decision-log artifacts from the last seven days",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "record_fundamental_validation", "description": "Record research evidence for a fundamental thesis",
     "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}, "conclusion": {"type": "string"}, "evidence": {"type": "array", "items": {}}, "risks": {"type": "array", "items": {}}, "notes": {"type": "string"}}, "required": ["symbol"]}},
    {"name": "search_holder", "description": "Search disclosed A-share top-10 floating shareholder names without excluding any holder type",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["query"]}},
    {"name": "holder_positions", "description": "Find stocks where an exact shareholder name appears in each company's latest disclosed top-10 floating shareholder list",
     "parameters": {"type": "object", "properties": {"holder_name": {"type": "string"}, "holder_type": {"type": "string", "default": "未知"}, "aliases": {"type": "array", "items": {"type": "string"}}, "limit": {"type": "integer", "default": 100}}, "required": ["holder_name", "holder_type"]}},
    {"name": "holder_history", "description": "Return objective quarter-by-quarter top-10 floating shareholder changes and exits",
     "parameters": {"type": "object", "properties": {"holder_name": {"type": "string"}, "holder_type": {"type": "string", "default": "未知"}, "aliases": {"type": "array", "items": {"type": "string"}}, "limit": {"type": "integer", "default": 200}}, "required": ["holder_name", "holder_type"]}},
    {"name": "market_capital_snapshot", "description": "Return a deterministic, source-dated full A-share post-close capital snapshot without scoring or recommendations",
     "parameters": {"type": "object", "properties": {"window": {"type": "integer", "default": 60, "minimum": 20, "maximum": 250}}}},
]


async def _reports(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del session, user_id
    rows = await ReportKBService().search_reports(args["query"], top_k=args.get("top_k", 5), companies=args.get("companies") or None)
    return {"reports": rows}


async def _tushare(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del user_id
    rows = await TushareReadService(session).query_table(args["table"], args.get("filters") or {}, args.get("limit", 50))
    return {"rows": rows, "tushare_token_required": False}


async def _brief(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del user_id
    tushare, reports = TushareReadService(session), ReportKBService()
    signals = []
    for symbol in (args.get("watchlist") or args.get("symbols") or [])[:20]:
        profile = await tushare.stock_profile(symbol)
        bars = await tushare.daily_bars(symbol, limit=2, adjusted=False)
        financials = await tushare.financial_indicators(symbol, limit=2)
        query = " ".join(filter(None, [profile.get("name") if profile else None, symbol]))
        hits = await reports.search_reports(query or symbol, top_k=3)
        signals.append({"symbol": symbol, "profile": profile, "latest_price_context": bars[:1],
                        "has_financials": bool(financials), "reports": hits, "research_only": True})
    return {"title": f"Research Brief {datetime.now(UTC).date().isoformat()}", "signals": signals,
            "risks": ["Research support only; verify source dates and fundamentals before any human decision."]}


async def _deep_research(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del user_id
    symbol = args["symbol"]
    tushare = TushareReadService(session)
    profile = await tushare.stock_profile(symbol)
    financials = await tushare.financial_indicators(symbol, limit=4)
    price = await tushare.daily_bars(symbol, limit=1, adjusted=False)
    hits = await ReportKBService().search_reports(" ".join(filter(None, [profile.get("name") if profile else None, symbol, "基本面 风险"])), top_k=8)
    return {"symbol": symbol, "market": args.get("market") or "cn_equity", "profile": profile,
            "financials": financials, "latest_price_context": price[:1], "reports": hits,
            "bull_case": "Requires durable earnings, cash generation, governance, and valuation support.",
            "bear_case": "Includes deteriorating fundamentals, stale data, governance, and valuation risk.",
            "falsifiers": ["New evidence contradicts the thesis", "Financial data is stale or restated"],
            "recommendation": "research_only"}


async def _decision(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del session, user_id
    return {"type": "decision_log", "status": "approved", "recorded_at": datetime.now(UTC).isoformat(), **args}


async def _weekly_review(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del args
    since = datetime.now(UTC) - timedelta(days=7)
    rows = (await session.execute(select(AgentArtifact).where(
        AgentArtifact.user_id == user_id, AgentArtifact.artifact_type == "decision_log",
        AgentArtifact.created_at >= since,
    ))).scalars().all()
    return {"decision_count": len(rows), "evidence": [{"artifact_id": str(row.id), "title": row.title} for row in rows],
            "lesson": "Review evidence quality, falsifiers, and whether the human decision followed the stated process."}


async def _validation(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    financials = await TushareReadService(session).financial_indicators(args["symbol"], limit=4)
    evidence = args.get("evidence") if isinstance(args.get("evidence"), list) else []
    return {"symbol": args["symbol"], "conclusion": args.get("conclusion") or "observe",
            "evidence": evidence, "risks": args.get("risks") or [], "notes": args.get("notes"),
            "has_recent_financials": bool(financials), "passed_gate": bool(financials and evidence),
            "research_only": True, "user_id": str(user_id)}


async def _search_holder(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del user_id
    service = TushareReadService(session)
    items = await service.search_holders(str(args["query"]), int(args.get("limit", 20)))
    return {"items": items, "source_available": await service.table_exists("top10_floatholders"),
            "identity_note": "Natural-person names are disclosure-name matches and may include namesakes."}


def _holder_tool_names(args: dict[str, Any]) -> list[str]:
    values = [args.get("holder_name"), *(args.get("aliases") or [])]
    return [str(value).strip() for value in values if str(value or "").strip()]


async def _holder_positions(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del user_id
    return await TushareReadService(session).holder_current_positions(
        _holder_tool_names(args), str(args.get("holder_type") or "未知"),
        limit=int(args.get("limit", 100)),
    )


async def _holder_history(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del user_id
    result = await TushareReadService(session).holder_history(
        _holder_tool_names(args), str(args.get("holder_type") or "未知"),
        limit=int(args.get("limit", 200)),
    )
    result["exit_note"] = "exited_top10 means absent from a later disclosed top-ten list, not a confirmed full sale."
    return result


async def _market_capital(session: AsyncSession, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    del user_id
    return await TushareReadService(session).market_capital_snapshot(int(args.get("window", 60)))


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "query_research_reports": _reports,
    "query_tushare_data": _tushare,
    "run_daily_brief": _brief,
    "deep_research": _deep_research,
    "record_investment_decision": _decision,
    "run_weekly_review": _weekly_review,
    "record_fundamental_validation": _validation,
    "search_holder": _search_holder,
    "holder_positions": _holder_positions,
    "holder_history": _holder_history,
    "market_capital_snapshot": _market_capital,
}


async def execute_platform_tool(name: str, args: dict[str, Any], session: AsyncSession, user_id: UUID) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await handler(session, user_id, args)
    except Exception as exc:
        return {"error": f"Tool execution failed: {str(exc)}"}
