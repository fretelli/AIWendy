"""L3 Procedural Memory — system prompts, rules, and configuration.

Procedural memory stores "how to do things" — agent system prompts,
trading rules, safety rules, and tool definitions. This layer is
primarily loaded from code/config but can be augmented at runtime.

Unlike L1/L2, procedural memories are loaded directly into agent context
and not searched dynamically. Think of them as the agent's "training."
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_PREFIX = "keeltrader:memory:procedural"

# Built-in trading rules (loaded into all agents that need them)
DEFAULT_TRADING_RULES = [
    "永远不要在没有止损的情况下开仓",
    "单笔交易风险不超过账户总值的 2%",
    "每日最大亏损限制: 账户总值的 5%",
    "连续亏损 3 笔后，强制冷静期 30 分钟",
    "不追涨杀跌——等待回调确认再入场",
    "严格遵守交易计划，不临时改变策略",
    "Ghost Trading 验证期内不执行真实交易",
    "Circuit Breaker 激活时，所有交易暂停",
]

# Safety rules (loaded into Guardian and Executor)
SAFETY_RULES = [
    "Trust Level 0 (OBSERVE): 只能分析和建议，不能下单",
    "Trust Level 1 (SUGGEST): 可以建议交易，需用户手动执行",
    "Trust Level 2 (CONFIRM): 可以准备订单，需用户 Telegram 确认",
    "Trust Level 3 (AUTO): 可自动执行，仍受安全栅栏约束",
    "8 层安全栅栏必须全部通过才能执行订单",
    "Circuit Breaker 由 /kill 命令或 Guardian 触发",
    "每个 Agent 有独立的冷却计时器，防止频繁操作",
    "事件链深度上限 5 层，超过自动断路",
]


class ProceduralMemory:
    """L3 Procedural Memory — rules, prompts, and configuration."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url

    async def get_trading_rules(
        self,
        agent_id: str,
        user_id: str | None = None,
    ) -> list[str]:
        """Get trading rules for an agent. Includes defaults + user custom rules."""
        rules = list(DEFAULT_TRADING_RULES)

        r = aioredis.from_url(self._redis_url)
        try:
            # Load user-specific custom rules
            if user_id:
                custom_key = f"{_PREFIX}:rules:{user_id}"
                custom_raw = await r.lrange(custom_key, 0, -1)
                for raw in custom_raw:
                    rule = raw.decode() if isinstance(raw, bytes) else raw
                    rules.append(rule)
        finally:
            await r.aclose()

        return rules

    async def get_safety_rules(self) -> list[str]:
        """Get safety rules (always returns built-in set)."""
        return list(SAFETY_RULES)

    async def get_agent_prompt(
        self,
        agent_id: str,
    ) -> str | None:
        """Get a custom system prompt override for an agent (if set at runtime)."""
        r = aioredis.from_url(self._redis_url)
        try:
            key = f"{_PREFIX}:prompt:{agent_id}"
            prompt = await r.get(key)
            if prompt:
                return prompt.decode() if isinstance(prompt, bytes) else prompt
            return None
        finally:
            await r.aclose()

    async def set_agent_prompt(
        self,
        agent_id: str,
        prompt: str,
    ) -> None:
        """Override an agent's system prompt at runtime."""
        r = aioredis.from_url(self._redis_url)
        try:
            key = f"{_PREFIX}:prompt:{agent_id}"
            await r.set(key, prompt)
            logger.info("Procedural memory: updated prompt for agent %s", agent_id)
        finally:
            await r.aclose()

    async def add_trading_rule(
        self,
        user_id: str,
        rule: str,
    ) -> int:
        """Add a custom trading rule for a user.

        Returns total number of custom rules.
        """
        r = aioredis.from_url(self._redis_url)
        try:
            key = f"{_PREFIX}:rules:{user_id}"
            count = await r.rpush(key, rule)
            logger.info("Procedural memory: added rule for user %s: %s", user_id, rule)
            return count
        finally:
            await r.aclose()

    async def remove_trading_rule(
        self,
        user_id: str,
        rule: str,
    ) -> bool:
        """Remove a custom trading rule for a user."""
        r = aioredis.from_url(self._redis_url)
        try:
            key = f"{_PREFIX}:rules:{user_id}"
            removed = await r.lrem(key, 1, rule)
            return removed > 0
        finally:
            await r.aclose()

    async def get_config(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get a procedural configuration value."""
        r = aioredis.from_url(self._redis_url)
        try:
            raw = await r.get(f"{_PREFIX}:config:{key}")
            if raw is None:
                return default
            val = raw.decode() if isinstance(raw, bytes) else raw
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return val
        finally:
            await r.aclose()

    async def set_config(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Set a procedural configuration value."""
        r = aioredis.from_url(self._redis_url)
        try:
            val = json.dumps(value) if not isinstance(value, str) else value
            await r.set(f"{_PREFIX}:config:{key}", val)
        finally:
            await r.aclose()

    def load_template(self, agent_id: str) -> str:
        """Load system prompt template from file system (L3 file-based)."""
        template_dir = Path(__file__).parent.parent / "agents" / "templates"
        template = template_dir / f"{agent_id}.txt"
        if template.exists():
            return template.read_text()
        return ""
