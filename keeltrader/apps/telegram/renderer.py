"""Telegram message renderer — formats agent output for rich Telegram messages."""

from __future__ import annotations

from typing import Any

from .i18n import t


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
    user_id: int | None = None,
) -> str:
    """Render a trade order confirmation message."""
    emoji = "🟢" if side == "buy" else "🔴"
    side_label = t("render.side_long", user_id) if side == "buy" else t("render.side_short", user_id)

    lines = [
        f"{emoji} <b>{t('render.trade_confirm', user_id)} | {symbol}</b>",
        "",
        f"{t('render.direction', user_id)}: <b>{side_label}</b> ({side.upper()})",
        f"{t('render.type', user_id)}: {order_type}",
        f"{t('render.amount', user_id)}: {amount}",
    ]

    if price:
        lines.append(f"{t('render.price', user_id)}: ${price:,.2f}")

    if stop_loss:
        lines.append(f"{t('render.stop_loss', user_id)}: ${stop_loss:,.2f}")

    if reasoning:
        lines.extend(["", f"💡 <i>{reasoning}</i>"])

    if safety_checks:
        lines.extend(["", t("render.safety_checks", user_id)])
        for check in safety_checks:
            icon = "✅" if check.get("passed") else "❌"
            lines.append(f"  {icon} {check.get('name', '?')}: {check.get('detail', '')}")

    lines.extend(["", f"<code>ID: {order_id[:8]}</code>"])

    return "\n".join(lines)


def render_ghost_trade_opened(trade: dict[str, Any], user_id: int | None = None) -> str:
    """Render a ghost trade opened notification."""
    side = trade.get("side", "buy")
    emoji = "🟢" if side == "buy" else "🔴"
    side_label = t("render.side_long", user_id) if side == "buy" else t("render.side_short", user_id)

    return (
        f"{t('render.ghost_opened', user_id)}\n\n"
        f"{emoji} {trade.get('symbol', '?')} {side_label}\n"
        f"{t('render.amount', user_id)}: {trade.get('amount', 0)}\n"
        f"{t('render.entry_price', user_id)}: ${float(trade.get('entry_price', 0)):,.2f}\n"
        f"{t('render.stop_loss', user_id)}: ${float(trade.get('stop_loss', 0)):,.2f}\n"
        f"{t('render.take_profit', user_id)}: ${float(trade.get('take_profit', 0)):,.2f}\n\n"
        f"💡 <i>{trade.get('reasoning', '')}</i>\n\n"
        f"<code>ID: {trade.get('id', '?')[:8]}</code>"
    )


def render_ghost_trade_closed(result: dict[str, Any], user_id: int | None = None) -> str:
    """Render a ghost trade closed notification."""
    pnl = result.get("pnl", 0)
    pnl_pct = result.get("pnl_pct", 0)
    emoji = "✅" if pnl >= 0 else "❌"
    pnl_icon = "📈" if pnl >= 0 else "📉"

    return (
        f"{t('render.ghost_closed', user_id)} {emoji}\n\n"
        f"{result.get('symbol', '?')} {result.get('side', '?')}\n"
        f"{t('render.entry', user_id)}: ${result.get('entry_price', 0):,.2f}\n"
        f"{t('render.exit', user_id)}: ${result.get('exit_price', 0):,.2f}\n"
        f"{t('render.amount', user_id)}: {result.get('amount', 0)}\n\n"
        f"{pnl_icon} P&L: <b>${pnl:+,.4f}</b> ({pnl_pct:+.2f}%)"
    )


