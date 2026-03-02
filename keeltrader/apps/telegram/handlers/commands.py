"""Telegram command handlers — with Redis/event bus integration."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from uuid import uuid4

import redis.asyncio as aioredis
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from ..keyboards import agent_status_keyboard, main_menu_keyboard
from ..renderer import render_circuit_breaker_status, render_ghost_portfolio

logger = logging.getLogger(__name__)
router = Router(name="commands")


async def _get_redis() -> aioredis.Redis:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    return aioredis.from_url(url)


async def _emit_event(event_type: str, user_id: str, payload: dict) -> None:
    r = await _get_redis()
    try:
        await r.xadd("keeltrader:events", {
            "id": str(uuid4()),
            "type": event_type,
            "source": "telegram",
            "user_id": user_id,
            "agent_id": "",
            "payload": json.dumps(payload),
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": str(uuid4()),
            "causation_id": "",
        }, maxlen=10000)
    finally:
        await r.aclose()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start — welcome and account binding."""
    await message.answer(
        "<b>KeelTrader Agent Matrix</b>\n\n"
        "欢迎使用 KeelTrader 交易助手。\n\n"
        "可用命令：\n"
        "/status — 查看 Agent 矩阵状态\n"
        "/portfolio — 持仓概览\n"
        "/ghost — Ghost Trading 状态\n"
        "/ask — 向 Agent 矩阵提问\n"
        "/kill — 紧急熔断\n"
        "/resume — 恢复交易\n"
        "/help — 帮助",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Handle /status — show live agent matrix status."""
    r = await _get_redis()
    try:
        # Check circuit breaker
        cb_active = await r.get("keeltrader:circuit_breaker")
        cb_status = "ON 🔴" if cb_active == b"1" else "OFF 🟢"

        # Check event stream
        try:
            info = await r.xinfo_stream("keeltrader:events")
            event_count = info.get("length", 0)
        except Exception:
            event_count = 0

        # Check prices
        prices = await r.hgetall("keeltrader:prices")
        price_lines = []
        for sym, p in prices.items():
            sym_str = sym.decode() if isinstance(sym, bytes) else sym
            p_str = p.decode() if isinstance(p, bytes) else p
            price_lines.append(f"  {sym_str}: ${float(p_str):,.2f}")

        status_text = (
            "<b>Agent 矩阵状态</b>\n\n"
            "🟢 Orchestrator — 在线\n"
            "🟢 Technical Analyst — 在线\n"
            "⚪ Sentiment Analyst — 未启用\n"
            "⚪ Fundamental Analyst — 未启用\n"
            "⚪ Psychology Coach — 未启用\n"
            "🟢 Guardian — 在线\n"
            "🟢 Executor — 在线\n\n"
            f"⚡ Circuit Breaker: {cb_status}\n"
            f"📊 事件流: {event_count} 条\n"
        )

        if price_lines:
            status_text += "\n💰 实时价格:\n" + "\n".join(price_lines)

    finally:
        await r.aclose()

    await message.answer(status_text, reply_markup=agent_status_keyboard())


@router.message(Command("kill"))
async def cmd_kill(message: Message) -> None:
    """Handle /kill — emergency circuit breaker activation."""
    user_id = str(message.from_user.id)

    r = await _get_redis()
    try:
        from ...execution.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(r)
        await cb.activate(
            reason=f"Emergency kill by Telegram user {user_id}",
            activated_by=f"tg:{user_id}",
        )
    finally:
        await r.aclose()

    await _emit_event("circuit_breaker.on", user_id, {
        "reason": "Emergency kill switch",
        "activated_by": f"tg:{user_id}",
    })

    await message.answer(
        "🔴 <b>紧急熔断已激活</b>\n\n"
        "• Circuit Breaker: ON\n"
        "• 所有 Agent 执行已锁定\n"
        "• Ghost Trading 暂停\n\n"
        "使用 /resume 恢复交易",
    )
    logger.warning("KILL switch activated by Telegram user %s", user_id)


@router.message(Command("resume"))
async def cmd_resume(message: Message) -> None:
    """Handle /resume — deactivate circuit breaker."""
    user_id = str(message.from_user.id)

    r = await _get_redis()
    try:
        from ...execution.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(r)
        await cb.deactivate(deactivated_by=f"tg:{user_id}")
    finally:
        await r.aclose()

    await _emit_event("circuit_breaker.off", user_id, {
        "deactivated_by": f"tg:{user_id}",
    })

    await message.answer(
        "🟢 <b>交易已恢复</b>\n\n"
        "• Circuit Breaker: OFF\n"
        "• Agent 矩阵恢复运行",
    )
    logger.info("Trading resumed by Telegram user %s", user_id)


@router.message(Command("portfolio"))
async def cmd_portfolio(message: Message) -> None:
    """Handle /portfolio — show current positions."""
    r = await _get_redis()
    try:
        # Show ghost trading portfolio
        from ...execution.ghost import GhostTradingService
        ghost = GhostTradingService(r)
        summary = await ghost.portfolio_summary(str(message.from_user.id))

        if summary.get("open_positions", 0) > 0 or summary.get("closed_trades", 0) > 0:
            text = render_ghost_portfolio(summary)
        else:
            text = (
                "<b>持仓概览</b>\n\n"
                "暂无活跃持仓。\n\n"
                "👻 使用 Ghost Trading 模拟交易\n"
                "📊 使用 /ask 分析市场"
            )
    except Exception:
        text = (
            "<b>持仓概览</b>\n\n"
            "暂无活跃持仓。\n\n"
            "连接交易所后可查看实时持仓。"
        )
    finally:
        await r.aclose()

    await message.answer(text)


@router.message(Command("ghost"))
async def cmd_ghost(message: Message) -> None:
    """Handle /ghost — show ghost trading status."""
    r = await _get_redis()
    try:
        from ...execution.ghost import GhostTradingService
        ghost = GhostTradingService(r)
        summary = await ghost.portfolio_summary(str(message.from_user.id))
        text = render_ghost_portfolio(summary)
    except Exception as e:
        text = f"👻 <b>Ghost Trading</b>\n\n暂无数据\n\n<i>使用 Executor Agent 开始 Ghost Trading</i>"
    finally:
        await r.aclose()

    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help."""
    await message.answer(
        "<b>KeelTrader 命令帮助</b>\n\n"
        "/start — 开始\n"
        "/status — Agent 矩阵状态\n"
        "/portfolio — 持仓概览\n"
        "/ghost — Ghost Trading 状态\n"
        "/ask <i>问题</i> — 向 Agent 矩阵提问\n"
        "/kill — 紧急熔断（停止所有交易）\n"
        "/resume — 恢复交易\n"
        "/help — 显示此帮助\n\n"
        "💡 也可以直接发送消息，Orchestrator 会自动路由到合适的 Agent。",
    )


@router.message(Command("ask"))
async def cmd_ask(message: Message) -> None:
    """Handle /ask — route question to Orchestrator agent via event bus."""
    question = message.text.replace("/ask", "", 1).strip()
    if not question:
        await message.answer(
            "请在 /ask 后输入你的问题。\n"
            "例如: /ask ETH 现在适合加仓吗？"
        )
        return

    user_id = str(message.from_user.id)

    await _emit_event("user.message", user_id, {
        "text": question,
        "telegram_user_id": message.from_user.id,
        "telegram_message_id": message.message_id,
    })

    await message.answer(
        f"🔄 <b>Agent 矩阵分析中...</b>\n\n"
        f"问题: {question}\n\n"
        f"<i>正在调度分析，请稍候...</i>"
    )
