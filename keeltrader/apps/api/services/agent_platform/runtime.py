from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from core.encryption import get_encryption_service
from domain.agent_platform.models import (
    AgentApproval, AgentArtifact, AgentDefinition, AgentMCPServer, AgentMemory, AgentMemoryVersion,
    AgentMessage, AgentModelProfile, AgentRun, AgentRunEvent, AgentRunStep, AgentSchedule, AgentSession,
    AgentToolGrant, AgentUsageLedger,
)
from services.agent_platform.mcp import call_tool
from services.tool_executor import execute_tool
from services.tool_definitions import TOOL_DEFINITIONS

TERMINAL = {"completed", "failed", "cancelled"}
RUNNABLE = {"queued", "running"}
SENSITIVE_MARKERS = ("token", "secret", "password", "authorization", "api_key", "apikey")


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "<redacted>" if any(marker in str(key).lower() for marker in SENSITIVE_MARKERS)
                else redact_sensitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


async def emit(session: AsyncSession, run_id: UUID, event_type: str, payload: dict[str, Any] | None = None) -> None:
    session.add(AgentRunEvent(run_id=run_id, event_type=event_type, payload=payload or {}))


def default_plan(prompt: str, tool_names: list[str] | None = None) -> list[dict[str, Any]]:
    allowed = set(tool_names or ["query_research_reports"])
    plan = []
    if "query_research_reports" in allowed:
        plan.append({"role": "report_researcher", "tool": "query_research_reports", "args": {"query": prompt, "top_k": 5}})
    plan.extend([
        {"role": "fundamental_analyst", "tool": None, "args": {}},
        {"role": "red_team", "tool": None, "args": {}},
        {"role": "risk_reviewer", "tool": None, "args": {}},
        {"role": "coordinator", "tool": None, "args": {}},
    ])
    return plan


def parse_mcp_tool(name: str) -> tuple[UUID, str] | None:
    if not name.startswith("mcp:"):
        return None
    try:
        _, server_id, tool_name = name.split(":", 2)
        return UUID(server_id), tool_name
    except (ValueError, TypeError):
        return None


async def enqueue_run(session: AsyncSession, user_id: UUID, agent: AgentDefinition, prompt: str,
                      session_id: UUID | None = None) -> AgentRun:
    chat = None
    if session_id:
        chat = await session.get(AgentSession, session_id)
        if not chat or chat.user_id != user_id:
            raise ValueError("Session not found")
    if chat is None:
        chat = AgentSession(user_id=user_id, agent_definition_id=agent.id, title=prompt[:120])
        session.add(chat)
        await session.flush()
    session.add(AgentMessage(session_id=chat.id, role="user", content=prompt))
    run = AgentRun(
        user_id=user_id, session_id=chat.id, agent_definition_id=agent.id, prompt=prompt,
        token_budget=agent.task_token_budget, cost_budget_usd=agent.task_cost_budget_usd,
    )
    session.add(run)
    await session.flush()
    await emit(session, run.id, "run.queued", {"prompt_length": len(prompt)})
    return run


async def claim_run(session: AsyncSession, worker_id: str) -> AgentRun | None:
    now = datetime.now(UTC)
    stmt = (
        select(AgentRun).where(
            AgentRun.status.in_(RUNNABLE),
            or_(AgentRun.lease_expires_at.is_(None), AgentRun.lease_expires_at < now),
        ).order_by(AgentRun.created_at).with_for_update(skip_locked=True).limit(1)
    )
    run = (await session.execute(stmt)).scalar_one_or_none()
    if not run:
        return None
    run.lease_owner = worker_id
    run.lease_expires_at = now + timedelta(seconds=90)
    if run.status == "queued":
        run.status = "planning"
        run.started_at = now
    await session.flush()
    return run


