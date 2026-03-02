"""Telegram keyboard builders — dynamic inline keyboards for all flows."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu inline keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 状态", callback_data="agent:status"),
            InlineKeyboardButton(text="💼 持仓", callback_data="agent:portfolio"),
        ],
        [
            InlineKeyboardButton(text="🧠 教练", callback_data="talk_to_coach"),
            InlineKeyboardButton(text="👻 Ghost", callback_data="agent:ghost"),
        ],
    ])


def agent_status_keyboard() -> InlineKeyboardMarkup:
    """Agent status page keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 刷新", callback_data="agent:refresh_status"),
            InlineKeyboardButton(text="📈 事件流", callback_data="agent:events"),
        ],
    ])


def order_confirmation_keyboard(confirmation_id: str) -> InlineKeyboardMarkup:
    """Order confirmation keyboard with confirmation ID in callback data."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ 确认执行",
                callback_data=f"confirm_order:{confirmation_id}",
            ),
            InlineKeyboardButton(
                text="❌ 拒绝",
                callback_data=f"reject_order:{confirmation_id}",
            ),
        ],
    ])


def stop_loss_confirmation_keyboard(confirmation_id: str) -> InlineKeyboardMarkup:
    """Stop-loss confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ 确认平仓",
                callback_data=f"confirm_order:{confirmation_id}",
            ),
            InlineKeyboardButton(
                text="⏸ 等等再看",
                callback_data=f"reject_order:{confirmation_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 移动止损",
                callback_data="agent:adjust_sl",
            ),
        ],
    ])


def guardian_alert_keyboard() -> InlineKeyboardMarkup:
    """Guardian risk alert keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ 暂停交易", callback_data="pause_trading"),
            InlineKeyboardButton(text="❌ 我没事", callback_data="agent:dismiss"),
        ],
        [
            InlineKeyboardButton(text="💬 和教练聊聊", callback_data="talk_to_coach"),
        ],
    ])


def analysis_result_keyboard(confirmation_id: str = "") -> InlineKeyboardMarkup:
    """Analysis result keyboard — optionally with execute button."""
    buttons = []

    if confirmation_id:
        buttons.append([
            InlineKeyboardButton(
                text="✅ 执行建议",
                callback_data=f"confirm_order:{confirmation_id}",
            ),
            InlineKeyboardButton(
                text="📊 详细图表",
                callback_data="view_details",
            ),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="📊 详细图表", callback_data="view_details"),
        ])

    buttons.append([
        InlineKeyboardButton(text="❌ 暂不操作", callback_data="agent:dismiss"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ghost_trade_keyboard(trade_id: str) -> InlineKeyboardMarkup:
    """Ghost trade management keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔴 平仓",
                callback_data=f"agent:close_ghost:{trade_id}",
            ),
            InlineKeyboardButton(
                text="📊 详情",
                callback_data=f"agent:ghost_detail:{trade_id}",
            ),
        ],
    ])
