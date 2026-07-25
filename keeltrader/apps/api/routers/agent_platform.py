from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any, AsyncIterator, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.auth import get_current_user
from config import get_settings
from core.database import get_session
from core.encryption import get_encryption_service
from domain.agent_platform.models import (
    AgentApproval, AgentArtifact, AgentBackgroundJob, AgentCompanyDossier, AgentCompanyDossierVersion, AgentCompanyEvidence,
    AgentCompanyWatchlist, AgentDefinition, AgentHolderEvent, AgentHolderWatchlist, AgentMCPServer, AgentMemory, AgentMemoryVersion,
    AgentContextSnapshot, AgentMessage, AgentModelProfile, AgentRun, AgentRunEvent, AgentRunStep, AgentSchedule, AgentSession,
    AgentToolGrant, AgentUsageLedger,
)
from domain.file.models import UploadedFile
from domain.user.models import User
from services.agent_platform.mcp import call_tool, discover_tools, schema_digest
from services.agent_platform.network import validate_external_https_url
from services.agent_platform.runtime import TERMINAL, emit, enqueue_run, parse_mcp_tool, redact_sensitive
from services.agent_platform.tools import execute_platform_tool
from services.agent_platform.tushare import TushareReadService
from services.agent_platform.opportunities import OpportunityService, profile_payload
from services.agent_platform.search import global_search
from services.agent_platform.dossier import enqueue_dossier_refresh
from services.agent_platform.holders import enqueue_holder_scan, holder_names, normalize_holder_name
from services.agent_platform.learning import LearningBridge
from services.file_extractor import can_extract_text, extract_text
from services.storage_service import get_storage_provider

router = APIRouter()
encryption = get_encryption_service()

BUILTIN_TOOLS = {
    "run_daily_brief", "deep_research", "record_investment_decision", "run_weekly_review",
    "query_tushare_data", "query_research_reports", "record_fundamental_validation",
    "search_holder", "holder_positions", "holder_history", "market_capital_snapshot",
    "get_opportunity_snapshot", "get_company_dossier_version",
}

DEFAULT_AGENT_TOOLS = sorted(BUILTIN_TOOLS - {"record_investment_decision"})
DEFAULT_AGENT_NAME = "KeelTrader"
DEFAULT_AGENT_DESCRIPTION = "统一的只读投资研究助手"
DEFAULT_AGENT_ROLE = "research_assistant"
DEFAULT_AGENT_PROMPT = (
    "你是 KeelTrader，只读投资研究助手。所有结论必须区分事实、推断和不确定性，"
    "引用可核验证据，主动寻找反例与证伪条件，禁止执行交易。"
)


async def _ensure_managed_profile(session: AsyncSession) -> AgentModelProfile | None:
    settings = get_settings()
    if not settings.agent_managed_api_key or not settings.agent_managed_model:
        return None
    item = (await session.execute(select(AgentModelProfile).where(
        AgentModelProfile.managed_slug == "deployment-default",
    ))).scalar_one_or_none()
    if item is None:
        await session.execute(pg_insert(AgentModelProfile).values(
            id=uuid4(), user_id=None, name="部署默认模型", provider=settings.agent_managed_provider,
            base_url=settings.agent_managed_base_url, model=settings.agent_managed_model,
            api_key_encrypted=None, credential_source="managed", managed_slug="deployment-default",
            key_prefix=None, context_window=settings.agent_managed_context_window,
            max_output_tokens=settings.agent_managed_max_output_tokens,
            input_cost_per_million=0, output_cost_per_million=0, is_active=True,
        ).on_conflict_do_nothing())
        await session.flush()
        item = (await session.execute(select(AgentModelProfile).where(
            AgentModelProfile.managed_slug == "deployment-default",
        ))).scalar_one()
    else:
        item.provider = settings.agent_managed_provider
        item.base_url = settings.agent_managed_base_url
        item.model = settings.agent_managed_model
        item.context_window = settings.agent_managed_context_window
        item.max_output_tokens = settings.agent_managed_max_output_tokens
        item.is_active = True
    return item


