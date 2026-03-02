"""Telegram keyboard builders."""

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
            InlineKeyboardButton(text="🔄 刷新", callback_data="agent:status"),
            InlineKeyboardButton(text="📈 事件流", callback_data="agent:events"),
        ],
    ])


def order_confirmation_keyboard(order_id: str = "") -> InlineKeyboardMarkup:
    """Order confirmation keyboard (approve/reject)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ 确认执行", callback_data="confirm_order"),
            InlineKeyboardButton(text="❌ 拒绝", callback_data="reject_order"),
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


def analysis_result_keyboard() -> InlineKeyboardMarkup:
    """Analysis result keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ 执行建议", callback_data="confirm_order"),
            InlineKeyboardButton(text="📊 详细图表", callback_data="view_details"),
        ],
        [
            InlineKeyboardButton(text="❌ 暂不操作", callback_data="agent:dismiss"),
        ],
    ])
