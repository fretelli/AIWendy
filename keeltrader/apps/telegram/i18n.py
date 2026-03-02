"""Lightweight i18n for Telegram Bot.

Translation dict inline — no dependency on frontend JSON files.
Default language: zh (current sole user is Chinese-speaking).
Users can switch via /lang command.
"""

from __future__ import annotations

import os

# Per-user language stored in memory (resets on restart).
# For persistence, could use Redis in the future.
_user_langs: dict[int, str] = {}

# Default language from env or fallback to "zh"
DEFAULT_LANG = os.environ.get("TELEGRAM_LANG", "zh")

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── keyboards.py ──
    "kb.status": {"zh": "📊 状态", "en": "📊 Status"},
    "kb.portfolio": {"zh": "💼 持仓", "en": "💼 Portfolio"},
    "kb.coach": {"zh": "🧠 教练", "en": "🧠 Coach"},
    "kb.ghost": {"zh": "👻 Ghost", "en": "👻 Ghost"},
    "kb.refresh": {"zh": "🔄 刷新", "en": "🔄 Refresh"},
    "kb.events": {"zh": "📈 事件流", "en": "📈 Events"},
    "kb.confirm_exec": {"zh": "✅ 确认执行", "en": "✅ Confirm"},
    "kb.reject": {"zh": "❌ 拒绝", "en": "❌ Reject"},
    "kb.confirm_close": {"zh": "✅ 确认平仓", "en": "✅ Close Position"},
    "kb.wait": {"zh": "⏸ 等等再看", "en": "⏸ Wait & See"},
    "kb.trailing_stop": {"zh": "🔄 移动止损", "en": "🔄 Trailing Stop"},
    "kb.pause_trading": {"zh": "✅ 暂停交易", "en": "✅ Pause Trading"},
    "kb.im_fine": {"zh": "❌ 我没事", "en": "❌ I'm Fine"},
    "kb.talk_coach": {"zh": "💬 和教练聊聊", "en": "💬 Talk to Coach"},
    "kb.exec_suggestion": {"zh": "✅ 执行建议", "en": "✅ Execute"},
    "kb.detailed_chart": {"zh": "📊 详细图表", "en": "📊 Details"},
    "kb.skip": {"zh": "❌ 暂不操作", "en": "❌ Skip"},
    "kb.close_position": {"zh": "🔴 平仓", "en": "🔴 Close"},
    "kb.details": {"zh": "📊 详情", "en": "📊 Details"},

    # ── commands.py ──
    "cmd.welcome": {
        "zh": (
            "<b>KeelTrader Agent Matrix</b>\n\n"
            "欢迎使用 KeelTrader 交易助手。\n\n"
            "可用命令：\n"
            "/status — 查看 Agent 矩阵状态\n"
            "/portfolio — 持仓概览\n"
            "/ghost — Ghost Trading 状态\n"
            "/ask — 向 Agent 矩阵提问\n"
            "/kill — 紧急熔断\n"
            "/resume — 恢复交易\n"
            "/lang — 切换语言\n"
            "/help — 帮助"
        ),
        "en": (
            "<b>KeelTrader Agent Matrix</b>\n\n"
            "Welcome to KeelTrader Trading Assistant.\n\n"
            "Available commands:\n"
            "/status — Agent matrix status\n"
            "/portfolio — Portfolio overview\n"
            "/ghost — Ghost Trading status\n"
            "/ask — Ask the Agent matrix\n"
            "/kill — Emergency circuit breaker\n"
            "/resume — Resume trading\n"
            "/lang — Switch language\n"
            "/help — Help"
        ),
    },
    "cmd.status_title": {"zh": "<b>Agent 矩阵状态</b>", "en": "<b>Agent Matrix Status</b>"},
    "cmd.online": {"zh": "在线", "en": "Online"},
    "cmd.disabled": {"zh": "未启用", "en": "Disabled"},
    "cmd.events_count": {"zh": "📊 事件流: {count} 条", "en": "📊 Events: {count}"},
    "cmd.realtime_prices": {"zh": "💰 实时价格:", "en": "💰 Live Prices:"},
    "cmd.kill_activated": {
        "zh": (
            "🔴 <b>紧急熔断已激活</b>\n\n"
            "• Circuit Breaker: ON\n"
            "• 所有 Agent 执行已锁定\n"
            "• Ghost Trading 暂停\n\n"
            "使用 /resume 恢复交易"
        ),
        "en": (
            "🔴 <b>Emergency Circuit Breaker Activated</b>\n\n"
            "• Circuit Breaker: ON\n"
            "• All Agent executions locked\n"
            "• Ghost Trading paused\n\n"
            "Use /resume to resume trading"
        ),
    },
    "cmd.trading_resumed": {
        "zh": (
            "🟢 <b>交易已恢复</b>\n\n"
            "• Circuit Breaker: OFF\n"
            "• Agent 矩阵恢复运行"
        ),
        "en": (
            "🟢 <b>Trading Resumed</b>\n\n"
            "• Circuit Breaker: OFF\n"
            "• Agent matrix back online"
        ),
    },
    "cmd.portfolio_title": {"zh": "<b>持仓概览</b>", "en": "<b>Portfolio Overview</b>"},
    "cmd.no_positions": {"zh": "暂无活跃持仓。", "en": "No active positions."},
    "cmd.portfolio_ghost_hint": {
        "zh": "👻 使用 Ghost Trading 模拟交易\n📊 使用 /ask 分析市场",
        "en": "👻 Try Ghost Trading for paper trades\n📊 Use /ask to analyze markets",
    },
    "cmd.portfolio_exchange_hint": {
        "zh": "连接交易所后可查看实时持仓。",
        "en": "Connect an exchange to view live positions.",
    },
    "cmd.ghost_no_data": {
        "zh": "👻 <b>Ghost Trading</b>\n\n暂无数据\n\n<i>使用 Executor Agent 开始 Ghost Trading</i>",
        "en": "👻 <b>Ghost Trading</b>\n\nNo data\n\n<i>Start Ghost Trading via Executor Agent</i>",
    },
    "cmd.help": {
        "zh": (
            "<b>KeelTrader 命令帮助</b>\n\n"
            "/start — 开始\n"
            "/status — Agent 矩阵状态\n"
            "/portfolio — 持仓概览\n"
            "/ghost — Ghost Trading 状态\n"
            "/ask <i>问题</i> — 向 Agent 矩阵提问\n"
            "/kill — 紧急熔断（停止所有交易）\n"
            "/resume — 恢复交易\n"
            "/lang — 切换语言 (中/英)\n"
            "/help — 显示此帮助\n\n"
            "💡 也可以直接发送消息，Orchestrator 会自动路由到合适的 Agent。"
        ),
        "en": (
            "<b>KeelTrader Command Help</b>\n\n"
            "/start — Start\n"
            "/status — Agent matrix status\n"
            "/portfolio — Portfolio overview\n"
            "/ghost — Ghost Trading status\n"
            "/ask <i>question</i> — Ask the Agent matrix\n"
            "/kill — Emergency circuit breaker (halt all trading)\n"
            "/resume — Resume trading\n"
            "/lang — Switch language (zh/en)\n"
            "/help — Show this help\n\n"
            "💡 You can also send messages directly — Orchestrator routes them to the right Agent."
        ),
    },
    "cmd.ask_empty": {
        "zh": "请在 /ask 后输入你的问题。\n例如: /ask ETH 现在适合加仓吗？",
        "en": "Please type your question after /ask.\nExample: /ask Is it a good time to add ETH?",
    },
    "cmd.ask_processing": {
        "zh": "🔄 <b>Agent 矩阵分析中...</b>\n\n问题: {question}\n\n<i>正在调度分析，请稍候...</i>",
        "en": "🔄 <b>Agent Matrix Analyzing...</b>\n\nQuestion: {question}\n\n<i>Dispatching analysis, please wait...</i>",
    },
    "cmd.lang_switched": {
        "zh": "🌐 语言已切换为 <b>中文</b>",
        "en": "🌐 Language switched to <b>English</b>",
    },
    "cmd.lang_usage": {
        "zh": "用法: /lang zh 或 /lang en\n当前语言: <b>中文</b>",
        "en": "Usage: /lang zh or /lang en\nCurrent language: <b>English</b>",
    },

    # ── callbacks.py ──
    "cb.order_confirmed": {"zh": "✅ 订单已确认", "en": "✅ Order confirmed"},
    "cb.order_confirmed_text": {"zh": "\n\n✅ <b>已确认</b> — 正在执行...", "en": "\n\n✅ <b>Confirmed</b> — Executing..."},
    "cb.order_rejected": {"zh": "❌ 订单已拒绝", "en": "❌ Order rejected"},
    "cb.order_rejected_text": {"zh": "\n\n❌ <b>已拒绝</b>", "en": "\n\n❌ <b>Rejected</b>"},
    "cb.trading_paused": {
        "zh": "⏸ 交易已暂停 30 分钟",
        "en": "⏸ Trading paused for 30 minutes",
    },
    "cb.trading_paused_text": {
        "zh": "\n\n⏸ <b>交易已暂停 30 分钟</b>",
        "en": "\n\n⏸ <b>Trading paused for 30 minutes</b>",
    },
    "cb.coach_intro": {
        "zh": "🧠 <b>Psychology Coach</b>\n\n我是你的交易心理教练。说说你现在的感受？\n\n<i>直接发送消息即可开始对话。</i>",
        "en": "🧠 <b>Psychology Coach</b>\n\nI'm your trading psychology coach. How are you feeling?\n\n<i>Just send a message to start chatting.</i>",
    },
    "cb.coach_event_text": {
        "zh": "我需要和教练聊聊交易心理",
        "en": "I need to talk to the coach about trading psychology",
    },
    "cb.view_details": {
        "zh": "📊 <b>详细分析</b>\n\n<i>使用 /ask 命令查看详细分析。</i>\n例如: /ask BTC 多时间框架分析",
        "en": "📊 <b>Detailed Analysis</b>\n\n<i>Use /ask for detailed analysis.</i>\nExample: /ask BTC multi-timeframe analysis",
    },
    "cb.ghost_no_data": {
        "zh": "👻 <b>Ghost Trading</b>\n\n暂无数据",
        "en": "👻 <b>Ghost Trading</b>\n\nNo data",
    },
    "cb.action_exec": {"zh": "执行: {action}", "en": "Executing: {action}"},

    # ── messages.py ──
    "msg.processing": {
        "zh": "🔄 <b>处理中...</b>\n\n正在将你的消息路由到 Orchestrator Agent...\n\n<i>Agent Matrix 功能开发中。</i>",
        "en": "🔄 <b>Processing...</b>\n\nRouting your message to Orchestrator Agent...\n\n<i>Agent Matrix under development.</i>",
    },

    # ── renderer.py ──
    "render.trade_confirm": {"zh": "交易确认", "en": "Trade Confirmation"},
    "render.side_long": {"zh": "做多", "en": "Long"},
    "render.side_short": {"zh": "做空", "en": "Short"},
    "render.direction": {"zh": "方向", "en": "Direction"},
    "render.type": {"zh": "类型", "en": "Type"},
    "render.amount": {"zh": "数量", "en": "Amount"},
    "render.price": {"zh": "价格", "en": "Price"},
    "render.stop_loss": {"zh": "止损", "en": "Stop Loss"},
    "render.safety_checks": {"zh": "🛡 安全检查:", "en": "🛡 Safety Checks:"},
    "render.ghost_opened": {"zh": "👻 <b>Ghost Trade 已开仓</b>", "en": "👻 <b>Ghost Trade Opened</b>"},
    "render.entry_price": {"zh": "入场价", "en": "Entry Price"},
    "render.take_profit": {"zh": "止盈", "en": "Take Profit"},
    "render.ghost_closed": {"zh": "👻 <b>Ghost Trade 已平仓</b>", "en": "👻 <b>Ghost Trade Closed</b>"},
    "render.entry": {"zh": "入场", "en": "Entry"},
    "render.exit": {"zh": "出场", "en": "Exit"},
    "render.ghost_overview": {"zh": "👻 <b>Ghost Trading 概览</b>", "en": "👻 <b>Ghost Trading Overview</b>"},
    "render.open_positions": {"zh": "活跃持仓", "en": "Open Positions"},
    "render.closed_trades": {"zh": "已平仓", "en": "Closed Trades"},
    "render.unrealized_pnl": {"zh": "未实现 P&L", "en": "Unrealized P&L"},
    "render.realized_pnl": {"zh": "已实现 P&L", "en": "Realized P&L"},
    "render.total_pnl": {"zh": "总 P&L", "en": "Total P&L"},
    "render.win_rate": {"zh": "胜率", "en": "Win Rate"},
    "render.active_positions": {"zh": "📊 活跃持仓:", "en": "📊 Open Positions:"},
    "render.analysis_title": {"zh": "📊 <b>分析报告 | {symbol}</b>", "en": "📊 <b>Analysis Report | {symbol}</b>"},
    "render.trend": {"zh": "趋势", "en": "Trend"},
    "render.volume": {"zh": "成交量", "en": "Volume"},
    "render.vol_high": {"zh": "高", "en": "High"},
    "render.vol_low": {"zh": "低", "en": "Low"},
    "render.vol_normal": {"zh": "正常", "en": "Normal"},
    "render.loss_streak_title": {"zh": "⚠️ <b>连亏告警</b>", "en": "⚠️ <b>Loss Streak Alert</b>"},
    "render.loss_streak_body": {
        "zh": "最近 {count} 笔交易连续亏损\n累计亏损: <b>${total_loss}</b>\n\nPsychology Coach 建议暂停交易",
        "en": "Last {count} trades in a row lost\nTotal loss: <b>${total_loss}</b>\n\nPsychology Coach suggests pausing trading",
    },
    "render.position_risk_title": {"zh": "🔴 <b>高风险持仓告警</b>", "en": "🔴 <b>High Risk Position Alert</b>"},
    "render.position_risk_body": {
        "zh": "Symbol: {symbol}\n浮亏: <b>{pnl_pct}%</b>\n\nGuardian 建议考虑止损",
        "en": "Symbol: {symbol}\nUnrealized Loss: <b>{pnl_pct}%</b>\n\nGuardian suggests considering a stop loss",
    },
    "render.daily_limit_title": {"zh": "🚨 <b>日亏损限额已触发</b>", "en": "🚨 <b>Daily Loss Limit Triggered</b>"},
    "render.daily_limit_body": {
        "zh": "今日 P&L: <b>${daily_pnl}</b>\n限额: ${limit}\n\n所有 Agent 交易已自动锁定",
        "en": "Today's P&L: <b>${daily_pnl}</b>\nLimit: ${limit}\n\nAll Agent trading auto-locked",
    },
    "render.generic_alert": {"zh": "⚠️ <b>风控告警: {alert_type}</b>", "en": "⚠️ <b>Risk Alert: {alert_type}</b>"},
    "render.cb_active_title": {"zh": "🔴 <b>熔断器状态: 已激活</b>", "en": "🔴 <b>Circuit Breaker: ACTIVE</b>"},
    "render.cb_reason": {"zh": "原因", "en": "Reason"},
    "render.cb_by": {"zh": "操作人", "en": "Activated by"},
    "render.cb_paused": {"zh": "所有交易执行已暂停\n使用 /resume 恢复交易", "en": "All trading halted\nUse /resume to resume trading"},
    "render.cb_normal": {"zh": "🟢 <b>熔断器状态: 正常</b>\n\n所有 Agent 正常运行", "en": "🟢 <b>Circuit Breaker: NORMAL</b>\n\nAll Agents running normally"},
}


def get_lang(user_id: int | None = None) -> str:
    """Get language for a user. Falls back to DEFAULT_LANG."""
    if user_id is not None and user_id in _user_langs:
        return _user_langs[user_id]
    return DEFAULT_LANG


def set_lang(user_id: int, lang: str) -> None:
    """Set language for a user."""
    if lang in ("zh", "en"):
        _user_langs[user_id] = lang


def t(key: str, user_id: int | None = None, **kwargs: object) -> str:
    """Get translated string for key. Supports {param} interpolation."""
    lang = get_lang(user_id)
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get("zh", key)
    if kwargs:
        text = text.format(**kwargs)
    return text
