"""Event dispatcher — routes events to subscribed agents."""

from __future__ import annotations

import logging
from typing import Any

from ..agents.base import AgentDependencies, AgentResult, BaseAgent
from .event_types import Event
from .safety import EventSafety

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Routes events from the bus to subscribed agents."""

    def __init__(self, safety: EventSafety):
        self._agents: dict[str, BaseAgent] = {}
        self._subscriptions: dict[str, list[str]] = {}  # event_type -> [agent_ids]
        self._safety = safety

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent and its event subscriptions."""
        self._agents[agent.agent_id] = agent
        for event_type in agent.subscriptions:
            self._subscriptions.setdefault(event_type, []).append(agent.agent_id)
        logger.info(
            "Registered agent %s with subscriptions: %s",
            agent.agent_id, agent.subscriptions,
        )

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self._agents:
            agent = self._agents.pop(agent_id)
            for event_type in agent.subscriptions:
                if event_type in self._subscriptions:
                    self._subscriptions[event_type] = [
                        aid for aid in self._subscriptions[event_type]
                        if aid != agent_id
                    ]

    def get_subscribers(self, event_type: str) -> list[str]:
        """Get agent IDs subscribed to an event type."""
        return self._subscriptions.get(event_type, [])

    async def dispatch(
        self, event: Event, deps: AgentDependencies
    ) -> list[AgentResult]:
        """Dispatch an event to all subscribed agents.

        Returns list of results from each agent.
        """
        subscribers = self.get_subscribers(event.type.value)
        if not subscribers:
            logger.debug("No subscribers for event: %s", event.type.value)
            return []

        results = []
        for agent_id in subscribers:
            agent = self._agents.get(agent_id)
            if agent is None:
                continue

            if not agent.config.is_active:
                continue

            # Safety checks
            allowed, reason = await self._safety.check_all(event, agent_id)
            if not allowed:
                logger.warning(
                    "Event %s blocked for agent %s: %s",
                    event.type.value, agent_id, reason,
                )
                results.append(AgentResult(
                    agent_id=agent_id,
                    success=False,
                    message=f"Blocked: {reason}",
                    data={"event_type": event.type.value, "blocked_reason": reason},
                ))
                continue

            try:
                event_dict = {
                    "type": event.type.value,
                    "source": event.source,
                    "user_id": str(event.user_id) if event.user_id else None,
                    "payload": event.payload,
                    "correlation_id": str(event.correlation_id),
                    "causation_id": str(event.causation_id) if event.causation_id else None,
                }

                # Set correlation context
                deps.correlation_id = str(event.correlation_id)

                result = await agent.handle_event(event_dict, deps)
                results.append(result)

                # Record execution for cooldown
                await self._safety.record_agent_execution(agent_id)

                logger.info(
                    "Agent %s processed event %s: success=%s",
                    agent_id, event.type.value, result.success,
                )
            except Exception as e:
                logger.error(
                    "Agent %s failed on event %s: %s",
                    agent_id, event.type.value, e,
                )
                results.append(AgentResult(
                    agent_id=agent_id,
                    success=False,
                    message=f"Error: {e}",
                    data={"event_type": event.type.value, "error": str(e)},
                ))

        return results

    @property
    def registered_agents(self) -> dict[str, BaseAgent]:
        return dict(self._agents)