async def _ensure_default_agent(session: AsyncSession, user: User,
                                preferred_profile: AgentModelProfile | None = None) -> AgentDefinition | None:
    existing = (await session.execute(select(AgentDefinition).where(
        AgentDefinition.user_id == user.id, AgentDefinition.is_default.is_(True),
        AgentDefinition.is_active.is_(True),
    ))).scalar_one_or_none()
    if existing:
        # The product exposes one KeelTrader assistant. Keep the persisted definition as
        # an implementation detail so historical sessions and foreign keys stay valid.
        existing.name = DEFAULT_AGENT_NAME
        existing.description = DEFAULT_AGENT_DESCRIPTION
        existing.role = DEFAULT_AGENT_ROLE
        existing.tool_names = DEFAULT_AGENT_TOOLS
        if preferred_profile is not None:
            existing.model_profile_id = preferred_profile.id
        return existing
    profile = preferred_profile or await _ensure_managed_profile(session)
    if profile is None:
        return None
    await session.execute(pg_insert(AgentDefinition).values(
        id=uuid4(), user_id=user.id, name=DEFAULT_AGENT_NAME, description=DEFAULT_AGENT_DESCRIPTION,
        system_prompt=DEFAULT_AGENT_PROMPT,
        role=DEFAULT_AGENT_ROLE, model_profile_id=profile.id, tool_names=DEFAULT_AGENT_TOOLS,
        memory_enabled=True, max_steps=12, max_parallel=3, task_token_budget=50000,
        task_cost_budget_usd=5, is_default=True, is_active=True,
    ).on_conflict_do_nothing())
    await session.flush()
    return (await session.execute(select(AgentDefinition).where(
        AgentDefinition.user_id == user.id, AgentDefinition.is_default.is_(True),
        AgentDefinition.is_active.is_(True),
    ))).scalar_one()


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


class SessionCreate(BaseModel):
    agent_definition_id: UUID
    title: str = Field(default="新会话", min_length=1, max_length=200)
    interaction_mode: Literal["ask", "research", "plan"] = "ask"
    company_code: str | None = Field(default=None, max_length=20)


class SessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    is_pinned: bool | None = None
    archived: bool | None = None
    interaction_mode: Literal["ask", "research", "plan"] | None = None
    company_code: str | None = Field(default=None, max_length=20)


class SessionMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    agent_definition_id: UUID | None = None
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=10)
    context_snapshot_ids: list[UUID] = Field(default_factory=list, max_length=10)
    client_request_id: UUID


class ContextSnapshotCreate(BaseModel):
    resource_type: Literal["macro", "futures", "options", "underlying", "capital", "rates", "opportunity", "trade_plan", "allocation_policy"]
    resource_id: str = Field(min_length=1, max_length=120)
    field: str | None = Field(default=None, max_length=80)
    visible_start: str | None = Field(default=None, max_length=32)
    visible_end: str | None = Field(default=None, max_length=32)
    selected_point: dict[str, Any] | None = None
    source: str = Field(min_length=1, max_length=240)
    methodology: str = Field(min_length=1, max_length=2000)


class WatchlistAdd(BaseModel):
    company: str = Field(min_length=1, max_length=120)


class HolderWatchAdd(BaseModel):
    holder_name: str = Field(min_length=1, max_length=500)
    holder_type: str = Field(default="未知", min_length=1, max_length=80)


class HolderWatchUpdate(BaseModel):
    aliases: list[str] | None = Field(default=None, max_length=20)
    enabled: bool | None = None


class HolderEventsRead(BaseModel):
    event_ids: list[UUID] = Field(default_factory=list, max_length=500)


class RiskProfileUpdate(BaseModel):
    account_equity: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=12)
    risk_per_trade: float | None = Field(default=None, gt=0, le=0.05)
    aggregate_open_risk: float | None = Field(default=None, gt=0, le=0.20)
    single_instrument_notional: float | None = Field(default=None, gt=0, le=1)
    derivative_premium_risk: float | None = Field(default=None, gt=0, le=0.05)
    max_leverage: float | None = Field(default=None, gt=0, le=5)


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


