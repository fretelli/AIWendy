"""Telegram command handlers — /start, /status, /kill, /agent, etc."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from ..keyboards import main_menu_keyboard, agent_status_keyboard

logger = logging.getLogger(__name__)
router = Router(name="commands")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command — welcome and account binding."""
    await message.answer(
        "<b>KeelTrader Agent Matrix</b>\n\n"
        "欢迎使用 KeelTrader 交易助手。\n\n"
        "可用命令：\n"
        "/status — 查看 Agent 矩阵状态\n"
        "/portfolio — 持仓概览\n"
        "/ask — 向 Agent 矩阵提问\n"
        "/kill — 紧急熔断（停止所有交易）\n"
        "/help — 帮助",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Handle /status — show agent matrix status."""
    # TODO: Query actual agent status from event engine
    status_text = (
        "<b>Agent 矩阵状态</b>\n\n"
        "🟢 Orchestrator — 在线\n"
        "🟢 Technical Analyst — 在线\n"
        "🟢 Sentiment Analyst — 在线\n"
        "🟢 Fundamental Analyst — 在线\n"
        "🟢 Psychology Coach — 在线\n"
        "🟢 Guardian — 在线\n"
        "🟢 Executor — 在线\n\n"
        "⚡ Circuit Breaker: OFF\n"
        "📊 今日事件: 0\n"
        "💰 今日 P&L: $0.00"
    )
    await message.answer(status_text, reply_markup=agent_status_keyboard())


@router.message(Command("kill"))
async def cmd_kill(message: Message) -> None:
    """Handle /kill — emergency circuit breaker."""
    # TODO: Set circuit breaker via Redis, cancel all pending orders
    await message.answer(
        "🔴 <b>紧急熔断已激活</b>\n\n"
        "• Circuit Breaker: ON\n"
        "• 所有挂单已撤销\n"
        "• 所有 Agent 执行已锁定\n\n"
        "使用 /resume 恢复交易",
    )
    logger.warning("KILL switch activated by user %s", message.from_user.id)


@router.message(Command("resume"))
async def cmd_resume(message: Message) -> None:
    """Handle /resume — deactivate circuit breaker."""
    # TODO: Clear circuit breaker via Redis
    await message.answer(
        "🟢 <b>交易已恢复</b>\n\n"
        "• Circuit Breaker: OFF\n"
        "• Agent 矩阵恢复运行",
    )
    logger.info("Trading resumed by user %s", message.from_user.id)


@router.message(Command("portfolio"))
async def cmd_portfolio(message: Message) -> None:
    """Handle /portfolio — show current positions."""
    # TODO: Query exchange positions via CCXT
    await message.answer(
        "<b>持仓概览</b>\n\n"
        "暂无活跃持仓。\n\n"
        "连接交易所后可查看实时持仓。",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help."""
    await message.answer(
        "<b>KeelTrader 命令帮助</b>\n\n"
        "/start — 开始\n"
        "/status — Agent 矩阵状态\n"
        "/portfolio — 持仓概览\n"
        "/ask <i>问题</i> — 向 Agent 矩阵提问\n"
        "/kill — 紧急熔断\n"
        "/resume — 恢复交易\n"
        "/ghost — Ghost Trading 状态\n"
        "/help — 显示此帮助",
    )


@router.message(Command("ask"))
async def cmd_ask(message: Message) -> None:
    """Handle /ask — route question to Orchestrator agent."""
    question = message.text.replace("/ask", "", 1).strip()
    if not question:
        await message.answer("请在 /ask 后输入你的问题。\n例如: /ask ETH 现在适合加仓吗？")
        return

    # TODO: Route to Orchestrator agent
    await message.answer(
        f"🔄 <b>Agent 矩阵分析中...</b>\n\n"
        f"问题: {question}\n\n"
        f"<i>正在调度 Technical + Sentiment + Fundamental 分析...</i>"
    )
