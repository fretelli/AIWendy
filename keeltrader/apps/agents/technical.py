"""Technical Analyst Agent — K-line analysis, indicators, trend identification.

Subscribes to price alerts and kline patterns, runs comprehensive technical
analysis, and produces structured trading signals.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext

from .base import AgentConfig, AgentDependencies, AgentResult, BaseAgent
from ..engine.event_types import EventType
from ..tools.registry import register_tools_for_agent

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


def create_technical_analyst(
    model: str = "anthropic/claude-haiku-4-5-20251001",
) -> TechnicalAnalystAgent:
    """Factory: create a configured Technical Analyst agent."""
    config = AgentConfig(
        agent_id="technical-analyst",
        name="Technical Analyst",
        description="K-line analysis, indicators, trend identification, chart patterns",
        agent_type="technical",
        model=model,
        temperature=0.3,  # Lower temperature for analytical precision
        max_tokens=4096,
        subscriptions=[
            EventType.PRICE_ALERT.value,
            EventType.KLINE_PATTERN.value,
            EventType.AGENT_ANALYSIS.value,
            EventType.DAILY_REVIEW.value,
        ],
        trust_level=0,  # OBSERVE — analysis only, no execution
        cooldown_seconds=30,
        is_active=True,
    )
    return TechnicalAnalystAgent(config)


class TechnicalAnalystAgent(BaseAgent):
    """Technical Analyst Agent implementation."""

    def _default_system_prompt(self) -> str:
        """Load system prompt from template file."""
        template = TEMPLATE_DIR / "technical.txt"
        if template.exists():
            return template.read_text()
        return "You are the Technical Analyst Agent of KeelTrader."

    def _register_tools(self, agent: Agent) -> None:
        """Register market and analysis tools."""
        register_tools_for_agent(agent, "technical")

        @agent.tool
        async def analyze_symbol(
            ctx: RunContext[AgentDependencies],
            symbol: str,
            timeframe: str = "1h",
            exchange: str = "okx",
        ) -> dict[str, Any]:
            """Run full technical analysis on a symbol.

            Fetches market data, calculates all indicators, and assesses trend.

            Args:
                symbol: Trading pair (e.g., "BTC/USDT")
                timeframe: Analysis timeframe (1m, 5m, 15m, 1h, 4h, 1d)
                exchange: Exchange name
            """
            from ..tools.analysis import full_technical_analysis

            return await full_technical_analysis(symbol, interval=timeframe, exchange=exchange)

        @agent.tool
        async def analyze_multiple_timeframes(
            ctx: RunContext[AgentDependencies],
            symbol: str,
            exchange: str = "okx",
        ) -> dict[str, Any]:
            """Analyze a symbol across 15m, 1h, 4h, 1d timeframes.

            Args:
                symbol: Trading pair
                exchange: Exchange name
            """
            from ..tools.analysis import multi_timeframe_analysis

            return await multi_timeframe_analysis(symbol, exchange=exchange)

        @agent.tool
        async def evaluate_trade(
            ctx: RunContext[AgentDependencies],
            symbol: str,
            side: str,
            timeframe: str = "1h",
            exchange: str = "okx",
        ) -> dict[str, Any]:
            """Evaluate a potential trade setup with scoring.

            Args:
                symbol: Trading pair
                side: "buy" or "sell"
                timeframe: Primary analysis timeframe
                exchange: Exchange name
            """
            from ..tools.analysis import full_technical_analysis, score_trade_setup

            indicators = await full_technical_analysis(symbol, interval=timeframe, exchange=exchange)
            if "error" in indicators:
                return indicators
            score = score_trade_setup(indicators, side=side)
            return {**indicators, "trade_score": score}

        @agent.tool
        async def find_key_levels(
            ctx: RunContext[AgentDependencies],
            symbol: str,
            exchange: str = "okx",
        ) -> dict[str, Any]:
            """Identify key support and resistance levels.

            Uses SMA, EMA, Bollinger Bands, and recent highs/lows.

            Args:
                symbol: Trading pair
                exchange: Exchange name
            """
            from ..tools.market import get_klines, calc_indicators
            import numpy as np

            klines = await get_klines(symbol, interval="1d", limit=100, exchange=exchange)
            if not klines:
                return {"symbol": symbol, "error": "No data"}

            indicators = calc_indicators(klines, ["sma", "ema", "bb"])

            highs = [k["high"] for k in klines]
            lows = [k["low"] for k in klines]
            closes = [k["close"] for k in klines]
            current = closes[-1]

            # Recent swing highs/lows (simple approach)
            levels = []

            # SMA levels
            sma = indicators.get("sma", {})
            for key, val in sma.items():
                if val is not None:
                    levels.append({"type": key, "price": val})

            # EMA levels
            ema = indicators.get("ema", {})
            for key, val in ema.items():
                if val is not None:
                    levels.append({"type": key, "price": val})

            # Bollinger Bands
            bb = indicators.get("bollinger_bands", {})
            if bb.get("upper"):
                levels.append({"type": "bb_upper", "price": bb["upper"]})
                levels.append({"type": "bb_lower", "price": bb["lower"]})

            # Recent high/low
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])
            levels.append({"type": "20d_high", "price": recent_high})
            levels.append({"type": "20d_low", "price": recent_low})

            # Classify as support or resistance
            supports = sorted(
                [l for l in levels if l["price"] < current],
                key=lambda x: x["price"],
                reverse=True,
            )
            resistances = sorted(
                [l for l in levels if l["price"] >= current],
                key=lambda x: x["price"],
            )

            return {
                "symbol": symbol,
                "current_price": current,
                "supports": supports[:5],
                "resistances": resistances[:5],
                "range_20d": {"high": recent_high, "low": recent_low},
            }

    async def handle_event(
        self, event: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle events with technical-analyst-specific logic."""
        event_type = event.get("type", "")
        payload = event.get("payload", {})

        if event_type == EventType.PRICE_ALERT.value:
            return await self._handle_price_alert(payload, deps)
        elif event_type == EventType.DAILY_REVIEW.value:
            return await self._handle_daily_review(payload, deps)
        elif event_type == EventType.AGENT_ANALYSIS.value:
            target = payload.get("target_agent", "")
            if target == "technical":
                return await self._handle_analysis_request(payload, deps)
            return AgentResult(
                agent_id=self.agent_id, success=True,
                message="Not targeted at technical analyst",
            )
        else:
            return await super().handle_event(event, deps)

    async def _handle_price_alert(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Analyze a price alert — determine significance and potential trade setups."""
        symbol = payload.get("symbol", "BTC/USDT")
        alert_type = payload.get("alert_type", "unknown")

        agent = self.get_pydantic_agent()
        prompt = (
            f"Price alert triggered for {symbol}: {alert_type}\n"
            f"Alert details: {payload}\n\n"
            "1. Use analyze_multiple_timeframes to check the bigger picture.\n"
            "2. If the alert suggests a potential trade, use evaluate_trade.\n"
            "3. Identify key support/resistance levels with find_key_levels.\n"
            "4. Provide a concise technical summary."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"symbol": symbol, "alert_type": alert_type},
                events_emitted=[EventType.AGENT_ANALYSIS.value],
            )
        except Exception as e:
            logger.error("Price alert analysis failed for %s: %s", symbol, e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )

    async def _handle_daily_review(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Run daily technical review for key pairs."""
        symbol = payload.get("context", {}).get("symbol", "BTC/USDT")

        agent = self.get_pydantic_agent()
        prompt = (
            f"Daily technical review for {symbol}.\n\n"
            "1. Analyze across multiple timeframes.\n"
            "2. Identify the primary trend and any potential trend changes.\n"
            "3. Find key levels and potential trade setups.\n"
            "4. Provide a structured summary suitable for the user's daily briefing."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"symbol": symbol, "review_type": "daily"},
                events_emitted=[EventType.AGENT_ANALYSIS.value],
            )
        except Exception as e:
            logger.error("Daily review failed for %s: %s", symbol, e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )

    async def _handle_analysis_request(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle an analysis request delegated from the Orchestrator."""
        context = payload.get("context", {})
        query = context.get("query", "")
        symbol = context.get("symbol")

        agent = self.get_pydantic_agent()

        if symbol:
            prompt = (
                f"Analysis request for {symbol}: {query}\n\n"
                "1. Use analyze_symbol for primary timeframe analysis.\n"
                "2. If this is a trade evaluation, use evaluate_trade.\n"
                "3. Provide key levels with find_key_levels.\n"
                "4. Give a clear, structured response."
            )
        else:
            prompt = (
                f"Analysis request: {query}\n\n"
                "Respond with your technical analysis expertise."
            )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"query": query, "symbol": symbol},
                events_emitted=[EventType.AGENT_ANALYSIS.value],
            )
        except Exception as e:
            logger.error("Analysis request failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )
