"""Tool registry — central registration of MCP tools for PydanticAI agents.

Each agent gets a curated set of tools based on its role.
Tools are registered as PydanticAI tool functions via dependency injection.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from pydantic_ai import Agent

from ..agents.base import AgentDependencies

logger = logging.getLogger(__name__)


# Tool sets by category
TOOL_CATEGORIES: dict[str, list[str]] = {
    "market": [
        "get_price",
        "get_klines",
        "get_orderbook",
        "get_funding_rate",
        "calc_indicators",
    ],
    "analysis": [
        "full_technical_analysis",
        "multi_timeframe_analysis",
        "score_trade_setup",
    ],
    "portfolio": [
        "get_balance",
        "get_positions",
        "get_open_orders",
        "get_trade_history",
    ],
    "memory": [
        "memory_search",
        "memory_update",
        "memory_forget",
    ],
    "communication": [
        "send_telegram",
        "request_confirmation",
        "delegate_to_agent",
    ],
    "execution": [
        "place_order",
        "cancel_order",
        "close_position",
    ],
    "ibkr": [
        "search_contracts",
        "get_option_chain",
        "get_option_greeks",
        "get_margin_requirements",
        "get_market_hours",
    ],
}

# Agent type → allowed tool categories
AGENT_TOOL_MAP: dict[str, list[str]] = {
    "orchestrator": ["market", "analysis", "portfolio", "memory", "communication"],
    "technical": ["market", "analysis", "memory"],
    "sentiment": ["market", "memory"],
    "fundamental": ["market", "memory"],
    "psychology": ["memory", "communication"],
    "guardian": ["market", "portfolio", "memory", "communication", "ibkr"],
    "executor": ["market", "portfolio", "execution", "communication", "ibkr"],
}


def _get_tool_functions() -> dict[str, Callable]:
    """Lazy-load all tool functions."""
    from . import analysis, communication, execution, market, portfolio
    from . import ibkr_tools
    from ..memory import tools as memory_tools

    return {
        # Market tools
        "get_price": market.get_price,
        "get_klines": market.get_klines,
        "get_orderbook": market.get_orderbook,
        "get_funding_rate": market.get_funding_rate,
        "calc_indicators": market.calc_indicators,
        # Analysis tools
        "full_technical_analysis": analysis.full_technical_analysis,
        "multi_timeframe_analysis": analysis.multi_timeframe_analysis,
        "score_trade_setup": analysis.score_trade_setup,
        # Portfolio tools
        "get_balance": portfolio.get_balance,
        "get_positions": portfolio.get_positions,
        "get_open_orders": portfolio.get_open_orders,
        "get_trade_history": portfolio.get_trade_history,
        # Memory tools
        "memory_search": memory_tools.memory_search,
        "memory_update": memory_tools.memory_update,
        "memory_forget": memory_tools.memory_forget,
        # Execution tools
        "place_order": execution.place_order,
        "cancel_order": execution.cancel_order,
        "close_position": execution.close_position,
        # Communication tools
        "send_telegram": communication.send_telegram,
        "request_confirmation": communication.request_confirmation,
        "delegate_to_agent": communication.delegate_to_agent,
        # IBKR tools
        "search_contracts": ibkr_tools.search_contracts,
        "get_option_chain": ibkr_tools.get_option_chain,
        "get_option_greeks": ibkr_tools.get_option_greeks,
        "get_margin_requirements": ibkr_tools.get_margin_requirements,
        "get_market_hours": ibkr_tools.get_market_hours,
    }


def register_tools_for_agent(
    agent: Agent,
    agent_type: str,
    extra_tools: list[str] | None = None,
) -> list[str]:
    """Register appropriate tools on a PydanticAI agent based on its type.

    Args:
        agent: PydanticAI Agent instance
        agent_type: One of: orchestrator, technical, sentiment, fundamental,
                    psychology, guardian, executor
        extra_tools: Additional tool names to register beyond the default set

    Returns:
        List of registered tool names
    """
    allowed_categories = AGENT_TOOL_MAP.get(agent_type, [])
    allowed_tools = set()
    for cat in allowed_categories:
        allowed_tools.update(TOOL_CATEGORIES.get(cat, []))

    if extra_tools:
        allowed_tools.update(extra_tools)

    all_tools = _get_tool_functions()
    registered = []

    for tool_name in sorted(allowed_tools):
        func = all_tools.get(tool_name)
        if func is None:
            logger.warning("Tool %s not found in registry", tool_name)
            continue

        agent.tool(func)
        registered.append(tool_name)

    logger.info(
        "Registered %d tools for %s agent: %s",
        len(registered), agent_type, registered,
    )
    return registered


def get_available_tools(agent_type: str) -> list[str]:
    """Get list of tool names available for an agent type."""
    categories = AGENT_TOOL_MAP.get(agent_type, [])
    tools = []
    for cat in categories:
        tools.extend(TOOL_CATEGORIES.get(cat, []))
    return tools
