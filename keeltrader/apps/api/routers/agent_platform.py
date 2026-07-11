from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any, AsyncIterator, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from core.encryption import get_encryption_service
from domain.agent_platform.models import (
    AgentApproval, AgentArtifact, AgentDefinition, AgentMCPServer, AgentMemory, AgentMemoryVersion,
    AgentMessage, AgentModelProfile, AgentRun, AgentRunEvent, AgentRunStep, AgentSchedule, AgentSession,
    AgentToolGrant, AgentUsageLedger,
)
from domain.user.models import User
from services.agent_platform.mcp import call_tool, discover_tools, schema_digest
from services.agent_platform.network import validate_external_https_url
from services.agent_platform.runtime import TERMINAL, emit, enqueue_run, parse_mcp_tool, redact_sensitive
from services.tool_executor import execute_tool

router = APIRouter()
encryption = get_encryption_service()

BUILTIN_TOOLS = {
    "run_daily_brief", "deep_research", "record_investment_decision", "run_weekly_review",
    "query_tushare_data", "query_research_reports", "record_fundamental_validation",
}


def dump(model, *, secret_fields: set[str] | None = None) -> dict[str, Any]:
    secret_fields = secret_fields or set()
    result = {}
    for column in model.__table__.columns:
        if column.name in secret_fields:
            continue
        value = getattr(model, column.name)
        result[column.name] = value.isoformat() if isinstance(value, datetime) else str(value) if isinstance(value, UUID) else value
    return result


class ModelProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider: Literal["openai", "anthropic"]
    base_url: str | None = Field(default=None, max_length=500)
    model: str = Field(min_length=1, max_length=160)
    api_key: str = Field(min_length=8, max_length=1000)
    context_window: int = Field(ge=4096, le=2_000_000)
    max_output_tokens: int = Field(ge=256, le=200_000)
    input_cost_per_million: float = Field(ge=0, le=1000)
    output_cost_per_million: float = Field(ge=0, le=1000)


class DefinitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    system_prompt: str = Field(min_length=1, max_length=20000)
    role: str = Field(default="custom", max_length=50)
    model_profile_id: UUID
    tool_names: list[str] = Field(default_factory=list, max_length=50)
    memory_enabled: bool = True
    max_steps: int = Field(default=12, ge=1, le=20)
    max_parallel: int = Field(default=3, ge=1, le=5)
    task_token_budget: int = Field(default=50000, ge=1000, le=2_000_000)
    task_cost_budget_usd: float = Field(default=5, ge=.01, le=1000)


class RunCreate(BaseModel):
    agent_definition_id: UUID
    prompt: str = Field(min_length=1, max_length=20000)
    session_id: UUID | None = None


class ApprovalResolve(BaseModel):
    decision: Literal["approved", "rejected"]
    scope: Literal["once", "always"] = "once"
    reason: str | None = Field(default=None, max_length=1000)


class RunBudgetUpdate(BaseModel):
    token_budget: int = Field(ge=1000, le=2_000_000)
    cost_budget_usd: float = Field(ge=.01, le=1000)


class MemoryUpdate(BaseModel):
    value: Any
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    confidence: float = Field(default=.5, ge=0, le=1)


class MCPCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=500)
    auth_token: str | None = Field(default=None, max_length=2000)


class ScheduleCreate(BaseModel):
    agent_definition_id: UUID
    name: str = Field(min_length=1, max_length=160)
    prompt: str = Field(min_length=1, max_length=20000)
    cron: str = Field(pattern=r"^[0-9*,-/]+ [0-9*,-/]+ [0-9*,-/]+ [0-9*,-/]+ [0-9*,-/]+$")
    timezone: str = Field(default="Asia/Shanghai", max_length=80)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "agent-platform", "mode": "research-only"}


