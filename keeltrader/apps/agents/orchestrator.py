"""Orchestrator Agent — central coordinator of the Agent Matrix.

Understands user intent, decomposes complex requests, dispatches to
specialized agents, and synthesizes multi-agent results.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext

from .base import AgentConfig, AgentDependencies, AgentResult, BaseAgent
from ..engine.event_types import Event, EventType
from ..tools.registry import register_tools_for_agent

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


def create_orchestrator(model: str = "anthropic/claude-sonnet-4-20250514") -> OrchestratorAgent:
    """Factory: create a configured Orchestrator agent."""
    config = AgentConfig(
        agent_id="orchestrator",
        name="Orchestrator",
        description="Central coordinator — routes tasks and synthesizes results",
        agent_type="orchestrator",
        model=model,
        temperature=0.5,
        max_tokens=4096,
        subscriptions=[
            EventType.USER_MESSAGE.value,
            EventType.USER_COMMAND.value,
            EventType.AGENT_ANALYSIS.value,
            EventType.AGENT_RECOMMENDATION.value,
            EventType.SYSTEM_STARTUP.value,
            EventType.DAILY_REVIEW.value,
        ],
        trust_level=1,  # SUGGEST — can't execute trades
        cooldown_seconds=5,
        is_active=True,
    )
    return OrchestratorAgent(config)


class OrchestratorAgent(BaseAgent):
    """Orchestrator Agent implementation."""

    def _default_system_prompt(self) -> str:
        """Load system prompt from template file."""
        template = TEMPLATE_DIR / "orchestrator.txt"
        if template.exists():
            return template.read_text()
        return "You are the Orchestrator Agent of KeelTrader."

    def _register_tools(self, agent: Agent) -> None:
        """Register tools for the Orchestrator."""
        register_tools_for_agent(agent, "orchestrator")

        # Additional orchestrator-specific tools
        @agent.tool
        async def route_to_analyst(
            ctx: RunContext[AgentDependencies],
            agent_type: str,
            query: str,
            symbol: str | None = None,
        ) -> str:
            """Route an analysis request to a specialized agent.

            Args:
                agent_type: Target agent (technical, sentiment, fundamental)
                query: The analysis question
                symbol: Optional trading pair
            """
            from ..tools.communication import delegate_to_agent

            result = await delegate_to_agent(
                agent_type=agent_type,
                context={"query": query, "symbol": symbol},
                user_id=ctx.deps.user_id,
                correlation_id=ctx.deps.correlation_id,
            )
            if result.get("success"):
                return f"Delegated to {agent_type} agent (event: {result['event_id']})"
            return f"Failed to delegate: {result.get('error', 'unknown')}"

        @agent.tool
        async def classify_intent(
            ctx: RunContext[AgentDependencies],
            user_message: str,
        ) -> dict[str, Any]:
            """Classify user message intent to determine routing.

            Args:
                user_message: Raw user message text

            Returns:
                Dict with intent type, target agents, and extracted entities
            """
            message_lower = user_message.lower()

            # Simple keyword-based intent classification
            intent: dict[str, Any] = {
                "original": user_message,
                "targets": [],
                "entities": {},
            }

            # Detect symbols
            import re
            symbol_match = re.findall(
                r'\b(BTC|ETH|SOL|BNB|XRP|ADA|DOGE|DOT|AVAX|MATIC|LINK|UNI)(?:/USDT?)?\b',
                user_message.upper(),
            )
            if symbol_match:
                intent["entities"]["symbols"] = [
                    f"{s}/USDT" for s in symbol_match
                ]

            # Technical analysis keywords
            tech_keywords = [
                "价格", "k线", "指标", "rsi", "macd", "趋势", "支撑", "阻力",
                "price", "chart", "indicator", "trend", "support", "resistance",
                "技术分析", "technical", "ema", "sma", "布林",
            ]
            if any(kw in message_lower for kw in tech_keywords):
                intent["targets"].append("technical")

            # Sentiment keywords
            sent_keywords = [
                "情绪", "舆情", "消息", "新闻", "恐惧", "贪婪",
                "sentiment", "news", "fear", "greed", "social",
            ]
            if any(kw in message_lower for kw in sent_keywords):
                intent["targets"].append("sentiment")

            # Fundamental keywords
            fund_keywords = [
                "基本面", "链上", "tvl", "持仓", "市值", "fundamental",
                "on-chain", "mcap", "supply", "etf",
            ]
            if any(kw in message_lower for kw in fund_keywords):
                intent["targets"].append("fundamental")

            # Psychology keywords
            psych_keywords = [
                "心理", "情绪", "焦虑", "冲动", "纪律", "复盘",
                "psychology", "emotion", "discipline", "anxiety", "review",
            ]
            if any(kw in message_lower for kw in psych_keywords):
                intent["targets"].append("psychology")

            # Risk / guardian keywords
            risk_keywords = [
                "风险", "仓位", "止损", "风控", "risk", "position",
                "stop.?loss", "杠杆", "leverage",
            ]
            if any(kw in message_lower for kw in risk_keywords):
                intent["targets"].append("guardian")

            # Trade execution keywords
            exec_keywords = [
                "买", "卖", "做多", "做空", "开仓", "平仓", "下单",
                "buy", "sell", "long", "short", "open", "close", "order",
            ]
            if any(kw in message_lower for kw in exec_keywords):
                intent["targets"].append("guardian")  # Always route through guardian first
                intent["is_execution"] = True

            # Generic analysis request (e.g., "ETH怎么看", "分析BTC")
            general_keywords = [
                "怎么看", "分析", "analyze", "analysis", "看法", "观点",
                "怎么样", "适合", "建议", "recommend", "should",
            ]
            if any(kw in message_lower for kw in general_keywords):
                if "technical" not in intent["targets"]:
                    intent["targets"].append("technical")
                # Multi-agent analysis for broad questions
                if not intent["targets"] or len(intent["targets"]) == 1:
                    intent["targets"].extend(["sentiment", "fundamental"])

            # Deduplicate
            intent["targets"] = list(dict.fromkeys(intent["targets"]))

            if not intent["targets"]:
                intent["targets"] = ["orchestrator"]  # Handle directly
                intent["is_general_chat"] = True

            return intent

    async def handle_event(
        self, event: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle events with orchestrator-specific logic."""
        event_type = event.get("type", "")
        payload = event.get("payload", {})

        if event_type == EventType.USER_MESSAGE.value:
            return await self._handle_user_message(payload, deps)
        elif event_type == EventType.AGENT_ANALYSIS.value:
            return await self._handle_agent_analysis(payload, deps)
        elif event_type == EventType.DAILY_REVIEW.value:
            return await self._trigger_daily_review(deps)
        else:
            return await super().handle_event(event, deps)

    async def _handle_user_message(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Process a user message: classify intent and route to agents."""
        message = payload.get("text", "")
        if not message:
            return AgentResult(
                agent_id=self.agent_id, success=False, message="Empty message"
            )

        agent = self.get_pydantic_agent()

        prompt = (
            f"User message: {message}\n\n"
            "1. Use classify_intent to understand what the user wants.\n"
            "2. If symbols are detected, use get_price to get current prices.\n"
            "3. For analysis requests, use route_to_analyst to dispatch to appropriate agents.\n"
            "4. Provide a helpful initial response while agents work on detailed analysis.\n"
            "5. Respond in the same language as the user."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"event_type": "user.message"},
            )
        except Exception as e:
            logger.error("Orchestrator failed on user message: %s", e)
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                message=f"处理消息时出错: {e}",
            )

    async def _handle_agent_analysis(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Collect and synthesize analysis results from other agents."""
        agent = self.get_pydantic_agent()
        source_agent = payload.get("source_agent", "unknown")
        analysis = payload.get("analysis", {})

        prompt = (
            f"Analysis result from {source_agent}:\n{analysis}\n\n"
            "Summarize this analysis result concisely for the user. "
            "If this completes a multi-agent analysis, provide the final synthesis."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"synthesized_from": source_agent},
            )
        except Exception as e:
            logger.error("Orchestrator synthesis failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e)
            )

    async def _trigger_daily_review(self, deps: AgentDependencies) -> AgentResult:
        """Trigger daily review — dispatch analysis tasks to all analysts."""
        from ..tools.communication import delegate_to_agent

        # Dispatch to technical analyst for major pairs
        for symbol in ["BTC/USDT", "ETH/USDT"]:
            await delegate_to_agent(
                agent_type="technical",
                context={"query": "daily_review", "symbol": symbol},
                user_id=deps.user_id,
                correlation_id=deps.correlation_id,
            )

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            message="Daily review dispatched to analysts",
            events_emitted=["agent.analysis"],
        )
