"""Psychology Coach Agent — trading psychology, emotional regulation, behavior patterns.

Fuses multiple coaching styles (Wendy/Marcus/Alex/Socrates) into one agent.
Detects emotional patterns, provides real-time check-ins, and tracks
psychological evolution over time using the memory system.
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


def create_psychology_coach(
    model: str = "anthropic/claude-sonnet-4-20250514",
) -> PsychologyCoachAgent:
    """Factory: create a configured Psychology Coach agent."""
    config = AgentConfig(
        agent_id="psychology-coach",
        name="Psychology Coach",
        description="Trading psychology specialist — emotional regulation and behavior pattern detection",
        agent_type="psychology",
        model=model,
        temperature=0.7,  # Higher temperature for empathetic responses
        max_tokens=4096,
        subscriptions=[
            EventType.PATTERN_DETECTED.value,
            EventType.BEHAVIOR_ALERT.value,
            EventType.LOSS_STREAK.value,
            EventType.USER_MESSAGE.value,
            EventType.AGENT_ANALYSIS.value,
        ],
        trust_level=0,  # OBSERVE — no trade execution
        cooldown_seconds=10,
        is_active=True,
    )
    return PsychologyCoachAgent(config)


class PsychologyCoachAgent(BaseAgent):
    """Psychology Coach Agent implementation."""

    def _default_system_prompt(self) -> str:
        template = TEMPLATE_DIR / "psychology.txt"
        if template.exists():
            return template.read_text()
        return "You are the Psychology Coach Agent of KeelTrader."

    def _register_tools(self, agent: Agent) -> None:
        """Register memory and communication tools."""
        register_tools_for_agent(agent, "psychology")

        @agent.tool
        async def assess_emotional_state(
            ctx: RunContext[AgentDependencies],
            recent_trades: list[dict[str, Any]] | None = None,
            user_message: str = "",
        ) -> dict[str, Any]:
            """Assess the user's current emotional state based on trading behavior.

            Args:
                recent_trades: Recent trade history (if available)
                user_message: User's latest message for sentiment analysis
            """
            indicators: dict[str, Any] = {
                "emotional_markers": [],
                "risk_level": "low",
                "suggested_action": "none",
            }

            if recent_trades:
                # Detect patterns
                losses = [t for t in recent_trades if float(t.get("pnl", 0)) < 0]
                wins = [t for t in recent_trades if float(t.get("pnl", 0)) > 0]

                # Losing streak
                consecutive_losses = 0
                for t in reversed(recent_trades):
                    if float(t.get("pnl", 0)) < 0:
                        consecutive_losses += 1
                    else:
                        break

                if consecutive_losses >= 3:
                    indicators["emotional_markers"].append("losing_streak")
                    indicators["risk_level"] = "high"
                    indicators["consecutive_losses"] = consecutive_losses
                    indicators["suggested_action"] = "pause_trading"

                # Win streak (overconfidence risk)
                consecutive_wins = 0
                for t in reversed(recent_trades):
                    if float(t.get("pnl", 0)) > 0:
                        consecutive_wins += 1
                    else:
                        break

                if consecutive_wins >= 5:
                    indicators["emotional_markers"].append("winning_streak_overconfidence")
                    indicators["risk_level"] = max(indicators["risk_level"], "medium")
                    indicators["consecutive_wins"] = consecutive_wins

                # Frequency increase (potential revenge trading)
                if len(recent_trades) >= 5:
                    # Check if trading frequency is increasing
                    indicators["trade_count_recent"] = len(recent_trades)

            # Simple sentiment from message
            if user_message:
                negative_words = [
                    "亏", "损", "惨", "完了", "后悔", "怎么办", "焦虑", "紧张",
                    "fuck", "shit", "loss", "lost", "regret", "anxious", "scared",
                ]
                positive_words = [
                    "赚", "涨", "牛", "太好了", "开心",
                    "profit", "win", "great", "happy", "bullish",
                ]

                msg_lower = user_message.lower()
                neg_count = sum(1 for w in negative_words if w in msg_lower)
                pos_count = sum(1 for w in positive_words if w in msg_lower)

                if neg_count > pos_count:
                    indicators["emotional_markers"].append("negative_sentiment")
                    if neg_count >= 2:
                        indicators["risk_level"] = "medium"
                elif pos_count > 0 and neg_count == 0:
                    indicators["emotional_markers"].append("positive_sentiment")

            return indicators

        @agent.tool
        async def get_psychological_profile(
            ctx: RunContext[AgentDependencies],
        ) -> dict[str, Any]:
            """Retrieve the user's psychological profile from memory.

            Returns known patterns, triggers, and effective coping strategies.
            """
            from ..memory.tools import memory_search

            user_id = ctx.deps.user_id

            # Search episodic memory for past patterns
            past_patterns = await memory_search(
                query="behavior_pattern",
                layer="episodic",
                agent_id="psychology-coach",
                user_id=user_id,
                time_range_days=30,
                limit=5,
            )

            # Search semantic memory for learned strategies
            strategies = await memory_search(
                query="coping strategy effective",
                layer="semantic",
                agent_id="psychology-coach",
                user_id=user_id,
                limit=5,
            )

            return {
                "user_id": user_id,
                "known_patterns": [
                    {"key": e.memory_key, "value": e.memory_value}
                    for e in past_patterns.entries
                ],
                "effective_strategies": [
                    {"key": e.memory_key, "value": e.memory_value}
                    for e in strategies.entries
                ],
                "total_observations": past_patterns.total_count,
            }

        @agent.tool
        async def record_psychological_observation(
            ctx: RunContext[AgentDependencies],
            observation_type: str,
            details: str,
            severity: str = "low",
        ) -> str:
            """Record a psychological observation about the user's behavior.

            Args:
                observation_type: Type (e.g., revenge_trading, fomo, fear_exit, overconfidence)
                details: Description of the observed behavior
                severity: low/medium/high/critical
            """
            from ..memory.tools import memory_update

            await memory_update(
                key=f"behavior_pattern:{observation_type}",
                value={
                    "type": observation_type,
                    "details": details,
                    "severity": severity,
                },
                layer="episodic",
                agent_id="psychology-coach",
                user_id=ctx.deps.user_id,
                importance={"low": 0.3, "medium": 0.5, "high": 0.7, "critical": 0.9}.get(
                    severity, 0.5
                ),
            )
            return f"Observation recorded: {observation_type} ({severity})"

    async def handle_event(
        self, event: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle events with psychology-specific logic."""
        event_type = event.get("type", "")
        payload = event.get("payload", {})

        if event_type == EventType.LOSS_STREAK.value:
            return await self._handle_loss_streak(payload, deps)
        elif event_type == EventType.BEHAVIOR_ALERT.value:
            return await self._handle_behavior_alert(payload, deps)
        elif event_type == EventType.PATTERN_DETECTED.value:
            return await self._handle_pattern_detected(payload, deps)
        elif event_type == EventType.USER_MESSAGE.value:
            target = payload.get("target_agent", "")
            if target in ("psychology", "psychology-coach", "coach"):
                return await self._handle_user_message(payload, deps)
            return AgentResult(
                agent_id=self.agent_id, success=True,
                message="Not targeted at psychology coach",
            )
        else:
            return await super().handle_event(event, deps)

    async def _handle_loss_streak(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle a loss streak event — provide emotional support."""
        streak_count = payload.get("streak_count", 3)
        total_loss = payload.get("total_loss", 0)

        agent = self.get_pydantic_agent()
        prompt = (
            f"The user has a losing streak of {streak_count} consecutive trades "
            f"with total loss of ${abs(total_loss):,.2f}.\n\n"
            "1. Use assess_emotional_state to evaluate the situation.\n"
            "2. Use get_psychological_profile to check for recurring patterns.\n"
            "3. If this is a new pattern, record it with record_psychological_observation.\n"
            "4. Provide a supportive response that:\n"
            "   - Acknowledges the difficulty (Wendy)\n"
            "   - Presents the data objectively (Alex)\n"
            "   - Suggests concrete next steps (Marcus)\n"
            "   - Ends with a reflective question (Socrates)\n"
            "5. Keep response under 200 words. Use HTML formatting for Telegram."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"trigger": "loss_streak", "streak_count": streak_count},
            )
        except Exception as e:
            logger.error("Loss streak handling failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )

    async def _handle_behavior_alert(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle a behavior alert from Guardian."""
        pattern_type = payload.get("pattern_type", "unknown")
        severity = payload.get("severity", "medium")

        agent = self.get_pydantic_agent()
        prompt = (
            f"Guardian has detected a {severity} behavior pattern: {pattern_type}\n"
            f"Details: {payload}\n\n"
            "1. Record this observation with record_psychological_observation.\n"
            "2. Check psychological profile for past occurrences.\n"
            "3. Craft a response appropriate to the severity level.\n"
            "4. If severity is high/critical, strongly recommend a break."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"pattern_type": pattern_type, "severity": severity},
            )
        except Exception as e:
            logger.error("Behavior alert handling failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )

    async def _handle_pattern_detected(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle a pattern detection event."""
        return await self._handle_behavior_alert(payload, deps)

    async def _handle_user_message(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle direct user message to the psychology coach."""
        message = payload.get("text", "")
        agent = self.get_pydantic_agent()

        prompt = (
            f"User message: {message}\n\n"
            "1. Assess their emotional state from the message.\n"
            "2. Check their psychological profile.\n"
            "3. Respond with empathy and practical advice.\n"
            "4. Use the appropriate coaching style based on what they need."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"trigger": "user_message"},
            )
        except Exception as e:
            logger.error("User message handling failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )
