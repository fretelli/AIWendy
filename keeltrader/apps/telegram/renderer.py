"""Telegram message renderer — formats agent output for rich Telegram messages."""

from __future__ import annotations

from typing import Any


def render_order_confirmation(
    order_id: str,
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: float | None,
    stop_loss: float | None,
    reasoning: str = "",
    safety_checks: list[dict] | None = None,
) -> str:
    """Render a trade order confirmation message."""
    emoji = "🟢" if side == "buy" else "🔴"
    side_cn = "做多" if side == "buy" else "做空"

    lines = [
        f"{emoji} <b>交易确认 | {symbol}</b>",
        "",
        f"方向: <b>{side_cn}</b> ({side.upper()})",
        f"类型: {order_type}",
        f"数量: {amount}",
    ]

    if price:
        lines.append(f"价格: ${price:,.2f}")

    if stop_loss:
        lines.append(f"止损: ${stop_loss:,.2f}")

    if reasoning:
        lines.extend(["", f"💡 <i>{reasoning}</i>"])

    if safety_checks:
        lines.extend(["", "🛡 安全检查:"])
        for check in safety_checks:
            icon = "✅" if check.get("passed") else "❌"
            lines.append(f"  {icon} {check.get('name', '?')}: {check.get('detail', '')}")

    lines.extend(["", f"<code>ID: {order_id[:8]}</code>"])

    return "\n".join(lines)


def render_ghost_trade_opened(trade: dict[str, Any]) -> str:
    """Render a ghost trade opened notification."""
    side = trade.get("side", "buy")
    emoji = "🟢" if side == "buy" else "🔴"
    side_cn = "做多" if side == "buy" else "做空"

    return (
        f"👻 <b>Ghost Trade 已开仓</b>\n\n"
        f"{emoji} {trade.get('symbol', '?')} {side_cn}\n"
        f"数量: {trade.get('amount', 0)}\n"
        f"入场价: ${float(trade.get('entry_price', 0)):,.2f}\n"
        f"止损: ${float(trade.get('stop_loss', 0)):,.2f}\n"
        f"止盈: ${float(trade.get('take_profit', 0)):,.2f}\n\n"
        f"💡 <i>{trade.get('reasoning', '')}</i>\n\n"
        f"<code>ID: {trade.get('id', '?')[:8]}</code>"
    )


def render_ghost_trade_closed(result: dict[str, Any]) -> str:
    """Render a ghost trade closed notification."""
    pnl = result.get("pnl", 0)
    pnl_pct = result.get("pnl_pct", 0)
    emoji = "✅" if pnl >= 0 else "❌"
    pnl_icon = "📈" if pnl >= 0 else "📉"

    return (
        f"👻 <b>Ghost Trade 已平仓</b> {emoji}\n\n"
        f"{result.get('symbol', '?')} {result.get('side', '?')}\n"
        f"入场: ${result.get('entry_price', 0):,.2f}\n"
        f"出场: ${result.get('exit_price', 0):,.2f}\n"
        f"数量: {result.get('amount', 0)}\n\n"
        f"{pnl_icon} P&L: <b>${pnl:+,.4f}</b> ({pnl_pct:+.2f}%)"
    )


def render_ghost_portfolio(summary: dict[str, Any]) -> str:
    """Render ghost trading portfolio summary."""
    lines = [
        "👻 <b>Ghost Trading 概览</b>",
        "",
        f"活跃持仓: {summary.get('open_positions', 0)}",
        f"已平仓: {summary.get('closed_trades', 0)}",
        "",
        f"未实现 P&L: <b>${summary.get('total_unrealized_pnl', 0):+,.4f}</b>",
        f"已实现 P&L: <b>${summary.get('total_realized_pnl', 0):+,.4f}</b>",
        f"总 P&L: <b>${summary.get('total_pnl', 0):+,.4f}</b>",
        "",
        f"胜率: {summary.get('win_rate', 0):.1f}% "
        f"({summary.get('win_count', 0)}W / {summary.get('loss_count', 0)}L)",
    ]

    open_trades = summary.get("open_trades", [])
    if open_trades:
        lines.extend(["", "📊 活跃持仓:"])
        for t in open_trades:
            emoji = "🟢" if t["side"] == "buy" else "🔴"
            pnl = t.get("unrealized_pnl", 0)
            pnl_icon = "↑" if pnl >= 0 else "↓"
            lines.append(
                f"  {emoji} {t['symbol']} {t['amount']}@{t['entry_price']:,.2f} "
                f"{pnl_icon}${pnl:+,.2f}"
            )

    return "\n".join(lines)