async def dispatch_due_schedules(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    schedules = (await session.execute(
        select(AgentSchedule).where(AgentSchedule.enabled.is_(True), AgentSchedule.next_run_at <= now)
        .with_for_update(skip_locked=True).limit(20)
    )).scalars().all()
    count = 0
    for item in schedules:
        agent = await session.get(AgentDefinition, item.agent_definition_id)
        if not agent or not agent.is_active:
            item.enabled = False
            continue
        await enqueue_run(session, item.user_id, agent, item.prompt)
        item.last_run_at = now
        item.next_run_at = item.next_run_at + timedelta(days=1)
        count += 1
    return count


async def _daily_usage(session: AsyncSession, user_id: UUID) -> tuple[int, float]:
    since = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    row = (await session.execute(
        select(func.coalesce(func.sum(AgentUsageLedger.input_tokens + AgentUsageLedger.output_tokens), 0),
               func.coalesce(func.sum(AgentUsageLedger.cost_usd), 0.0))
        .where(AgentUsageLedger.user_id == user_id, AgentUsageLedger.created_at >= since)
    )).one()
    return int(row[0]), float(row[1])


async def _model_text(profile: AgentModelProfile, system: str, messages: list[dict[str, str]]) -> tuple[str, int, int]:
    key = get_encryption_service().decrypt(profile.api_key_encrypted)
    if profile.provider == "anthropic":
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=key, base_url=profile.base_url or None)
        response = await client.messages.create(model=profile.model, system=system, messages=messages,
                                                max_tokens=profile.max_output_tokens)
        text = "".join(getattr(block, "text", "") for block in response.content)
        return text, int(response.usage.input_tokens), int(response.usage.output_tokens)
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=key, base_url=profile.base_url or None)
    response = await client.chat.completions.create(
        model=profile.model, messages=[{"role": "system", "content": system}, *messages],
        max_tokens=profile.max_output_tokens,
    )
    usage = response.usage
    return response.choices[0].message.content or "", int(usage.prompt_tokens or 0), int(usage.completion_tokens or 0)


async def _record_usage(session: AsyncSession, run: AgentRun, profile: AgentModelProfile,
                        input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens * profile.input_cost_per_million + output_tokens * profile.output_cost_per_million) / 1_000_000
    run.tokens_used += input_tokens + output_tokens
    run.cost_used_usd += cost
    session.add(AgentUsageLedger(user_id=run.user_id, run_id=run.id, model_profile_id=profile.id,
                                 input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost))
    return cost


async def _generate_plan(session: AsyncSession, run: AgentRun, agent: AgentDefinition,
                         profile: AgentModelProfile) -> list[dict[str, Any]]:
    allowed = set(agent.tool_names or [])
    schemas: list[dict[str, Any]] = [
        {"name": item["name"], "description": item["description"], "parameters": item["parameters"]}
        for item in TOOL_DEFINITIONS if item["name"] in allowed
    ]
    for name in sorted(allowed):
        ref = parse_mcp_tool(name)
        if not ref:
            continue
        server = await session.get(AgentMCPServer, ref[0])
        if not server or server.user_id != run.user_id or server.status != "active":
            continue
        tool = next((item for item in server.tools_snapshot or [] if item["name"] == ref[1]), None)
        if tool:
            schemas.append({"name": name, "description": tool.get("description") or "External MCP tool",
                            "parameters": tool.get("inputSchema") or {"type": "object"}})
    instruction = (
        "Return only a JSON array of at most %d research steps. Each item must have role, tool, args. "
        "tool must be null or exactly one of the supplied tool names. Use external tools only when needed. "
        "Never plan orders, trades, code execution, or credential access. End with analyst, red_team, "
        "risk_reviewer, and coordinator synthesis steps using tool=null.\nTools: %s"
    ) % (min(agent.max_steps, 20), json.dumps(schemas, ensure_ascii=False))
    text, input_tokens, output_tokens = await _model_text(
        profile, instruction, [{"role": "user", "content": run.prompt}],
    )
    await _record_usage(session, run, profile, input_tokens, output_tokens)
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        raw = json.loads(cleaned)
    except json.JSONDecodeError:
        return default_plan(run.prompt, agent.tool_names or [])
    plan: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw[: min(agent.max_steps, 20)]:
            if not isinstance(item, dict):
                continue
            tool = item.get("tool")
            if tool is not None and tool not in allowed:
                continue
            role = str(item.get("role") or "researcher")[:50]
            args = item.get("args") if isinstance(item.get("args"), dict) else {}
            plan.append({"role": role, "tool": tool, "args": args})
    return plan or default_plan(run.prompt, agent.tool_names or [])


