"""Telegram keyboard builders — dynamic inline keyboards for all flows."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .i18n import t


def main_menu_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    """Main menu inline keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("kb.status", user_id), callback_data="agent:status"),
            InlineKeyboardButton(text=t("kb.portfolio", user_id), callback_data="agent:portfolio"),
        ],
        [
            InlineKeyboardButton(text=t("kb.coach", user_id), callback_data="talk_to_coach"),
            InlineKeyboardButton(text=t("kb.ghost", user_id), callback_data="agent:ghost"),
        ],
    ])


def agent_status_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    """Agent status page keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("kb.refresh", user_id), callback_data="agent:refresh_status"),
            InlineKeyboardButton(text=t("kb.events", user_id), callback_data="agent:events"),
        ],
    ])


def order_confirmation_keyboard(confirmation_id: str, user_id: int | None = None) -> InlineKeyboardMarkup:
    """Order confirmation keyboard with confirmation ID in callback data."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("kb.confirm_exec", user_id),
                callback_data=f"confirm_order:{confirmation_id}",
            ),
            InlineKeyboardButton(
                text=t("kb.reject", user_id),
                callback_data=f"reject_order:{confirmation_id}",
            ),
        ],
    ])


def stop_loss_confirmation_keyboard(confirmation_id: str, user_id: int | None = None) -> InlineKeyboardMarkup:
    """Stop-loss confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("kb.confirm_close", user_id),
                callback_data=f"confirm_order:{confirmation_id}",
            ),
            InlineKeyboardButton(
                text=t("kb.wait", user_id),
                callback_data=f"reject_order:{confirmation_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=t("kb.trailing_stop", user_id),
                callback_data="agent:adjust_sl",
            ),
        ],
    ])


def guardian_alert_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    """Guardian risk alert keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("kb.pause_trading", user_id), callback_data="pause_trading"),
            InlineKeyboardButton(text=t("kb.im_fine", user_id), callback_data="agent:dismiss"),
        ],
        [
            InlineKeyboardButton(text=t("kb.talk_coach", user_id), callback_data="talk_to_coach"),
        ],
    ])


def analysis_result_keyboard(confirmation_id: str = "", user_id: int | None = None) -> InlineKeyboardMarkup:
    """Analysis result keyboard — optionally with execute button."""
    buttons = []

    if confirmation_id:
        buttons.append([
            InlineKeyboardButton(
                text=t("kb.exec_suggestion", user_id),
                callback_data=f"confirm_order:{confirmation_id}",
            ),
            InlineKeyboardButton(
                text=t("kb.detailed_chart", user_id),
                callback_data="view_details",
            ),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text=t("kb.detailed_chart", user_id), callback_data="view_details"),
        ])

    buttons.append([
        InlineKeyboardButton(text=t("kb.skip", user_id), callback_data="agent:dismiss"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ghost_trade_keyboard(trade_id: str, user_id: int | None = None) -> InlineKeyboardMarkup:
    """Ghost trade management keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("kb.close_position", user_id),
                callback_data=f"agent:close_ghost:{trade_id}",
            ),
            InlineKeyboardButton(
                text=t("kb.details", user_id),
                callback_data=f"agent:ghost_detail:{trade_id}",
            ),
        ],
    ])