def render_analysis_result(
    symbol: str,
    analysis: dict[str, Any],
) -> str:
    """Render a technical/multi-agent analysis result."""
    lines = [f"📊 <b>分析报告 | {symbol}</b>", ""]

    # Trend
    trend = analysis.get("trend", {})
    if trend:
        overall = trend.get("overall", "unknown")
        trend_emoji = "🟢" if overall == "bullish" else "🔴" if overall == "bearish" else "🟡"
        lines.append(
            f"趋势: {trend_emoji} <b>{overall.upper()}</b> "
            f"({trend.get('bullish_signals', 0)}↑ / {trend.get('bearish_signals', 0)}↓)"
        )

    # Key indicators
    rsi = analysis.get("rsi", {})
    if rsi.get("value"):
        lines.append(f"RSI: {rsi['value']} ({rsi.get('signal', 'N/A')})")

    macd = analysis.get("macd", {})
    if macd.get("signal"):
        lines.append(f"MACD: {macd['signal']}")

    bb = analysis.get("bollinger_bands", {})
    if bb.get("pct_b") is not None:
        lines.append(f"BB %B: {bb['pct_b']} ({bb.get('signal', 'N/A')})")

    # Volume
    vol = analysis.get("volume_profile", {})
    if vol.get("relative_volume"):
        rv = vol["relative_volume"]
        vol_label = "高" if rv > 1.5 else "低" if rv < 0.5 else "正常"
        lines.append(f"成交量: {vol_label} ({rv:.1f}x)")

    # Signal summary
    summary = analysis.get("signal_summary", "")
    if summary:
        lines.extend(["", f"<i>{summary}</i>"])

    return "\n".join(lines)


def render_guardian_alert(
    alert_type: str,
    details: dict[str, Any],
) -> str:
    """Render a Guardian risk alert."""
    if alert_type == "loss_streak":
        count = details.get("count", 0)
        total_loss = details.get("total_loss", 0)
        return (
            f"⚠️ <b>连亏告警</b>\n\n"
            f"最近 {count} 笔交易连续亏损\n"
            f"累计亏损: <b>${abs(total_loss):,.2f}</b>\n\n"
            f"Psychology Coach 建议暂停交易"
        )

    elif alert_type == "position_risk_high":
        symbol = details.get("symbol", "?")
        pnl_pct = details.get("pnl_pct", 0)
        return (
            f"🔴 <b>高风险持仓告警</b>\n\n"
            f"Symbol: {symbol}\n"
            f"浮亏: <b>{pnl_pct:.1f}%</b>\n\n"
            f"Guardian 建议考虑止损"
        )

    elif alert_type == "daily_loss_limit":
        daily_pnl = details.get("daily_pnl", 0)
        limit = details.get("limit", 0)
        return (
            f"🚨 <b>日亏损限额已触发</b>\n\n"
            f"今日 P&L: <b>${daily_pnl:,.2f}</b>\n"
            f"限额: ${limit:,.2f}\n\n"
            f"所有 Agent 交易已自动锁定"
        )

    return f"⚠️ <b>风控告警: {alert_type}</b>\n\n{details}"


def render_circuit_breaker_status(active: bool, reason: str = "", by: str = "") -> str:
    """Render circuit breaker status."""
    if active:
        return (
            f"🔴 <b>熔断器状态: 已激活</b>\n\n"
            f"原因: {reason}\n"
            f"操作人: {by}\n\n"
            f"所有交易执行已暂停\n"
            f"使用 /resume 恢复交易"
        )
    return "🟢 <b>熔断器状态: 正常</b>\n\n所有 Agent 正常运行"
