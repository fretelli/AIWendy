"""KeelTrader Telegram Bot — aiogram v3 with webhook mode."""

from __future__ import annotations

import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from .handlers import callbacks, commands, messages
from .middleware import AuthMiddleware, LoggingMiddleware

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    """Create and configure the Telegram bot."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Create and configure the aiogram dispatcher."""
    dp = Dispatcher()

    # Register middleware
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Register handlers (order matters — more specific first)
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(messages.router)

    return dp


async def on_startup(bot: Bot) -> None:
    """Set webhook on startup."""
    webhook_url = os.environ.get("TELEGRAM_WEBHOOK_URL", "")
    if webhook_url:
        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
        )
        logger.info("Webhook set: %s", webhook_url)
    else:
        logger.warning("No TELEGRAM_WEBHOOK_URL set, webhook not configured")


async def on_shutdown(bot: Bot) -> None:
    """Clean up on shutdown."""
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("Bot shutdown complete")


def create_app() -> web.Application:
    """Create the aiohttp web application for webhook handling."""
    bot = create_bot()
    dp = create_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    # Health check endpoint
    async def health(request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "keeltrader-telegram"})

    app.router.add_get("/health", health)

    # Webhook handler
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    # Setup aiogram application lifecycle
    setup_application(app, dp, bot=bot)

    return app


def main():
    """Entry point for the Telegram bot."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    app = create_app()
    port = int(os.environ.get("BOT_PORT", "8080"))
    logger.info("Starting Telegram bot on port %d (webhook mode)", port)
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
