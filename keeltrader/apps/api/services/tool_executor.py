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
        "description": "查询当前所有交易所的持仓情况",
        "parameters": {
            "type": "object",
            "properties": {
                "exchange": {"type": "string", "description": "交易所名称（okx/bybit），留空查全部"},
                "symbol": {"type": "string", "description": "交易对（如 BTC/USDT），留空查全部"},
            },
        },
    },
    {
        "name": "get_pnl",
        "description": "查询指定时段的盈亏情况",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "时段：today/week/month/all", "default": "today"},
            },
        },
    },
    {
        "name": "query_trades",
        "description": "查询历史交易记录",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "交易对筛选"},
                "days": {"type": "integer", "description": "查询天数", "default": 7},
                "limit": {"type": "integer", "description": "返回条数", "default": 50},
            },
        },
    },
    {
        "name": "analyze_performance",
        "description": "分析交易表现（胜率、盈亏比、最大连胜/连亏等）",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "分析天数", "default": 30},
                "symbol": {"type": "string", "description": "按交易对筛选"},
            },
        },
    },
    {
        "name": "detect_patterns",
        "description": "检测交易行为模式（FOMO、报复交易、过度交易等）",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "检测天数", "default": 14},
            },
        },
    },
    {
        "name": "get_market_data",
        "description": "获取行情数据（K线 + 实时价格）",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "交易对（如 BTC/USDT）"},
                "timeframe": {"type": "string", "description": "K线周期", "default": "1h"},
                "limit": {"type": "integer", "description": "K线数量", "default": 100},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "analyze_market",
        "description": "AI 分析市场技术面（MA/RSI/波动率等）",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "交易对"},
                "timeframe": {"type": "string", "description": "分析周期", "default": "4h"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "place_order",
        "description": "下单交易（需用户确认）",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "交易对"},
                "side": {"type": "string", "enum": ["buy", "sell"], "description": "买卖方向"},
                "amount": {"type": "number", "description": "数量"},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
                "price": {"type": "number", "description": "限价单价格"},
                "stop_loss": {"type": "number", "description": "止损价"},
                "take_profit": {"type": "number", "description": "止盈价"},
                "exchange": {"type": "string", "description": "交易所"},
                "confirmed": {"type": "boolean", "description": "是否已确认", "default": False},
            },
            "required": ["symbol", "side", "amount"],
        },
    },
    {
        "name": "cancel_order",
        "description": "撤销订单",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单 ID"},
                "symbol": {"type": "string", "description": "交易对"},
                "exchange": {"type": "string", "description": "交易所"},
            },
            "required": ["order_id", "symbol"],
        },
    },
    {
        "name": "search_knowledge",
        "description": "搜索交易知识库",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "top_k": {"type": "integer", "description": "返回条数", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "manage_journal",
        "description": "管理交易日志（查看/创建/更新）",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "get", "create"], "default": "list"},
                "journal_id": {"type": "string", "description": "日志 ID（get 操作需要）"},
                "data": {"type": "object", "description": "创建数据"},
                "days": {"type": "integer", "default": 30},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "update_settings",
        "description": "更新风控参数和推送偏好",
        "parameters": {
            "type": "object",
            "properties": {
                "settings": {"type": "object", "description": "要更新的设置键值对"},
            },
            "required": ["settings"],
        },
    },
    {
        "name": "generate_chart",
        "description": "生成图表数据（K线、指标叠加）",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "交易对"},
                "chart_type": {"type": "string", "default": "candlestick"},
                "timeframe": {"type": "string", "default": "1h"},
                "indicators": {"type": "array", "items": {"type": "string"}, "description": "叠加指标（如 ma20, rsi）"},
                "days": {"type": "integer", "default": 7},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "backtest_strategy",
        "description": "回测交易策略（均线交叉、RSI反转、突破）",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "交易对"},
                "strategy": {"type": "string", "description": "策略名称：ma_crossover/rsi/breakout"},
                "params": {"type": "object", "description": "策略参数"},
                "days": {"type": "integer", "default": 90},
                "timeframe": {"type": "string", "default": "1d"},
            },
            "required": ["symbol", "strategy"],
        },
    },
    {
        "name": "replay_my_trades",
        "description": "交易回放 what-if 分析",
        "parameters": {
            "type": "object",
            "properties": {
                "journal_id": {"type": "string", "description": "指定日志 ID"},
                "days": {"type": "integer", "description": "回放天数", "default": 7},
                "what_if": {"type": "object", "description": "假设场景（exit_price/position_size）"},
            },
        },
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

        elif name == "detect_patterns":
            from tools.analysis_tools import detect_patterns
            return await detect_patterns(session, user_id, **args)

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

        elif name == "search_knowledge":
            from tools.knowledge_tools import search_knowledge
            return await search_knowledge(session, user_id, **args)

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

        else:
            return {"error": f"未知工具: {name}"}

    except Exception as e:
        logger.error("tool_execution_failed", tool=name, error=str(e), exc_info=True)
        return {"error": f"工具执行失败: {str(e)}"}


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
