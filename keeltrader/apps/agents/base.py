"""Base Agent class built on PydanticAI."""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from pydantic_ai import Agent

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AgentConfig(BaseModel):
    """Configuration for an Agent."""

    agent_id: str
    name: str
    description: str
    agent_type: str  # orchestrator / analyst / coach / guardian / executor
    model: str = "anthropic/claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str = ""
    subscriptions: list[str] = []
    trust_level: int = 0  # 0=OBSERVE, 1=SUGGEST, 2=CONFIRM, 3=AUTO
    max_order_usd: float = 0.0
    daily_limit: int = 0
    allowed_symbols: list[str] = []
    cooldown_seconds: int = 60
    is_active: bool = True


class AgentResult(BaseModel):
    """Standardized agent execution result."""

    agent_id: str
    success: bool
    message: str = ""
    data: dict[str, Any] = {}
    events_emitted: list[str] = []
    tools_called: list[str] = []


@dataclass
class AgentDependencies:
    """Dependencies injected into agent tools via PydanticAI dependency injection."""

    user_id: str | None = None
    db_url: str = ""
    redis_url: str = ""
    litellm_base: str = ""
    litellm_key: str = ""
    correlation_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    """Base class for all KeelTrader agents.

    Wraps PydanticAI Agent with standardized configuration,
    event subscription, and execution patterns.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self._agent: Agent | None = None
        self._tools_registered = False
        logger.info(
            "Agent initialized: %s (%s)", config.agent_id, config.agent_type
        )

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @property
    def subscriptions(self) -> list[str]:
        return self.config.subscriptions

    def get_pydantic_agent(self) -> Agent:
        """Get or create the PydanticAI agent instance."""
        if self._agent is None:
            self._agent = Agent(
                model=self.config.model,
                system_prompt=self._build_system_prompt(),
                deps_type=AgentDependencies,
            )
            self._register_tools(self._agent)
            self._tools_registered = True
        return self._agent

    def _build_system_prompt(self) -> str:
        """Build the full system prompt for this agent."""
        base = self.config.system_prompt
        if not base:
            base = self._default_system_prompt()
        return base

    @abstractmethod
    def _default_system_prompt(self) -> str:
        """Return the default system prompt for this agent type."""
        ...

    @abstractmethod
    def _register_tools(self, agent: Agent) -> None:
        """Register PydanticAI tools on the agent instance."""
        ...

    async def handle_event(
        self, event: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle an incoming event from the event bus.

        Subclasses should override this to implement event-specific logic.
        Default implementation runs the agent with event data as the prompt.
        """
        agent = self.get_pydantic_agent()
        event_type = event.get("type", "unknown")
        payload = event.get("payload", {})

        prompt = (
            f"Event: {event_type}\n"
            f"Payload: {payload}\n"
            f"Handle this event according to your role."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"event_type": event_type},
            )
        except Exception as e:
            logger.error("Agent %s failed on event %s: %s", self.agent_id, event_type, e)
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                message=f"Error: {e}",
                data={"event_type": event_type, "error": str(e)},
            )

    async def run(
        self, prompt: str, deps: AgentDependencies | None = None
    ) -> AgentResult:
        """Run the agent with a direct prompt (e.g., from user message)."""
        agent = self.get_pydantic_agent()
        if deps is None:
            deps = AgentDependencies()

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
            )
        except Exception as e:
            logger.error("Agent %s run failed: %s", self.agent_id, e)
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                message=f"Error: {e}",
            )
