"""Deterministic metrics for strategy evaluation."""

from __future__ import annotations

import math
from statistics import mean, pstdev


def max_drawdown(equity_curve: list[float]) -> float:
    """Return max drawdown percentage for an equity curve."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak:
            max_dd = max(max_dd, (peak - value) / peak * 100)
    return round(max_dd, 4)


def sharpe_ratio(returns: list[float], periods_per_year: int = 252) -> float:
    """Annualized Sharpe ratio from periodic returns."""
    if len(returns) < 2:
        return 0.0
    vol = pstdev(returns)
    if vol == 0:
        return 0.0
    return round(mean(returns) / vol * math.sqrt(periods_per_year), 4)


def deflated_sharpe_ratio_proxy(
    sharpe: float,
    observations: int,
    trials: int,
) -> float:
    """Conservative DSR-style proxy.

    Full DSR requires skew/kurtosis and expected max Sharpe under multiple
    testing. This proxy deliberately penalizes high trial counts and small
    samples so v1 does not overstate strategy quality.
    """
    if observations <= 1:
        return 0.0
    trials = max(trials, 1)
    sample_penalty = math.sqrt((observations - 1) / observations)
    search_penalty = math.sqrt(2 * math.log(trials + 1)) / math.sqrt(observations)
    return round(sharpe * sample_penalty - search_penalty, 4)


def summarize_trade_returns(pct_returns: list[float], trials: int = 1) -> dict:
    """Return common backtest metrics from trade percentage returns."""
    if not pct_returns:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "deflated_sharpe_proxy": 0.0,
            "dsr_method": "conservative_proxy_v1",
            "research_only": True,
        }

    equity = [100.0]
    periodic_returns = []
    for pct in pct_returns:
        r = pct / 100
        periodic_returns.append(r)
        equity.append(equity[-1] * (1 + r))

    wins = [p for p in pct_returns if p > 0]
    losses = [p for p in pct_returns if p <= 0]
    sharpe = sharpe_ratio(periodic_returns)
    return {
        "total_trades": len(pct_returns),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(pct_returns) * 100, 2),
        "total_return_pct": round(equity[-1] - 100, 4),
        "max_drawdown_pct": max_drawdown(equity),
        "avg_win_pct": round(mean(wins), 4) if wins else 0.0,
        "avg_loss_pct": round(mean(losses), 4) if losses else 0.0,
        "profit_factor": round(abs(sum(wins) / sum(losses)), 4) if losses and sum(losses) else 0.0,
        "sharpe_ratio": sharpe,
        "deflated_sharpe_proxy": deflated_sharpe_ratio_proxy(sharpe, len(pct_returns), trials),
        "dsr_method": "conservative_proxy_v1",
        "research_only": True,
    }
