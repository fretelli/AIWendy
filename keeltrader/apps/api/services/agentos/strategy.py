"""AgentOS guarded strategy experiment workflows."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agentos.models import BacktestRun, StrategyHypothesis
from services.agentos.metrics import summarize_trade_returns
from services.agentos.research import _as_iso
from services.agentos.tushare_read import TushareReadService


class AgentOSStrategyService:
    """Strategy hypotheses and deterministic v1 backtests."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.tushare = TushareReadService(session)

    async def create_hypothesis(self, user_id: UUID, payload: dict[str, Any]) -> StrategyHypothesis:
        hypothesis = StrategyHypothesis(
            user_id=user_id,
            project_id=payload.get("project_id"),
            name=payload["name"],
            hypothesis=payload["hypothesis"],
            rationale=payload.get("rationale"),
            asset_universe=payload.get("asset_universe") or [],
            frequency=payload.get("frequency", "daily"),
            status="draft",
        )
        self.session.add(hypothesis)
        await self.session.flush()
        return hypothesis

    async def record_backtest(
        self,
        user_id: UUID,
        symbol: str,
        strategy: str,
        params: dict[str, Any] | None = None,
        hypothesis_id: UUID | None = None,
    ) -> BacktestRun:
        """Run a simple MA crossover backtest and persist metrics."""
        params = params or {}
        hypothesis = None
        if hypothesis_id:
            result = await self.session.execute(
                select(StrategyHypothesis).where(StrategyHypothesis.id == hypothesis_id, StrategyHypothesis.user_id == user_id)
            )
            hypothesis = result.scalar_one_or_none()

        bars = list(reversed(await self.tushare.daily_bars(symbol, limit=500, adjusted=False)))
        fast = int(params.get("fast_period", 20))
        slow = int(params.get("slow_period", 60))
        trades: list[dict[str, Any]] = []
        returns: list[float] = []
        position = None

        closes = [float(b["close"]) for b in bars if b.get("close") is not None]
        dates = [b.get("trade_date") for b in bars if b.get("close") is not None]
        if strategy != "ma_crossover":
            notes = "v1 persisted unsupported strategy as metadata only; no trades generated."
        elif len(closes) < slow + 2:
            notes = "Insufficient bars for MA crossover."
        else:
            notes = "MA crossover backtest completed with deterministic vectorized v1 engine."
            for i in range(slow, len(closes)):
                fast_ma = sum(closes[i - fast + 1:i + 1]) / fast
                slow_ma = sum(closes[i - slow + 1:i + 1]) / slow
                prev_fast = sum(closes[i - fast:i]) / fast
                prev_slow = sum(closes[i - slow:i]) / slow
                if prev_fast <= prev_slow and fast_ma > slow_ma and position is None:
                    position = {"entry_price": closes[i], "entry_time": dates[i]}
                elif prev_fast >= prev_slow and fast_ma < slow_ma and position is not None:
                    ret = (closes[i] - position["entry_price"]) / position["entry_price"] * 100
                    returns.append(ret)
                    trades.append({
                        "entry_time": _as_iso(position["entry_time"]),
                        "exit_time": _as_iso(dates[i]),
                        "entry_price": position["entry_price"],
                        "exit_price": closes[i],
                        "pnl_pct": round(ret, 4),
                    })
                    position = None

        attempt_number = (hypothesis.attempt_count + 1) if hypothesis else 1
        metrics = summarize_trade_returns(returns, trials=attempt_number)
        passed_gate = (
            metrics.get("total_trades", 0) >= 10
            and metrics.get("max_drawdown_pct", 100) <= 25
            and metrics.get("deflated_sharpe_proxy", 0) > 0.5
        )
        if hypothesis:
            hypothesis.attempt_count = attempt_number
            hypothesis.status = "observing" if passed_gate else "tested"

        run = BacktestRun(
            user_id=user_id,
            hypothesis_id=hypothesis_id,
            symbol=symbol,
            strategy=strategy,
            params=params,
            metrics=metrics,
            trades=trades[-100:],
            attempt_number=attempt_number,
            passed_gate=passed_gate,
            notes=notes,
        )
        self.session.add(run)
        await self.session.flush()
        return run
