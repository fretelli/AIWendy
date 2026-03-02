"""Analysis tools — pattern detection, multi-indicator scoring.

Wraps ML analytics and indicator calculations for agent consumption.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from .market import calc_indicators, get_klines

logger = logging.getLogger(__name__)


async def full_technical_analysis(
    symbol: str,
    interval: str = "1h",
    exchange: str = "okx",
) -> dict[str, Any]:
    """Run comprehensive technical analysis on a symbol.

    Fetches klines and calculates all indicators in one call.

    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        exchange: Exchange name

    Returns:
        Dict with all indicators, trend assessment, and signals
    """
    klines = await get_klines(symbol, interval=interval, limit=200, exchange=exchange)
    if not klines:
        return {"symbol": symbol, "error": "No kline data available"}

    indicators = calc_indicators(
        klines,
        indicators=["rsi", "macd", "bb", "ema", "sma", "atr", "volume_profile"],
    )

    # Add trend assessment
    trend = _assess_trend(indicators)
    indicators["trend"] = trend

    # Add signal summary
    indicators["signal_summary"] = _summarize_signals(indicators)
    indicators["interval"] = interval
    indicators["exchange"] = exchange

    return indicators


def _assess_trend(indicators: dict[str, Any]) -> dict[str, Any]:
    """Assess overall trend from indicators."""
    signals = []

    # EMA trend
    ema = indicators.get("ema", {})
    if ema.get("ema_12") and ema.get("ema_26"):
        if ema["ema_12"] > ema["ema_26"]:
            signals.append(("ema_cross", "bullish"))
        else:
            signals.append(("ema_cross", "bearish"))

    # SMA trend
    sma = indicators.get("sma", {})
    price = indicators.get("latest_close", 0)
    if sma.get("sma_50") and price:
        if price > sma["sma_50"]:
            signals.append(("price_vs_sma50", "bullish"))
        else:
            signals.append(("price_vs_sma50", "bearish"))

    # RSI
    rsi = indicators.get("rsi", {})
    if rsi.get("signal") == "oversold":
        signals.append(("rsi", "bullish"))
    elif rsi.get("signal") == "overbought":
        signals.append(("rsi", "bearish"))
    else:
        signals.append(("rsi", "neutral"))

    # MACD
    macd = indicators.get("macd", {})
    macd_signal = macd.get("signal", "")
    if "bullish" in macd_signal:
        signals.append(("macd", "bullish"))
    elif "bearish" in macd_signal:
        signals.append(("macd", "bearish"))

    # Bollinger position
    bb = indicators.get("bollinger_bands", {})
    if bb.get("signal") == "near_lower":
        signals.append(("bollinger", "bullish"))
    elif bb.get("signal") == "near_upper":
        signals.append(("bollinger", "bearish"))
    else:
        signals.append(("bollinger", "neutral"))

    # Count
    bullish = sum(1 for _, s in signals if s == "bullish")
    bearish = sum(1 for _, s in signals if s == "bearish")

    if bullish > bearish + 1:
        overall = "bullish"
    elif bearish > bullish + 1:
        overall = "bearish"
    else:
        overall = "neutral"

    return {
        "overall": overall,
        "bullish_signals": bullish,
        "bearish_signals": bearish,
        "details": signals,
    }


def _summarize_signals(indicators: dict[str, Any]) -> str:
    """Generate a human-readable signal summary."""
    parts = []

    rsi = indicators.get("rsi", {})
    if rsi.get("value"):
        parts.append(f"RSI {rsi['value']} ({rsi.get('signal', 'N/A')})")

    macd = indicators.get("macd", {})
    if macd.get("signal"):
        parts.append(f"MACD {macd['signal']}")

    bb = indicators.get("bollinger_bands", {})
    if bb.get("pct_b") is not None:
        parts.append(f"BB %B={bb['pct_b']}")

    trend = indicators.get("trend", {})
    if trend.get("overall"):
        parts.append(f"Trend: {trend['overall']}")

    vol = indicators.get("volume_profile", {})
    if vol.get("relative_volume"):
        rv = vol["relative_volume"]
        vol_label = "high" if rv > 1.5 else "low" if rv < 0.5 else "normal"
        parts.append(f"Volume: {vol_label} ({rv:.1f}x)")

    return " | ".join(parts)


async def multi_timeframe_analysis(
    symbol: str,
    exchange: str = "okx",
) -> dict[str, Any]:
    """Analyze a symbol across multiple timeframes.

    Args:
        symbol: Trading pair
        exchange: Exchange name

    Returns:
        Dict with analysis for each timeframe and consensus
    """
    timeframes = ["15m", "1h", "4h", "1d"]
    results: dict[str, Any] = {"symbol": symbol, "exchange": exchange, "timeframes": {}}

    for tf in timeframes:
        analysis = await full_technical_analysis(symbol, interval=tf, exchange=exchange)
        results["timeframes"][tf] = {
            "trend": analysis.get("trend", {}).get("overall", "unknown"),
            "rsi": analysis.get("rsi", {}).get("value"),
            "macd_signal": analysis.get("macd", {}).get("signal"),
            "signal_summary": analysis.get("signal_summary", ""),
        }

    # Consensus across timeframes
    trends = [v["trend"] for v in results["timeframes"].values() if v["trend"] != "unknown"]
    if trends:
        bullish = trends.count("bullish")
        bearish = trends.count("bearish")
        if bullish > bearish:
            results["consensus"] = "bullish"
        elif bearish > bullish:
            results["consensus"] = "bearish"
        else:
            results["consensus"] = "neutral"
        results["alignment"] = f"{max(bullish, bearish)}/{len(trends)} timeframes agree"
    else:
        results["consensus"] = "insufficient_data"

    return results


def score_trade_setup(
    indicators: dict[str, Any],
    side: str = "buy",
) -> dict[str, Any]:
    """Score a potential trade setup based on indicators.

    Args:
        indicators: Output from full_technical_analysis
        side: "buy" or "sell"

    Returns:
        Dict with score (0-100), confidence, reasoning
    """
    score = 50  # neutral starting point
    reasons = []

    trend = indicators.get("trend", {})
    if side == "buy":
        if trend.get("overall") == "bullish":
            score += 15
            reasons.append("+15: Bullish trend alignment")
        elif trend.get("overall") == "bearish":
            score -= 15
            reasons.append("-15: Against bearish trend")
    else:
        if trend.get("overall") == "bearish":
            score += 15
            reasons.append("+15: Bearish trend alignment")
        elif trend.get("overall") == "bullish":
            score -= 15
            reasons.append("-15: Against bullish trend")

    # RSI
    rsi = indicators.get("rsi", {})
    rsi_val = rsi.get("value")
    if rsi_val is not None:
        if side == "buy" and rsi_val < 30:
            score += 10
            reasons.append(f"+10: RSI oversold ({rsi_val})")
        elif side == "sell" and rsi_val > 70:
            score += 10
            reasons.append(f"+10: RSI overbought ({rsi_val})")
        elif side == "buy" and rsi_val > 70:
            score -= 10
            reasons.append(f"-10: RSI overbought for buy ({rsi_val})")
        elif side == "sell" and rsi_val < 30:
            score -= 10
            reasons.append(f"-10: RSI oversold for sell ({rsi_val})")

    # MACD
    macd = indicators.get("macd", {})
    macd_signal = macd.get("signal", "")
    if side == "buy" and "bullish_cross" in macd_signal:
        score += 10
        reasons.append("+10: MACD bullish crossover")
    elif side == "sell" and "bearish_cross" in macd_signal:
        score += 10
        reasons.append("+10: MACD bearish crossover")

    # Volume
    vol = indicators.get("volume_profile", {})
    rv = vol.get("relative_volume", 1.0)
    if rv > 1.5:
        score += 5
        reasons.append(f"+5: High volume confirmation ({rv:.1f}x)")

    # ATR for volatility
    atr = indicators.get("atr", {})
    atr_pct = atr.get("pct")
    if atr_pct and atr_pct > 5:
        score -= 5
        reasons.append(f"-5: High volatility (ATR {atr_pct}%)")

    score = max(0, min(100, score))

    if score >= 70:
        confidence = "high"
    elif score >= 50:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "score": score,
        "confidence": confidence,
        "side": side,
        "reasoning": reasons,
    }