class LearningFeedbackCreate(BaseModel):
    message_id: UUID
    feedback: Literal["adopted", "rejected", "correction", "preference"]
    comment: str | None = Field(default=None, max_length=1000)


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
async def health(session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    now = datetime.now(UTC)
    queued = (await session.execute(select(
        func.count(), func.min(func.coalesce(AgentRun.heartbeat_at, AgentRun.created_at)),
    ).where(
        AgentRun.status.in_({"queued", "planning", "running"})
    ))).one()
    jobs = (await session.execute(select(func.count()).select_from(AgentBackgroundJob).where(
        AgentBackgroundJob.status.in_({"queued", "running", "retry"})
    ))).scalar_one()
    redis = aioredis.from_url(settings.redis_url)
    try:
        heartbeat = await redis.get("keeltrader:agent-platform:heartbeat")
    finally:
        await redis.aclose()
    oldest_age = (now - queued[1]).total_seconds() if queued[1] else 0
    healthy = bool(heartbeat) and oldest_age < 90
    return {"status": "ok" if healthy else "degraded", "service": "agent-platform", "mode": "research-only",
            "managed_model_available": bool(settings.agent_managed_api_key and settings.agent_managed_model),
            "worker_heartbeat": bool(heartbeat), "active_runs": int(queued[0]),
            "oldest_active_age_seconds": round(oldest_age, 1), "background_jobs": int(jobs)}


@router.post("/model-credentials")
async def create_model(req: ModelProfileCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    if req.base_url:
        validate_external_https_url(req.base_url)
    item = AgentModelProfile(user_id=user.id, name=req.name, provider=req.provider, base_url=req.base_url,
                             model=req.model, api_key_encrypted=encryption.encrypt(req.api_key),
                             credential_source="byok", managed_slug=None,
                             key_prefix=req.api_key[:6], context_window=req.context_window,
                             max_output_tokens=req.max_output_tokens,
                             input_cost_per_million=req.input_cost_per_million,
                             output_cost_per_million=req.output_cost_per_million)
    session.add(item)
    await session.flush()
    await _ensure_default_agent(session, user, preferred_profile=item)
    return dump(item, secret_fields={"api_key_encrypted"})


@router.get("/model-credentials")
async def list_models(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    await _ensure_managed_profile(session)
    items = (await session.execute(select(AgentModelProfile).where(
                                   or_(AgentModelProfile.user_id == user.id,
                                       AgentModelProfile.managed_slug == "deployment-default"))
                                   .order_by(desc(AgentModelProfile.created_at)))).scalars().all()
    return {"items": [dump(item, secret_fields={"api_key_encrypted"}) for item in items]}


@router.delete("/model-credentials/{item_id}")
async def delete_model(item_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentModelProfile, item_id)
    if not item or item.user_id != user.id or item.credential_source == "managed":
        raise HTTPException(404, "Model profile not found")
    default_agent = await _ensure_default_agent(session, user)
    if default_agent and default_agent.model_profile_id == item.id:
        fallback = await _ensure_managed_profile(session)
        if fallback is None:
            raise HTTPException(409, "Cannot remove the active model without a deployment default")
        default_agent.model_profile_id = fallback.id
    item.is_active = False
    return {"ok": True}


@router.post("/definitions")
async def create_definition(req: DefinitionCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    profile = await session.get(AgentModelProfile, req.model_profile_id)
    if not profile or (profile.user_id not in {None, user.id}) or not profile.is_active:
        raise HTTPException(400, "Invalid model profile")
    unknown = set(req.tool_names) - BUILTIN_TOOLS
    for name in unknown:
        mcp_ref = parse_mcp_tool(name)
        if not mcp_ref:
            raise HTTPException(400, f"Unknown or forbidden tool: {name}")
        server = await session.get(AgentMCPServer, mcp_ref[0])
        if not server or server.user_id != user.id or server.status != "active" or mcp_ref[1] not in {t["name"] for t in server.tools_snapshot or []}:
            raise HTTPException(400, f"Unavailable MCP tool: {name}")
    item = await _ensure_default_agent(session, user, preferred_profile=profile)
    if item is None:
        raise HTTPException(503, "KeelTrader model is not configured")
    item.system_prompt = req.system_prompt
    item.tool_names = req.tool_names
    item.memory_enabled = req.memory_enabled
    item.max_steps = req.max_steps
    item.max_parallel = req.max_parallel
    item.task_token_budget = req.task_token_budget
    item.task_cost_budget_usd = req.task_cost_budget_usd
    return dump(item)


@router.get("/definitions")
async def list_definitions(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    await _ensure_default_agent(session, user)
    items = (await session.execute(select(AgentDefinition).where(
        AgentDefinition.user_id == user.id,
        AgentDefinition.is_default.is_(True),
        AgentDefinition.is_active.is_(True),
    ))).scalars().all()
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
        run = await enqueue_run(session, user.id, agent, req.prompt, req.session_id,
                                None if req.session_id else "research")
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
        frames: list[str] = []
        terminal = False
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
                frames.append(f"id: {item.id}\nevent: {item.event_type}\ndata: {json.dumps(item.payload, default=str)}\n\n")
            terminal = run.status in TERMINAL and not events
            await db.rollback()
        for frame in frames:
            yield frame
        if terminal:
            return
        yield ": keepalive\n\n"
        await asyncio.sleep(1)


@router.get("/runs/{run_id}/events")
async def run_events(run_id: UUID, request: Request, cursor: int = Query(0, ge=0), user: User = Depends(get_current_user)):
    last_event_id = request.headers.get("last-event-id")
    if last_event_id and last_event_id.isdigit():
        cursor = max(cursor, int(last_event_id))
    return StreamingResponse(_event_stream(run_id, user.id, cursor), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/sessions")
async def list_sessions(include_archived: bool = False, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    stmt = select(AgentSession).where(AgentSession.user_id == user.id)
    if not include_archived:
        stmt = stmt.where(AgentSession.archived_at.is_(None))
    items = (await session.execute(stmt.order_by(desc(AgentSession.is_pinned),
                                                  desc(AgentSession.last_message_at)).limit(100))).scalars().all()
    return {"items": [dump(item) for item in items]}


@router.get("/companies")
async def search_companies(query: str = Query(default="", max_length=120), limit: int = Query(20, ge=1, le=50),
                           session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    del user
    return {"items": await TushareReadService(session).search_companies(query, limit)}


@router.get("/watchlist")
async def list_watchlist(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    items = (await session.execute(select(AgentCompanyWatchlist).where(
        AgentCompanyWatchlist.user_id == user.id,
    ).order_by(desc(AgentCompanyWatchlist.added_at)))).scalars().all()
    return {"items": [dump(item) for item in items]}


@router.post("/watchlist")
async def add_watchlist(req: WatchlistAdd, session: AsyncSession = Depends(get_session),
                        user: User = Depends(get_current_user)):
    profile = await TushareReadService(session).stock_profile(req.company.strip())
    if not profile or not profile.get("ts_code"):
        raise HTTPException(404, "A-share company not found")
    code = str(profile["ts_code"])
    item = (await session.execute(select(AgentCompanyWatchlist).where(
        AgentCompanyWatchlist.user_id == user.id,
        AgentCompanyWatchlist.company_code == code,
    ))).scalar_one_or_none()
    if item is None:
        item = AgentCompanyWatchlist(user_id=user.id, company_code=code,
                                     company_name=str(profile.get("name") or code),
                                     industry=profile.get("industry"), refresh_enabled=True)
        session.add(item)
        await session.flush()
    else:
        item.refresh_enabled = True
    await enqueue_dossier_refresh(session, user.id, code)
    return dump(item)


@router.delete("/watchlist/{company_code}")
async def remove_watchlist(company_code: str, session: AsyncSession = Depends(get_session),
                           user: User = Depends(get_current_user)):
    item = (await session.execute(select(AgentCompanyWatchlist).where(
        AgentCompanyWatchlist.user_id == user.id,
        AgentCompanyWatchlist.company_code == company_code,
    ))).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Watchlist company not found")
    await session.delete(item)
    return {"ok": True}


def holder_watch_dump(item: AgentHolderWatchlist) -> dict[str, Any]:
    result = dump(item)
    result["identity_warning"] = "自然人仅按披露姓名匹配，可能存在同名。" if item.holder_type == "自然人" else None
    return result


@router.get("/holders/search")
async def search_holders(
    query: str = Query(min_length=1, max_length=120),
    limit: int = Query(30, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    del user
    service = TushareReadService(session)
    items = await service.search_holders(query, limit)
    return {
        "items": [{
            **item,
            "identity_warning": "自然人仅按披露姓名匹配，可能存在同名。"
            if item.get("holder_type") == "自然人" else None,
        } for item in items],
        "source_available": await service.table_exists("top10_floatholders"),
    }


@router.get("/market-capital")
async def market_capital(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    del user
    return await TushareReadService(session).market_capital_snapshot()


@router.get("/macro-market")
async def macro_market(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    del user
    return await TushareReadService(session).macro_market_snapshot()


@router.get("/futures/products")
async def futures_products(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    del user
    return await TushareReadService(session).futures_products()


@router.get("/futures/{product_code}/history")
async def futures_history(product_code: str, session: AsyncSession = Depends(get_session),
                          user: User = Depends(get_current_user)):
    del user
    return await TushareReadService(session).futures_history(product_code)


@router.get("/futures/{product_code}/curve")
async def futures_curve(product_code: str, trade_date: date | None = Query(None),
                        session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    del user
    return await TushareReadService(session).futures_curve(product_code, trade_date)


@router.get("/options/series")
async def options_series(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    del user
    return await TushareReadService(session).options_series()


@router.get("/options/{opt_code}/history")
async def options_history(opt_code: str, session: AsyncSession = Depends(get_session),
                          user: User = Depends(get_current_user)):
    del user
    return await TushareReadService(session).options_history(opt_code)


@router.get("/options/{opt_code}/chain")
async def options_chain(opt_code: str, trade_date: date | None = Query(None), maturity: date | None = Query(None),
                        limit: int = Query(300, ge=1, le=500), offset: int = Query(0, ge=0),
                        session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    del user
    return await TushareReadService(session).options_chain(opt_code, trade_date, maturity, limit, offset)


@router.get("/holder-watchlist")
async def list_holder_watchlist(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    items = (await session.execute(select(AgentHolderWatchlist).where(
        AgentHolderWatchlist.user_id == user.id,
    ).order_by(desc(AgentHolderWatchlist.created_at)))).scalars().all()
    return {"items": [holder_watch_dump(item) for item in items]}


@router.post("/holder-watchlist")
async def add_holder_watch(
    req: HolderWatchAdd,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    name = normalize_holder_name(req.holder_name)
    holder_type = normalize_holder_name(req.holder_type) or "未知"
    candidates = await TushareReadService(session).search_holders(name, 50)
    exact = next((item for item in candidates if item.get("holder_name") == name
                  and item.get("holder_type") == holder_type), None)
    if not exact:
        raise HTTPException(404, "未找到该股东名称与类型的精确披露记录")
    item = (await session.execute(select(AgentHolderWatchlist).where(
        AgentHolderWatchlist.user_id == user.id,
        AgentHolderWatchlist.normalized_name == normalize_holder_name(name),
        AgentHolderWatchlist.holder_type == holder_type,
    ))).scalar_one_or_none()
    if item is None:
        item = AgentHolderWatchlist(
            user_id=user.id, holder_name=name, normalized_name=normalize_holder_name(name),
            holder_type=holder_type, aliases=[], enabled=True,
        )
        session.add(item)
        await session.flush()
        await enqueue_holder_scan(session, user.id, item.id, initial=True)
    else:
        item.enabled = True
        await enqueue_holder_scan(session, user.id, item.id)
    return holder_watch_dump(item)


async def owned_holder_watch(session: AsyncSession, user_id, watch_id: UUID) -> AgentHolderWatchlist:
    item = await session.get(AgentHolderWatchlist, watch_id)
    if not item or item.user_id != user_id:
        raise HTTPException(404, "关注股东不存在")
    return item


@router.patch("/holder-watchlist/{watch_id}")
async def update_holder_watch(
    watch_id: UUID,
    req: HolderWatchUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = await owned_holder_watch(session, user.id, watch_id)
    if req.aliases is not None:
        aliases: list[str] = []
        seen = {item.holder_name}
        for raw in req.aliases:
            alias = normalize_holder_name(raw)
            if alias and alias not in seen:
                aliases.append(alias)
                seen.add(alias)
        item.aliases = aliases
    if req.enabled is not None:
        item.enabled = req.enabled
    if item.enabled:
        await enqueue_holder_scan(session, user.id, item.id)
    return holder_watch_dump(item)


@router.delete("/holder-watchlist/{watch_id}")
async def delete_holder_watch(
    watch_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = await owned_holder_watch(session, user.id, watch_id)
    await session.delete(item)
    return {"ok": True}


@router.post("/holder-watchlist/{watch_id}/refresh")
async def refresh_holder_watch(
    watch_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = await owned_holder_watch(session, user.id, watch_id)
    await enqueue_holder_scan(session, user.id, item.id)
    return {"ok": True, "status": "queued"}


@router.get("/holders/{watch_id}/positions")
async def holder_positions(
    watch_id: UUID,
    view: Literal["latest", "history"] = "latest",
    all_history: bool = False,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = await owned_holder_watch(session, user.id, watch_id)
    service = TushareReadService(session)
    if view == "history":
        min_end_date = None if all_history else (datetime.now(UTC) - timedelta(days=820)).strftime("%Y%m%d")
        result = await service.holder_history(
            holder_names(item), item.holder_type, limit=limit, offset=offset,
            min_end_date=min_end_date,
        )
    else:
        result = await service.holder_current_positions(holder_names(item), item.holder_type, limit=limit, offset=offset)
    return {**result, "watch": holder_watch_dump(item)}


@router.get("/holder-events")
async def holder_events(
    unread_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(AgentHolderEvent).where(AgentHolderEvent.user_id == user.id)
    if unread_only:
        stmt = stmt.where(AgentHolderEvent.read_at.is_(None))
    items = (await session.execute(stmt.order_by(
        desc(AgentHolderEvent.end_date), desc(AgentHolderEvent.detected_at)
    ).limit(limit))).scalars().all()
    unread = (await session.execute(select(func.count()).select_from(AgentHolderEvent).where(
        AgentHolderEvent.user_id == user.id, AgentHolderEvent.read_at.is_(None),
    ))).scalar_one()
    return {"items": [dump(item) for item in items], "unread": int(unread)}


@router.post("/holder-events/read")
async def read_holder_events(
    req: HolderEventsRead,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(AgentHolderEvent).where(AgentHolderEvent.user_id == user.id)
    if req.event_ids:
        stmt = stmt.where(AgentHolderEvent.id.in_(req.event_ids))
    items = (await session.execute(stmt)).scalars().all()
    now = datetime.now(UTC)
    for item in items:
        item.read_at = now
    return {"ok": True, "updated": len(items)}


@router.get("/dossiers/{company_code}")
async def get_dossier(company_code: str, session: AsyncSession = Depends(get_session),
                      user: User = Depends(get_current_user)):
    dossier = (await session.execute(select(AgentCompanyDossier).where(
        AgentCompanyDossier.user_id == user.id, AgentCompanyDossier.company_code == company_code,
    ))).scalar_one_or_none()
    if not dossier:
        return {"status": "pending", "company_code": company_code, "snapshot": None, "evidence": [], "versions": []}
    versions = (await session.execute(select(AgentCompanyDossierVersion).where(
        AgentCompanyDossierVersion.dossier_id == dossier.id).order_by(desc(AgentCompanyDossierVersion.version))
    )).scalars().all()
    current = versions[0] if versions else None
    evidence = []
    if current:
        evidence = (await session.execute(select(AgentCompanyEvidence).where(
            AgentCompanyEvidence.dossier_version_id == current.id).order_by(AgentCompanyEvidence.created_at)
        )).scalars().all()
    return {"dossier": dump(dossier), "snapshot": current.snapshot if current else None,
            "diff": current.diff if current else {}, "evidence": [dump(item) for item in evidence],
            "versions": [dump(item) for item in versions]}


@router.post("/dossiers/{company_code}/refresh")
async def request_dossier_refresh(company_code: str, session: AsyncSession = Depends(get_session),
                                  user: User = Depends(get_current_user)):
    watch = (await session.execute(select(AgentCompanyWatchlist.id).where(
        AgentCompanyWatchlist.user_id == user.id, AgentCompanyWatchlist.company_code == company_code,
        AgentCompanyWatchlist.refresh_enabled.is_(True),
    ))).scalar_one_or_none()
    if not watch:
        raise HTTPException(400, "Only companies in 我的自选 can be refreshed")
    await enqueue_dossier_refresh(session, user.id, company_code, force=True)
    return {"ok": True, "status": "queued"}


@router.get("/dossiers/{company_code}/versions/{version}")
async def get_dossier_version(company_code: str, version: int, session: AsyncSession = Depends(get_session),
                              user: User = Depends(get_current_user)):
    item = (await session.execute(select(AgentCompanyDossierVersion).join(AgentCompanyDossier).where(
        AgentCompanyDossier.user_id == user.id, AgentCompanyDossier.company_code == company_code,
        AgentCompanyDossierVersion.version == version,
    ))).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Dossier version not found")
    return dump(item)


@router.post("/sessions")
async def create_session(req: SessionCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    agent = await session.get(AgentDefinition, req.agent_definition_id)
    if not agent or agent.user_id != user.id or not agent.is_active:
        raise HTTPException(404, "Agent not found")
    item = AgentSession(user_id=user.id, agent_definition_id=agent.id, title=req.title,
                        interaction_mode=req.interaction_mode, company_code=req.company_code)
    session.add(item)
    await session.flush()
    # FastAPI may finalize yield-based dependencies after the response is sent.
    # Commit here so the frontend's immediate timeline request can always see
    # the newly-created session (read-after-write consistency).
    await session.commit()
    return dump(item)


@router.patch("/sessions/{session_id}")
async def update_session(session_id: UUID, req: SessionUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentSession, session_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Session not found")
    if req.title is not None:
        item.title = req.title
    if req.is_pinned is not None:
        item.is_pinned = req.is_pinned
    if req.archived is not None:
        item.archived_at = datetime.now(UTC) if req.archived else None
        item.status = "archived" if req.archived else "active"
    if req.interaction_mode is not None:
        item.interaction_mode = req.interaction_mode
    if "company_code" in req.model_fields_set:
        item.company_code = req.company_code
    item.updated_at = datetime.now(UTC)
    return dump(item)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: UUID, session: AsyncSession = Depends(get_session),
                         user: User = Depends(get_current_user)):
    item = await session.get(AgentSession, session_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Session not found")
    active_run = (await session.execute(select(AgentRun.id).where(
        AgentRun.session_id == session_id,
        AgentRun.user_id == user.id,
        AgentRun.status.not_in(TERMINAL),
    ).limit(1))).scalar_one_or_none()
    if active_run:
        raise HTTPException(409, "Stop the active research task before deleting this session")
    await session.delete(item)
    await session.commit()
    return {"ok": True}


@router.post("/context-snapshots")
async def create_context_snapshot(req: ContextSnapshotCreate, session: AsyncSession = Depends(get_session),
                                  user: User = Depends(get_current_user)):
    item = AgentContextSnapshot(user_id=user.id, **req.model_dump())
    session.add(item)
    await session.flush()
    return dump(item)


@router.get("/risk-profile")
async def get_risk_profile(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    service = OpportunityService(session, TushareReadService(session), user.id)
    return profile_payload(await service.risk_profile())


@router.put("/risk-profile")
async def put_risk_profile(req: RiskProfileUpdate, session: AsyncSession = Depends(get_session),
                           user: User = Depends(get_current_user)):
    service = OpportunityService(session, TushareReadService(session), user.id)
    return profile_payload(await service.update_risk_profile(req.model_dump(exclude_unset=True)))


@router.get("/search")
async def search_research(q: str = Query(..., min_length=1, max_length=200),
                          limit: int = Query(30, ge=1, le=100),
                          session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await global_search(session, user.id, q, limit)


@router.post("/sessions/{session_id}/messages")
async def create_session_message(session_id: UUID, req: SessionMessageCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentSession, session_id)
    if not item or item.user_id != user.id or item.archived_at is not None:
        raise HTTPException(404, "Session not found")
    agent_id = req.agent_definition_id or item.agent_definition_id
    agent = await session.get(AgentDefinition, agent_id) if agent_id else None
    if not agent or agent.user_id != user.id or not agent.is_active:
        raise HTTPException(404, "Agent not found")
    item.agent_definition_id = agent.id
    existing = (await session.execute(select(AgentRun).where(
        AgentRun.user_id == user.id, AgentRun.idempotency_key == str(req.client_request_id),
    ))).scalar_one_or_none()
    if existing:
        return {"run": dump(existing), "session": dump(item)}
    prompt = req.content
    attachment_meta = []
    context_meta = []
    if req.context_snapshot_ids:
        snapshots = (await session.execute(select(AgentContextSnapshot).where(
            AgentContextSnapshot.id.in_(req.context_snapshot_ids), AgentContextSnapshot.user_id == user.id,
        ).order_by(AgentContextSnapshot.created_at))).scalars().all()
        if len(snapshots) != len(set(req.context_snapshot_ids)):
            raise HTTPException(400, "Invalid context snapshot")
        context_meta = [dump(snapshot) for snapshot in snapshots]
        context_lines = [
            json.dumps({
                "resource_type": snapshot.resource_type, "resource_id": snapshot.resource_id,
                "field": snapshot.field, "visible_start": snapshot.visible_start,
                "visible_end": snapshot.visible_end, "selected_point": snapshot.selected_point,
                "source": snapshot.source, "methodology": snapshot.methodology,
            }, ensure_ascii=False, default=str)
            for snapshot in snapshots
        ]
        prompt += "\n\nUser-selected immutable market context (facts only; do not infer omitted history):\n" + "\n".join(context_lines)
    if req.attachment_ids:
        files = (await session.execute(select(UploadedFile).where(
            UploadedFile.id.in_(req.attachment_ids), UploadedFile.user_id == user.id,
            UploadedFile.deleted_at.is_(None),
        ))).scalars().all()
        if len(files) != len(set(req.attachment_ids)):
            raise HTTPException(400, "Invalid attachment")
        sections = []
        storage = get_storage_provider()
        for uploaded in files:
            attachment_meta.append({"id": str(uploaded.id), "name": uploaded.file_name,
                                    "company_code": item.company_code})
            path = await storage.get_file_path(uploaded.storage_path)
            if path and can_extract_text(uploaded.file_name):
                result = await extract_text(path, uploaded.file_name)
                if result.success and result.text:
                    sections.append(f"Attachment {uploaded.file_name}:\n{result.text[:30000]}")
            else:
                sections.append(f"Attachment {uploaded.file_name}: binary/image supplied by the user; do not invent its contents.")
        if sections:
            prompt = f"{req.content}\n\nUser attachments bound to {item.company_code or 'this session'}:\n" + "\n\n".join(sections)
    run = await enqueue_run(session, user.id, agent, prompt, item.id, item.interaction_mode,
                            idempotency_key=str(req.client_request_id))
    if attachment_meta or context_meta:
        message = (await session.execute(select(AgentMessage).where(
            AgentMessage.run_id == run.id, AgentMessage.role == "user"
        ))).scalar_one_or_none()
        if message:
            message.metadata_json = {**(message.metadata_json or {}), "attachments": attachment_meta,
                                     "context_snapshots": context_meta}
    return {"run": dump(run), "session": dump(item)}


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


@router.get("/sessions/{session_id}/timeline")
async def session_timeline(session_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentSession, session_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Session not found")
    messages = (await session.execute(select(AgentMessage).where(AgentMessage.session_id == session_id)
                                      .order_by(AgentMessage.created_at).limit(300))).scalars().all()
    runs = (await session.execute(select(AgentRun).where(AgentRun.session_id == session_id)
                                  .order_by(AgentRun.created_at).limit(100))).scalars().all()
    return {"session": dump(item), "messages": [dump(m) for m in messages], "runs": [dump(r) for r in runs]}


@router.post("/sessions/{session_id}/compact")
async def compact_session(session_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    item = await session.get(AgentSession, session_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Session not found")
    messages = (await session.execute(select(AgentMessage).where(AgentMessage.session_id == session_id)
                                      .order_by(desc(AgentMessage.created_at)).limit(12))).scalars().all()
    item.summary = "\n".join(f"{m.role}: {m.content}" for m in reversed(messages))[-12000:]
    item.context_tokens = min(item.context_tokens, 8000)
    return dump(item)


@router.post("/sessions/{session_id}/stop")
async def stop_session_run(session_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    run = (await session.execute(select(AgentRun).where(
        AgentRun.session_id == session_id, AgentRun.user_id == user.id,
        AgentRun.status.not_in(TERMINAL),
    ).order_by(desc(AgentRun.created_at)).limit(1))).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Active run not found")
    return await _control_run(run.id, "cancel", session, user)


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
            result = await execute_platform_tool(step.tool_name or "", step.input_json or {}, session, user.id)
        if result.get("error"):
            raise HTTPException(502, result["error"])
        step.output_json, step.status, step.finished_at = redact_sensitive(result), "completed", datetime.now(UTC)
        if item.kind == "decision_log":
            session.add(AgentArtifact(user_id=user.id, run_id=run.id, artifact_type="decision_log",
                                      title=f"{result.get('symbol', '')} {result.get('action', '')}".strip() or "Decision log",
                                      content=redact_sensitive(result)))
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


@router.get("/learning/status")
async def learning_status(user: User = Depends(get_current_user)):
    snapshot = LearningBridge(get_settings().agent_learning_bridge_path).snapshot()
    return {key: value for key, value in snapshot.items() if key != "memories"}


@router.get("/learning/memories")
async def learning_memories(user: User = Depends(get_current_user)):
    return LearningBridge(get_settings().agent_learning_bridge_path).snapshot()


@router.post("/learning/feedback")
async def learning_feedback(req: LearningFeedbackCreate, session: AsyncSession = Depends(get_session),
                            user: User = Depends(get_current_user)):
    message = await session.get(AgentMessage, req.message_id)
    if not message or message.role != "assistant":
        raise HTTPException(404, "Assistant message not found")
    chat = await session.get(AgentSession, message.session_id)
    if not chat or chat.user_id != user.id:
        raise HTTPException(404, "Assistant message not found")
    comment = (req.comment or "").strip()
    if req.feedback in {"correction", "preference"} and not comment:
        raise HTTPException(400, "Correction or preference text is required")
    event_type = {
        "adopted": "result_feedback",
        "rejected": "feedback",
        "correction": "correction",
        "preference": "preference",
    }[req.feedback]
    label = {"adopted": "采用了这次回答", "rejected": "拒绝了这次回答"}.get(req.feedback, comment)
    summary = label if not comment or req.feedback in {"correction", "preference"} else f"{label}：{comment}"
    try:
        return LearningBridge(get_settings().agent_learning_bridge_path).record_feedback({
            "event_type": event_type, "summary": summary, "conversation_id": str(chat.id),
            "task_id": str(message.run_id or ""), "message_id": str(message.id), "user_id": str(user.id),
        })
    except (OSError, ValueError) as exc:
        raise HTTPException(503, "Learning feedback bridge is unavailable") from exc


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