async def execute_claimed_run(session: AsyncSession, run: AgentRun) -> None:
    agent = await session.get(AgentDefinition, run.agent_definition_id)
    profile = await session.get(AgentModelProfile, agent.model_profile_id) if agent and agent.model_profile_id else None
    if not agent or not profile or profile.user_id != run.user_id:
        run.status, run.error = "failed", "Agent model profile is not configured"
        run.finished_at = datetime.now(UTC)
        await emit(session, run.id, "run.failed", {"reason": run.error})
        return
    if not run.plan:
        run.plan = await _generate_plan(session, run, agent, profile)
        for seq, item in enumerate(run.plan):
            session.add(AgentRunStep(run_id=run.id, sequence=seq, agent_role=item["role"], tool_name=item.get("tool"),
                                     input_json=item.get("args") or {}, idempotency_key=f"{run.id}:{seq}"))
        run.status = "running"
        await emit(session, run.id, "run.planned", {"steps": len(run.plan)})
        await session.flush()
    steps = (await session.execute(select(AgentRunStep).where(AgentRunStep.run_id == run.id)
                                   .order_by(AgentRunStep.sequence))).scalars().all()
    outputs: list[dict[str, Any]] = list((run.checkpoint or {}).get("outputs") or [])
    for step in steps:
        if step.status == "completed":
            continue
        if run.tokens_used >= run.token_budget or run.cost_used_usd >= run.cost_budget_usd:
            run.status = "paused_budget"
            await emit(session, run.id, "run.paused_budget", {})
            return
        daily_tokens, daily_cost = await _daily_usage(session, run.user_id)
        if daily_tokens >= 200000 or daily_cost >= 20:
            run.status = "paused_budget"
            await emit(session, run.id, "run.paused_budget", {"scope": "daily"})
            return
        step.status, step.started_at, step.attempts = "running", datetime.now(UTC), step.attempts + 1
        await emit(session, run.id, "step.started", {"step_id": str(step.id), "role": step.agent_role, "tool": step.tool_name})
        await session.flush()
        try:
            if step.tool_name:
                if step.tool_name not in set(agent.tool_names or []):
                    raise RuntimeError("Tool is not allowed for this agent")
                if step.tool_name == "record_investment_decision":
                    approval = AgentApproval(user_id=run.user_id, run_id=run.id, step_id=step.id,
                                             kind="decision_log", preview=step.input_json)
                    session.add(approval)
                    step.status, run.status = "waiting_approval", "waiting_approval"
                    await emit(session, run.id, "approval.required", {"approval_id": str(approval.id)})
                    return
                mcp_ref = parse_mcp_tool(step.tool_name)
                if mcp_ref:
                    server_id, tool_name = mcp_ref
                    server = await session.get(AgentMCPServer, server_id)
                    if not server or server.user_id != run.user_id or server.status != "active":
                        raise RuntimeError("MCP server is unavailable")
                    grant = (await session.execute(select(AgentToolGrant).where(
                        AgentToolGrant.user_id == run.user_id,
                        AgentToolGrant.mcp_server_id == server.id,
                        AgentToolGrant.tool_name == tool_name,
                        AgentToolGrant.schema_digest == server.schema_digest,
                        or_(AgentToolGrant.agent_definition_id.is_(None), AgentToolGrant.agent_definition_id == agent.id),
                    ))).scalar_one_or_none()
                    if not grant:
                        approval = AgentApproval(
                            user_id=run.user_id, run_id=run.id, step_id=step.id, kind="mcp_tool",
                            preview={"server": server.name, "url": server.url, "tool": tool_name,
                                     "arguments": redact_sensitive(step.input_json), "schema_digest": server.schema_digest},
                        )
                        session.add(approval)
                        step.status, run.status = "waiting_approval", "waiting_approval"
                        await session.flush()
                        await emit(session, run.id, "approval.required", {"approval_id": str(approval.id)})
                        return
                    result = await call_tool(server, tool_name, step.input_json)
                else:
                    result = await execute_tool(step.tool_name, step.input_json, session, run.user_id)
                if result.get("error"):
                    raise RuntimeError(result["error"])
                output = redact_sensitive(result)
            else:
                prompt = json.dumps(outputs[-4:], ensure_ascii=False, default=str)
                output_text, input_tokens, output_tokens = await _model_text(
                    profile,
                    agent.system_prompt + "\nYou are the " + step.agent_role + ". Research only; never place trades.",
                    [{"role": "user", "content": f"Task: {run.prompt}\nEvidence: {prompt}"}],
                )
                await _record_usage(session, run, profile, input_tokens, output_tokens)
                output = {"role": step.agent_role, "text": output_text}
            step.output_json, step.status, step.finished_at = output, "completed", datetime.now(UTC)
            outputs.append(output)
            run.current_step = step.sequence + 1
            run.checkpoint = {"outputs": outputs, "last_step": step.sequence}
            await emit(session, run.id, "step.completed", {"step_id": str(step.id)})
            await session.flush()
        except Exception as exc:
            step.error = str(exc)[:1000]
            if step.attempts < 2:
                step.status = "pending"
                await emit(session, run.id, "step.retry", {"step_id": str(step.id)})
                return
            step.status, run.status, run.error = "failed", "failed", step.error
            run.finished_at = datetime.now(UTC)
            await emit(session, run.id, "run.failed", {"reason": step.error})
            return
    final = outputs[-1] if outputs else {"text": "No output"}
    session.add(AgentArtifact(user_id=run.user_id, run_id=run.id, artifact_type="research",
                              title=run.prompt[:200], content={"result": final, "evidence": outputs[:-1]}))
    session.add(AgentMessage(session_id=run.session_id, role="assistant",
                             content=str(final.get("text") or json.dumps(final, ensure_ascii=False))))
    chat = await session.get(AgentSession, run.session_id)
    if chat:
        chat.context_tokens += run.tokens_used
        if chat.context_tokens >= int(profile.context_window * .7):
            chat.summary = str(final.get("text") or json.dumps(final, ensure_ascii=False))[:12000]
            chat.context_tokens = min(run.tokens_used, profile.max_output_tokens)
    if agent.memory_enabled:
        memory = AgentMemory(user_id=run.user_id, agent_definition_id=agent.id,
                             key=f"run:{run.id}", value={"summary": final},
                             evidence=[{"run_id": str(run.id)}], confidence=.6)
        session.add(memory)
        await session.flush()
        session.add(AgentMemoryVersion(memory_id=memory.id, version=1, value=memory.value, evidence=memory.evidence))
    run.status, run.finished_at, run.lease_expires_at = "completed", datetime.now(UTC), None
    await emit(session, run.id, "run.completed", {"artifact_type": "research"})


async def worker_loop() -> None:
    worker_id = f"{os.uname().nodename}:{os.getpid()}:{uuid4().hex[:8]}"
    while True:
        try:
            async with async_session() as session:
                async with session.begin():
                    await dispatch_due_schedules(session)
                    run = await claim_run(session, worker_id)
                if run:
                    async with session.begin():
                        run = await session.get(AgentRun, run.id, with_for_update=True)
                        await execute_claimed_run(session, run)
                    continue
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(2)
        await asyncio.sleep(1)
