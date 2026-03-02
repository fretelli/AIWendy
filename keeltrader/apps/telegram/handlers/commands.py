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

from ..i18n import get_lang, set_lang, t
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
    uid = message.from_user.id
    await message.answer(
        t("cmd.welcome", uid),
        reply_markup=main_menu_keyboard(uid),
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Handle /status — show live agent matrix status."""
    uid = message.from_user.id
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

        online = t("cmd.online", uid)
        disabled = t("cmd.disabled", uid)

        status_text = (
            f"{t('cmd.status_title', uid)}\n\n"
            f"🟢 Orchestrator — {online}\n"
            f"🟢 Technical Analyst — {online}\n"
            f"⚪ Sentiment Analyst — {disabled}\n"
            f"⚪ Fundamental Analyst — {disabled}\n"
            f"⚪ Psychology Coach — {disabled}\n"
            f"🟢 Guardian — {online}\n"
            f"🟢 Executor — {online}\n\n"
            f"⚡ Circuit Breaker: {cb_status}\n"
            f"{t('cmd.events_count', uid, count=event_count)}\n"
        )

        if price_lines:
            status_text += f"\n{t('cmd.realtime_prices', uid)}\n" + "\n".join(price_lines)

    finally:
        await r.aclose()

    await message.answer(status_text, reply_markup=agent_status_keyboard(uid))


@router.message(Command("kill"))
async def cmd_kill(message: Message) -> None:
    """Handle /kill — emergency circuit breaker activation."""
    uid = message.from_user.id
    user_id = str(uid)

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

    await message.answer(t("cmd.kill_activated", uid))
    logger.warning("KILL switch activated by Telegram user %s", user_id)


@router.message(Command("resume"))
async def cmd_resume(message: Message) -> None:
    """Handle /resume — deactivate circuit breaker."""
    uid = message.from_user.id
    user_id = str(uid)

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

    await message.answer(t("cmd.trading_resumed", uid))
    logger.info("Trading resumed by Telegram user %s", user_id)


@router.message(Command("portfolio"))
async def cmd_portfolio(message: Message) -> None:
    """Handle /portfolio — show current positions."""
    uid = message.from_user.id
    r = await _get_redis()
    try:
        # Show ghost trading portfolio
        from ...execution.ghost import GhostTradingService
        ghost = GhostTradingService(r)
        summary = await ghost.portfolio_summary(str(uid))

        if summary.get("open_positions", 0) > 0 or summary.get("closed_trades", 0) > 0:
            text = render_ghost_portfolio(summary, uid)
        else:
            text = (
                f"{t('cmd.portfolio_title', uid)}\n\n"
                f"{t('cmd.no_positions', uid)}\n\n"
                f"{t('cmd.portfolio_ghost_hint', uid)}"
            )
    except Exception:
        text = (
            f"{t('cmd.portfolio_title', uid)}\n\n"
            f"{t('cmd.no_positions', uid)}\n\n"
            f"{t('cmd.portfolio_exchange_hint', uid)}"
        )
    finally:
        await r.aclose()

    await message.answer(text)


@router.message(Command("ghost"))
async def cmd_ghost(message: Message) -> None:
    """Handle /ghost — show ghost trading status."""
    uid = message.from_user.id
    r = await _get_redis()
    try:
        from ...execution.ghost import GhostTradingService
        ghost = GhostTradingService(r)
        summary = await ghost.portfolio_summary(str(uid))
        text = render_ghost_portfolio(summary, uid)
    except Exception:
        text = t("cmd.ghost_no_data", uid)
    finally:
        await r.aclose()

    await message.answer(text)


@router.message(Command("lang"))
async def cmd_lang(message: Message) -> None:
    """Handle /lang — switch language."""
    uid = message.from_user.id
    arg = message.text.replace("/lang", "", 1).strip().lower()

    if arg in ("zh", "en"):
        set_lang(uid, arg)
        await message.answer(t("cmd.lang_switched", uid))
    else:
        await message.answer(t("cmd.lang_usage", uid))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help."""
    uid = message.from_user.id
    await message.answer(t("cmd.help", uid))


@router.message(Command("ask"))
async def cmd_ask(message: Message) -> None:
    """Handle /ask — route question to Orchestrator agent via event bus."""
    uid = message.from_user.id
    question = message.text.replace("/ask", "", 1).strip()
    if not question:
        await message.answer(t("cmd.ask_empty", uid))
        return

    user_id = str(uid)

    await _emit_event("user.message", user_id, {
        "text": question,
        "telegram_user_id": uid,
        "telegram_message_id": message.message_id,
    })

    await message.answer(t("cmd.ask_processing", uid, question=question))