def render_ghost_portfolio(summary: dict[str, Any], user_id: int | None = None) -> str:
    """Render ghost trading portfolio summary."""
    lines = [
        t("render.ghost_overview", user_id),
        "",
        f"{t('render.open_positions', user_id)}: {summary.get('open_positions', 0)}",
        f"{t('render.closed_trades', user_id)}: {summary.get('closed_trades', 0)}",
        "",
        f"{t('render.unrealized_pnl', user_id)}: <b>${summary.get('total_unrealized_pnl', 0):+,.4f}</b>",
        f"{t('render.realized_pnl', user_id)}: <b>${summary.get('total_realized_pnl', 0):+,.4f}</b>",
        f"{t('render.total_pnl', user_id)}: <b>${summary.get('total_pnl', 0):+,.4f}</b>",
        "",
        f"{t('render.win_rate', user_id)}: {summary.get('win_rate', 0):.1f}% "
        f"({summary.get('win_count', 0)}W / {summary.get('loss_count', 0)}L)",
    ]

    open_trades = summary.get("open_trades", [])
    if open_trades:
        lines.extend(["", t("render.active_positions", user_id)])
        for tr in open_trades:
            emoji = "🟢" if tr["side"] == "buy" else "🔴"
            pnl = tr.get("unrealized_pnl", 0)
            pnl_icon = "↑" if pnl >= 0 else "↓"
            lines.append(
                f"  {emoji} {tr['symbol']} {tr['amount']}@{tr['entry_price']:,.2f} "
                f"{pnl_icon}${pnl:+,.2f}"
            )

    return "\n".join(lines)


def render_analysis_result(
    symbol: str,
    analysis: dict[str, Any],
    user_id: int | None = None,
) -> str:
    """Render a technical/multi-agent analysis result."""
    lines = [t("render.analysis_title", user_id, symbol=symbol), ""]

    # Trend
    trend = analysis.get("trend", {})
    if trend:
        overall = trend.get("overall", "unknown")
        trend_emoji = "🟢" if overall == "bullish" else "🔴" if overall == "bearish" else "🟡"
        lines.append(
            f"{t('render.trend', user_id)}: {trend_emoji} <b>{overall.upper()}</b> "
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
        if rv > 1.5:
            vol_label = t("render.vol_high", user_id)
        elif rv < 0.5:
            vol_label = t("render.vol_low", user_id)
        else:
            vol_label = t("render.vol_normal", user_id)
        lines.append(f"{t('render.volume', user_id)}: {vol_label} ({rv:.1f}x)")

    # Signal summary
    summary = analysis.get("signal_summary", "")
    if summary:
        lines.extend(["", f"<i>{summary}</i>"])

    return "\n".join(lines)


def render_guardian_alert(
    alert_type: str,
    details: dict[str, Any],
    user_id: int | None = None,
) -> str:
    """Render a Guardian risk alert."""
    if alert_type == "loss_streak":
        count = details.get("count", 0)
        total_loss = details.get("total_loss", 0)
        return (
            f"{t('render.loss_streak_title', user_id)}\n\n"
            f"{t('render.loss_streak_body', user_id, count=count, total_loss=f'{abs(total_loss):,.2f}')}"
        )

    elif alert_type == "position_risk_high":
        symbol = details.get("symbol", "?")
        pnl_pct = details.get("pnl_pct", 0)
        return (
            f"{t('render.position_risk_title', user_id)}\n\n"
            f"{t('render.position_risk_body', user_id, symbol=symbol, pnl_pct=f'{pnl_pct:.1f}')}"
        )

    elif alert_type == "daily_loss_limit":
        daily_pnl = details.get("daily_pnl", 0)
        limit = details.get("limit", 0)
        return (
            f"{t('render.daily_limit_title', user_id)}\n\n"
            f"{t('render.daily_limit_body', user_id, daily_pnl=f'{daily_pnl:,.2f}', limit=f'{limit:,.2f}')}"
        )

    return f"{t('render.generic_alert', user_id, alert_type=alert_type)}\n\n{details}"


def render_circuit_breaker_status(active: bool, reason: str = "", by: str = "", user_id: int | None = None) -> str:
    """Render circuit breaker status."""
    if active:
        return (
            f"{t('render.cb_active_title', user_id)}\n\n"
            f"{t('render.cb_reason', user_id)}: {reason}\n"
            f"{t('render.cb_by', user_id)}: {by}\n\n"
            f"{t('render.cb_paused', user_id)}"
        )
    return t("render.cb_normal", user_id)