@router.post("/model-credentials")
async def create_model(req: ModelProfileCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    if req.base_url:
        validate_external_https_url(req.base_url)
    item = AgentModelProfile(user_id=user.id, name=req.name, provider=req.provider, base_url=req.base_url,
                             model=req.model, api_key_encrypted=encryption.encrypt(req.api_key),
                             key_prefix=req.api_key[:6], context_window=req.context_window,
                             max_output_tokens=req.max_output_tokens,
                             input_cost_per_million=req.input_cost_per_million,
                             output_cost_per_million=req.output_cost_per_million)
    session.add(item)
    await session.flush()
    return dump(item, secret_fields={"api_key_encrypted"})


@router.get("/model-credentials")
async def list_models(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    items = (await session.execute(select(AgentModelProfile).where(AgentModelProfile.user_id == user.id)
                                   .order_by(desc(AgentModelProfile.created_at)))).scalars().all()
    return {"items": [dump(item, secret_fields={"api_key_encrypted"}) for item in items]}


@router.delete("/model-credentials/{item_id}")
async def delete_model(item_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentModelProfile, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Model profile not found")
    item.is_active = False
    return {"ok": True}


@router.post("/definitions")
async def create_definition(req: DefinitionCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    profile = await session.get(AgentModelProfile, req.model_profile_id)
    if not profile or profile.user_id != user.id or not profile.is_active:
        raise HTTPException(400, "Invalid model profile")
    unknown = set(req.tool_names) - BUILTIN_TOOLS
    for name in unknown:
        mcp_ref = parse_mcp_tool(name)
        if not mcp_ref:
            raise HTTPException(400, f"Unknown or forbidden tool: {name}")
        server = await session.get(AgentMCPServer, mcp_ref[0])
        if not server or server.user_id != user.id or server.status != "active" or mcp_ref[1] not in {t["name"] for t in server.tools_snapshot or []}:
            raise HTTPException(400, f"Unavailable MCP tool: {name}")
    item = AgentDefinition(user_id=user.id, **req.model_dump())
    session.add(item)
    await session.flush()
    return dump(item)


@router.get("/definitions")
async def list_definitions(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    items = (await session.execute(select(AgentDefinition).where(AgentDefinition.user_id == user.id,
                                                                  AgentDefinition.is_active.is_(True))
                                   .order_by(desc(AgentDefinition.created_at)))).scalars().all()
    servers = (await session.execute(select(AgentMCPServer).where(AgentMCPServer.user_id == user.id,
                                                                  AgentMCPServer.status == "active"))).scalars().all()
    mcp_tools = [{"name": f"mcp:{server.id}:{tool['name']}", "server": server.name,
                  "description": tool.get("description") or ""}
                 for server in servers for tool in (server.tools_snapshot or [])]
    return {"items": [dump(item) for item in items], "builtin_tools": sorted(BUILTIN_TOOLS), "mcp_tools": mcp_tools}


@router.post("/runs")
async def create_run(req: RunCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    agent = await session.get(AgentDefinition, req.agent_definition_id)
    if not agent or agent.user_id != user.id or not agent.is_active:
        raise HTTPException(404, "Agent not found")
    try:
        run = await enqueue_run(session, user.id, agent, req.prompt, req.session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return dump(run)


@router.get("/runs")
async def list_runs(limit: int = Query(30, ge=1, le=100), session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    items = (await session.execute(select(AgentRun).where(AgentRun.user_id == user.id)
                                   .order_by(desc(AgentRun.created_at)).limit(limit))).scalars().all()
    return {"items": [dump(item) for item in items]}


@router.get("/runs/{run_id}")
async def get_run(run_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentRun, run_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Run not found")
    artifacts = (await session.execute(select(AgentArtifact).where(AgentArtifact.run_id == run_id))).scalars().all()
    return {"run": dump(item), "artifacts": [dump(a) for a in artifacts]}


async def _control_run(run_id: UUID, action: Literal["pause", "resume", "cancel"], session: AsyncSession, user: User):
    run = await session.get(AgentRun, run_id)
    if not run or run.user_id != user.id:
        raise HTTPException(404, "Run not found")
    if run.status in TERMINAL:
        raise HTTPException(409, "Run is already terminal")
    run.status = {"pause": "paused", "resume": "running", "cancel": "cancelled"}[action]
    if action == "resume":
        run.lease_expires_at = None
    if action == "cancel":
        run.finished_at = datetime.now(UTC)
    await emit(session, run.id, f"run.{action}", {})
    return dump(run)


@router.post("/runs/{run_id}/pause")
async def pause_run(run_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _control_run(run_id, "pause", session, user)


@router.post("/runs/{run_id}/resume")
async def resume_run(run_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _control_run(run_id, "resume", session, user)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _control_run(run_id, "cancel", session, user)


@router.post("/runs/{run_id}/budget")
async def update_run_budget(run_id: UUID, req: RunBudgetUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    run = await session.get(AgentRun, run_id)
    if not run or run.user_id != user.id:
        raise HTTPException(404, "Run not found")
    run.token_budget, run.cost_budget_usd = req.token_budget, req.cost_budget_usd
    if run.status == "paused_budget":
        run.status, run.lease_expires_at = "running", None
        await emit(session, run.id, "run.budget_extended", req.model_dump())
    return dump(run)


async def _event_stream(run_id: UUID, user_id: UUID, cursor: int) -> AsyncIterator[str]:
    from core.database import async_session
    last = cursor
    while True:
        async with async_session() as db:
            run = await db.get(AgentRun, run_id)
            if not run or run.user_id != user_id:
                yield "event: error\ndata: {\"detail\":\"not found\"}\n\n"
                return
            events = (await db.execute(select(AgentRunEvent).where(AgentRunEvent.run_id == run_id,
                                                                   AgentRunEvent.id > last)
                                       .order_by(AgentRunEvent.id).limit(100))).scalars().all()
            for item in events:
                last = item.id
                yield f"id: {item.id}\nevent: {item.event_type}\ndata: {json.dumps(item.payload)}\n\n"
            if run.status in TERMINAL and not events:
                return
        yield ": keepalive\n\n"
        await asyncio.sleep(1)


@router.get("/runs/{run_id}/events")
async def run_events(run_id: UUID, cursor: int = Query(0, ge=0), user: User = Depends(get_current_user)):
    return StreamingResponse(_event_stream(run_id, user.id, cursor), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/sessions")
async def list_sessions(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    items = (await session.execute(select(AgentSession).where(AgentSession.user_id == user.id)
                                   .order_by(desc(AgentSession.updated_at)).limit(100))).scalars().all()
    return {"items": [dump(item) for item in items]}


@router.get("/sessions/{session_id}/messages")
async def session_messages(session_id: UUID, before: datetime | None = None, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentSession, session_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Session not found")
    stmt = select(AgentMessage).where(AgentMessage.session_id == session_id)
    if before:
        stmt = stmt.where(AgentMessage.created_at < before)
    messages = (await session.execute(stmt.order_by(desc(AgentMessage.created_at)).limit(100))).scalars().all()
    return {"items": [dump(m) for m in reversed(messages)]}


@router.get("/approvals")
async def approvals(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    items = (await session.execute(select(AgentApproval).where(AgentApproval.user_id == user.id,
                                                               AgentApproval.status == "pending")
                                   .order_by(AgentApproval.created_at))).scalars().all()
    return {"items": [dump(item) for item in items]}


@router.post("/approvals/{approval_id}/resolve")
async def resolve_approval(approval_id: UUID, req: ApprovalResolve, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentApproval, approval_id)
    if not item or item.user_id != user.id or item.status != "pending":
        raise HTTPException(404, "Approval not found")
    item.status, item.decision_scope, item.reason, item.resolved_at = req.decision, req.scope, req.reason, datetime.now(UTC)
    run = await session.get(AgentRun, item.run_id)
    if req.decision == "approved":
        step = await session.get(AgentRunStep, item.step_id)
        mcp_ref = parse_mcp_tool(step.tool_name or "")
        if item.kind == "mcp_tool" and mcp_ref:
            server = await session.get(AgentMCPServer, mcp_ref[0])
            if not server or server.user_id != user.id or server.status != "active":
                raise HTTPException(409, "MCP server is unavailable")
            result = await call_tool(server, mcp_ref[1], step.input_json or {})
            if req.scope == "always":
                session.add(AgentToolGrant(user_id=user.id, agent_definition_id=run.agent_definition_id,
                                           mcp_server_id=server.id, tool_name=mcp_ref[1], scope="always",
                                           schema_digest=server.schema_digest or ""))
        else:
            result = await execute_tool(step.tool_name or "", step.input_json or {}, session, user.id)
        if result.get("error"):
            raise HTTPException(502, result["error"])
        step.output_json, step.status, step.finished_at = redact_sensitive(result), "completed", datetime.now(UTC)
        run.status, run.lease_expires_at = "running", None
    else:
        run.status, run.finished_at = "cancelled", datetime.now(UTC)
    await emit(session, run.id, "approval.resolved", {"approval_id": str(item.id), "decision": req.decision})
    return dump(item)


@router.get("/memories")
async def memories(include_deleted: bool = False, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    stmt = select(AgentMemory).where(AgentMemory.user_id == user.id)
    if not include_deleted:
        stmt = stmt.where(AgentMemory.is_deleted.is_(False))
    items = (await session.execute(stmt.order_by(desc(AgentMemory.updated_at)).limit(200))).scalars().all()
    return {"items": [dump(item) for item in items]}


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentMemory, memory_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Memory not found")
    item.is_deleted = True
    return {"ok": True}


@router.patch("/memories/{memory_id}")
async def update_memory(memory_id: UUID, req: MemoryUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentMemory, memory_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Memory not found")
    item.version += 1
    item.value, item.evidence, item.confidence, item.is_deleted = req.value, req.evidence, req.confidence, False
    session.add(AgentMemoryVersion(memory_id=item.id, version=item.version, value=item.value, evidence=item.evidence))
    return dump(item)


@router.post("/memories/{memory_id}/restore")
async def restore_memory(memory_id: UUID, version: int | None = None, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentMemory, memory_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Memory not found")
    if version is not None:
        previous = (await session.execute(select(AgentMemoryVersion).where(AgentMemoryVersion.memory_id == memory_id,
                                                                           AgentMemoryVersion.version == version))).scalar_one_or_none()
        if not previous:
            raise HTTPException(404, "Memory version not found")
        item.version += 1
        item.value, item.evidence = previous.value, previous.evidence
        session.add(AgentMemoryVersion(memory_id=item.id, version=item.version, value=item.value, evidence=item.evidence))
    item.is_deleted = False
    return dump(item)


@router.post("/mcp-servers")
async def create_mcp(req: MCPCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    url = validate_external_https_url(req.url)
    item = AgentMCPServer(user_id=user.id, name=req.name, url=url,
                          auth_encrypted=encryption.encrypt(req.auth_token) if req.auth_token else None,
                          auth_prefix=req.auth_token[:6] if req.auth_token else None)
    session.add(item)
    await session.flush()
    try:
        tools = await discover_tools(item)
        item.tools_snapshot, item.schema_digest, item.status = tools, schema_digest(tools), "active"
        item.last_checked_at = datetime.now(UTC)
    except Exception as exc:
        item.status = "error"
        raise HTTPException(502, f"MCP discovery failed: {str(exc)[:200]}") from exc
    return dump(item, secret_fields={"auth_encrypted"})


@router.get("/mcp-servers")
async def list_mcp(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    items = (await session.execute(select(AgentMCPServer).where(AgentMCPServer.user_id == user.id)
                                   .order_by(desc(AgentMCPServer.created_at)))).scalars().all()
    return {"items": [dump(item, secret_fields={"auth_encrypted"}) for item in items]}


def next_daily_run(cron: str) -> datetime:
    minute, hour, *_ = cron.split()
    if not minute.isdigit() or not hour.isdigit():
        raise HTTPException(400, "Initial release supports fixed minute/hour cron schedules")
    now = datetime.now(UTC)
    candidate = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)


@router.post("/schedules")
async def create_schedule(req: ScheduleCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    agent = await session.get(AgentDefinition, req.agent_definition_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(404, "Agent not found")
    item = AgentSchedule(user_id=user.id, next_run_at=next_daily_run(req.cron), **req.model_dump())
    session.add(item)
    await session.flush()
    return dump(item)


@router.get("/schedules")
async def list_schedules(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    items = (await session.execute(select(AgentSchedule).where(AgentSchedule.user_id == user.id)
                                   .order_by(AgentSchedule.created_at))).scalars().all()
    return {"items": [dump(item) for item in items]}


@router.get("/usage")
async def usage(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    since = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    row = (await session.execute(select(
        func.coalesce(func.sum(AgentUsageLedger.input_tokens), 0),
        func.coalesce(func.sum(AgentUsageLedger.output_tokens), 0),
        func.coalesce(func.sum(AgentUsageLedger.cost_usd), 0.0),
    ).where(AgentUsageLedger.user_id == user.id, AgentUsageLedger.created_at >= since))).one()
    return {"today": {"input_tokens": int(row[0]), "output_tokens": int(row[1]), "cost_usd": float(row[2])},
            "limits": {"tokens": 200000, "cost_usd": 20.0}}
