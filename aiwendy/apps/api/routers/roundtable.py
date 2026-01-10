"""Roundtable discussion endpoints for multi-coach conversations."""

import json
import asyncio
from datetime import datetime
from uuid import UUID
from typing import List, Optional, AsyncIterator
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from core.auth import get_current_user
from core.database import get_session
from core.logging import get_logger
from core.encryption import get_encryption_service
from domain.coach.models import (
    Coach,
    CoachPreset,
    RoundtableSession,
    RoundtableMessage,
)
from domain.knowledge.models import KnowledgeChunk, KnowledgeDocument
from domain.user.models import User
from infrastructure.llm.router import get_llm_router
from infrastructure.llm.base import Message as LLMMessage, MessageContent, ImageContent, LLMConfig
from infrastructure.llm.factory import create_llm_provider, llm_factory

router = APIRouter()
logger = get_logger(__name__)
encryption = get_encryption_service()


# ============= Pydantic Models =============

class CoachBrief(BaseModel):
    """Brief coach info for roundtable."""
    id: str
    name: str
    avatar_url: Optional[str]
    style: str
    description: Optional[str]

    class Config:
        orm_mode = True


class PresetResponse(BaseModel):
    """Preset combination response."""
    id: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    coach_ids: List[str]
    coaches: Optional[List[CoachBrief]] = None
    sort_order: int
    is_active: bool

    class Config:
        orm_mode = True


class CreateSessionRequest(BaseModel):
    """Create roundtable session request."""
    preset_id: Optional[str] = None
    coach_ids: Optional[List[str]] = Field(None, min_length=2, max_length=5)
    project_id: Optional[UUID] = None
    title: Optional[str] = None
    # Moderator mode settings
    discussion_mode: str = Field("free", pattern="^(free|moderated)$")
    moderator_id: Optional[str] = "host"  # Default to dedicated host coach

    # Optional session-level settings (can be overridden per message)
    config_id: Optional[str] = None  # User LLM config id
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=8000)
    kb_timing: str = Field("off", pattern="^(off|message|round|coach|moderator)$")
    kb_top_k: int = Field(5, ge=0, le=20)
    kb_max_candidates: int = Field(400, ge=50, le=2000)


class SessionResponse(BaseModel):
    """Roundtable session response."""
    id: UUID
    user_id: UUID
    project_id: Optional[UUID]
    preset_id: Optional[str]
    title: Optional[str]
    coach_ids: List[str]
    coaches: Optional[List[CoachBrief]] = None
    turn_order: Optional[List[str]]
    current_turn: int
    message_count: int
    round_count: int
    is_active: bool
    # Moderator mode fields
    discussion_mode: str = "free"
    moderator_id: Optional[str] = None
    moderator: Optional[CoachBrief] = None
    # Session-level settings
    llm_config_id: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_max_tokens: Optional[int] = None
    kb_timing: str = "off"
    kb_top_k: int = 5
    kb_max_candidates: int = 400
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class MessageAttachment(BaseModel):
    """Attachment in a roundtable message."""

    id: str
    type: str  # 'image', 'audio', 'pdf', 'word', 'excel', 'ppt', 'text', 'code', 'file'
    fileName: str
    fileSize: int
    mimeType: str
    url: str
    base64Data: Optional[str] = None  # For images to send to LLM (request only)
    extractedText: Optional[str] = None  # For documents
    transcription: Optional[str] = None  # For audio


class MessageResponse(BaseModel):
    """Roundtable message response."""
    id: UUID
    session_id: UUID
    coach_id: Optional[str]
    coach: Optional[CoachBrief] = None
    role: str
    content: str
    attachments: Optional[List[MessageAttachment]] = None
    message_type: str = "response"  # 'response' | 'opening' | 'summary' | 'closing'
    turn_number: Optional[int]
    sequence_in_turn: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True


class SessionDetailResponse(BaseModel):
    """Session with messages."""
    session: SessionResponse
    messages: List[MessageResponse]


class RoundtableChatRequest(BaseModel):
    """Roundtable chat request."""
    session_id: UUID
    content: str
    attachments: Optional[List[MessageAttachment]] = None
    max_rounds: int = Field(1, ge=1, le=3, description="Number of discussion rounds")
    config_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=8000)
    kb_timing: Optional[str] = Field(None, pattern="^(off|message|round|coach|moderator)$")
    kb_top_k: Optional[int] = Field(None, ge=0, le=20)
    kb_max_candidates: Optional[int] = Field(None, ge=50, le=2000)
    should_end: bool = Field(False, description="Request moderator to give closing remarks")
    debate_style: str = Field(
        "converge",
        pattern="^(converge|clash)$",
        description="Free-mode interaction style: converge (supplement+correct) or clash (debate+challenge)",
    )


class UpdateSessionSettingsRequest(BaseModel):
    """Update session-level settings (persisted)."""

    config_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=8000)
    kb_timing: Optional[str] = Field(None, pattern="^(off|message|round|coach|moderator)$")
    kb_top_k: Optional[int] = Field(None, ge=0, le=20)
    kb_max_candidates: Optional[int] = Field(None, ge=50, le=2000)


# ============= Helper Functions =============

def _decrypt_maybe(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        decrypted = encryption.decrypt(value)
        return decrypted or None
    except Exception:
        return value


def _get_user_llm_config(user: User, config_id: str) -> Optional[dict]:
    if not user.api_keys_encrypted:
        return None
    configs = user.api_keys_encrypted.get("llm_configs") or []
    for cfg in configs:
        if cfg.get("id") == config_id:
            return cfg
    return None


def _build_provider_from_llm_config(cfg: dict):
    provider_type = cfg.get("provider_type")
    if not provider_type:
        raise ValueError("provider_type is required")

    api_key = _decrypt_maybe(cfg.get("api_key"))
    base_url = (cfg.get("base_url") or "").strip() or None

    if provider_type == "custom":
        cfg_copy = cfg.copy()
        cfg_copy["api_key"] = api_key
        return llm_factory.create_custom_provider_from_dict(cfg_copy), provider_type, cfg

    provider = create_llm_provider(
        provider=provider_type,
        api_key=api_key,
        base_url=base_url,
        model=cfg.get("default_model") or None,
    )
    return provider, provider_type, cfg


async def _retrieve_kb_context(
    session: AsyncSession,
    current_user: User,
    project_id: Optional[UUID],
    query_text: str,
    top_k: int = 5,
    max_candidates: int = 400,
) -> list[dict]:
    query_text = (query_text or "").strip()
    if not query_text:
        return []

    llm_router = get_llm_router(user=current_user)
    provider_order: list[str] = []
    if "openai" in llm_router.providers:
        provider_order.append("openai")
    if "ollama" in llm_router.providers:
        provider_order.append("ollama")
    for name, provider in llm_router.providers.items():
        if name not in ("openai", "ollama", "anthropic"):
            if hasattr(provider, "config") and getattr(provider.config, "supports_embeddings", False):
                provider_order.append(name)

    for provider_name in provider_order:
        provider = llm_router.providers.get(provider_name)
        if provider is None:
            continue

        try:
            query_embedding = await provider.embed(query_text, model=None)
            if not query_embedding:
                continue
        except Exception as e:
            logger.warning(f"KB embedding failed with {provider_name}: {e}")
            continue

        dim = len(query_embedding)
        distance = KnowledgeChunk.embedding_vector.cosine_distance(query_embedding)
        conditions = [
            KnowledgeChunk.user_id == current_user.id,
            KnowledgeChunk.embedding_dim == dim,
            KnowledgeChunk.embedding_vector.isnot(None),
            KnowledgeDocument.user_id == current_user.id,
            KnowledgeDocument.deleted_at.is_(None),
        ]
        if project_id is not None:
            conditions.append(KnowledgeChunk.project_id == project_id)
            conditions.append(KnowledgeDocument.project_id == project_id)

        stmt = (
            select(KnowledgeChunk, KnowledgeDocument.title, distance.label("distance"))
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(and_(*conditions))
            .order_by(distance)
            .limit(max(1, min(top_k, 20)))
        )

        rows = (await session.execute(stmt)).all()
        if not rows:
            continue

        return [
            {
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "document_title": title,
                "score": max(0.0, 1.0 - float(dist)),
                "content": chunk.content,
            }
            for chunk, title, dist in rows
        ]

    return []


def _format_kb_context(chunks: list[dict]) -> str:
    if not chunks:
        return ""
    lines: list[str] = []
    for idx, item in enumerate(chunks, 1):
        title = str(item.get("document_title") or "Document")
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"[{idx}] {title}\n{content}")
    if not lines:
        return ""
    return (
        "以下为知识库检索到的参考内容（仅在相关时使用，不要编造引用）：\n\n"
        + "\n\n---\n\n".join(lines)
    )


def _sanitize_attachments_for_storage(attachments: Optional[List[MessageAttachment]]) -> Optional[list[dict]]:
    if not attachments:
        return None
    sanitized: list[dict] = []
    for att in attachments:
        sanitized.append(
            {
                "id": att.id,
                "type": att.type,
                "fileName": att.fileName,
                "fileSize": att.fileSize,
                "mimeType": att.mimeType,
                "url": att.url,
                "extractedText": att.extractedText,
                "transcription": att.transcription,
            }
        )
    return sanitized or None


def _build_user_llm_message(
    content: str,
    attachments: Optional[List[MessageAttachment]],
) -> LLMMessage:
    if not attachments:
        return LLMMessage(role="user", content=content)

    content_parts: List[MessageContent] = []
    if (content or "").strip():
        content_parts.append(MessageContent(type="text", text=content))

    extra_context: list[str] = []
    for att in attachments:
        if att.type == "image" and att.base64Data:
            content_parts.append(
                MessageContent(type="image_url", image_url=ImageContent(url=att.base64Data))
            )
            continue
        if att.extractedText:
            extra_context.append(f"[文件: {att.fileName}]\n{att.extractedText}")
            continue
        if att.transcription:
            extra_context.append(f"[语音转写: {att.fileName}]\n{att.transcription}")
            continue
        if att.type == "image":
            extra_context.append(f"[图片: {att.fileName}]\n{att.url}")
        else:
            extra_context.append(f"[附件: {att.fileName}]\n{att.url}")

    if extra_context:
        context_text = "\n\n---\n\n".join(extra_context)
        if content_parts and content_parts[0].type == "text":
            content_parts[0] = MessageContent(
                type="text",
                text=f"{content_parts[0].text}\n\n附件内容:\n{context_text}",
            )
        else:
            content_parts.insert(
                0,
                MessageContent(type="text", text=f"附件内容:\n{context_text}"),
            )

    if len(content_parts) > 1 or (len(content_parts) == 1 and content_parts[0].type == "image_url"):
        return LLMMessage(role="user", content=content_parts)
    if content_parts and content_parts[0].type == "text":
        return LLMMessage(role="user", content=content_parts[0].text or content)
    return LLMMessage(role="user", content=content)


def _build_roundtable_system_prompt(coach: Coach, all_coaches: List[Coach]) -> str:
    """Build system prompt for roundtable discussion."""
    coach_names = [c.name for c in all_coaches]
    other_coaches = [c for c in all_coaches if c.id != coach.id]
    other_names = ", ".join([c.name for c in other_coaches])

    base_prompt = coach.system_prompt or ""

    roundtable_context = f"""

你正在参与一场关于交易心理的圆桌讨论。
参与者：{', '.join(coach_names)}
你的角色是 {coach.name}（{coach.style.value if coach.style else '教练'}风格）。

讨论规则：
1. 保持你独特的个性和沟通风格
2. 可以回应、补充或友好地质疑其他教练的观点
3. 每次发言保持简洁，2-4句话即可
4. 关注用户的具体问题，给出有价值的建议
5. 如果其他教练已经给出了好的建议，可以补充而不是重复

其他教练：{other_names}
"""
    return base_prompt + roundtable_context


def _build_debate_round_instruction(round_num: int, debate_style: str) -> str:
    """Build per-round instruction to encourage multi-round cross-coach debate in free mode."""
    if round_num <= 1:
        return (
            "你正在进行第 1 轮讨论：请给出你从自己风格出发的核心判断与建议。\n"
            "要求：2-4 句，尽量具体可执行；不要复述其他人（因为还没开始互辩）。"
        )

    debate_style = (debate_style or "converge").strip().lower()
    if debate_style == "clash":
        return (
            f"你正在进行第 {round_num} 轮互辩（对立辩论风格）：你必须点名引用至少 1 位其他教练的观点，\n"
            "并指出其建议的潜在风险/盲点（可以不同意），然后给出你的替代方案或更严格的边界条件。\n"
            "最后输出 1 条你认为最关键、最可执行的动作建议。\n"
            "要求：2-5 句；避免重复上一轮自己的话；保持专业但允许有建设性的反驳。"
        )

    return (
        f"你正在进行第 {round_num} 轮互辩（收敛纠错风格）：你必须点名引用至少 1 位其他教练的观点，\n"
        "说明你同意/补充/纠错的点，并把各方观点合并成更清晰的执行方案（明确优先级或适用条件）。\n"
        "最后输出 1-2 条更具体、可执行的建议。\n"
        "要求：2-5 句；避免重复上一轮自己的话；保持专业、聚焦可执行。"
    )


# ============= Moderator Helper Functions =============

def _build_moderator_opening_prompt(moderator: Coach, coaches: List[Coach], user_question: str) -> str:
    """Build opening prompt for moderator."""
    coach_names = [c.name for c in coaches]
    coach_styles = [f"{c.name}（{c.style.value if c.style else '教练'}风格）" for c in coaches]

    base_prompt = moderator.system_prompt or ""

    opening_context = f"""

你是本次圆桌讨论的主持人。
参与教练：{', '.join(coach_styles)}
用户问题：{user_question}

请用 2-3 句话开场：
1. 简要破题，说明这是个什么类型的问题
2. 预告将邀请哪些教练从哪些角度来分析这个问题

注意：
- 保持简洁专业
- 不要重复用户的问题原文
- 让用户知道接下来会发生什么
"""
    return base_prompt + opening_context


def _build_moderator_summary_prompt(moderator: Coach, coaches: List[Coach], round_messages: List[dict]) -> str:
    """Build summary prompt for moderator after a round of discussion."""
    base_prompt = moderator.system_prompt or ""

    # Format round messages
    formatted_messages = []
    for msg in round_messages:
        if msg.get("coach_name"):
            formatted_messages.append(f"【{msg['coach_name']}】: {msg['content']}")

    summary_context = f"""

你是主持人，请总结本轮讨论。

各教练观点：
{chr(10).join(formatted_messages)}

请用 3-4 句话：
1. 总结各教练的核心观点和建议
2. 指出他们观点中的共识和分歧（如果有）
3. 提出一个深化问题供用户思考或追问

注意：
- 保持中立客观
- 突出要点，不要重复全部内容
- 深化问题要有启发性
"""
    return base_prompt + summary_context


def _build_moderator_closing_prompt(moderator: Coach, coaches: List[Coach], all_messages: List[dict]) -> str:
    """Build closing prompt for moderator."""
    base_prompt = moderator.system_prompt or ""

    # Get summary of the discussion
    coach_contributions = {}
    for msg in all_messages:
        if msg.get("coach_name") and msg.get("role") == "assistant":
            name = msg["coach_name"]
            if name not in coach_contributions:
                coach_contributions[name] = []
            coach_contributions[name].append(msg["content"])

    contributions_summary = []
    for name, contents in coach_contributions.items():
        contributions_summary.append(f"【{name}】共发言 {len(contents)} 次")

    closing_context = f"""

你是主持人，讨论即将结束，请给出结语。

讨论概况：
{chr(10).join(contributions_summary)}

请用 4-5 句话：
1. 感谢各位教练的精彩分享
2. 综合各教练观点，给出 2-3 条核心建议
3. 鼓励用户将建议付诸实践
4. 欢迎用户随时开启新的讨论

注意：
- 总结要有综合性，不是简单罗列
- 建议要具体可执行
- 语气温和专业
"""
    return base_prompt + closing_context


async def _get_coaches_by_ids(db: AsyncSession, coach_ids: List[str]) -> List[Coach]:
    """Get coaches by IDs, maintaining order."""
    result = await db.execute(
        select(Coach).where(Coach.id.in_(coach_ids), Coach.is_active == True)
    )
    coaches_map = {c.id: c for c in result.scalars().all()}
    return [coaches_map[cid] for cid in coach_ids if cid in coaches_map]


# ============= Preset Endpoints =============

@router.get("/presets", response_model=List[PresetResponse])
async def list_presets(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all active coach presets."""
    result = await db.execute(
        select(CoachPreset)
        .where(CoachPreset.is_active == True)
        .order_by(CoachPreset.sort_order)
    )
    presets = result.scalars().all()

    # Enrich with coach details
    response = []
    for preset in presets:
        coaches = await _get_coaches_by_ids(db, preset.coach_ids or [])
        preset_dict = {
            "id": preset.id,
            "name": preset.name,
            "description": preset.description,
            "icon": preset.icon,
            "coach_ids": preset.coach_ids or [],
            "coaches": [
                CoachBrief(
                    id=c.id,
                    name=c.name,
                    avatar_url=c.avatar_url,
                    style=c.style.value if c.style else "",
                    description=c.description,
                )
                for c in coaches
            ],
            "sort_order": preset.sort_order or 0,
            "is_active": preset.is_active,
        }
        response.append(PresetResponse(**preset_dict))

    return response


@router.get("/presets/{preset_id}", response_model=PresetResponse)
async def get_preset(
    preset_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a specific preset with coach details."""
    result = await db.execute(
        select(CoachPreset).where(CoachPreset.id == preset_id)
    )
    preset = result.scalar_one_or_none()

    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    coaches = await _get_coaches_by_ids(db, preset.coach_ids or [])

    return PresetResponse(
        id=preset.id,
        name=preset.name,
        description=preset.description,
        icon=preset.icon,
        coach_ids=preset.coach_ids or [],
        coaches=[
            CoachBrief(
                id=c.id,
                name=c.name,
                avatar_url=c.avatar_url,
                style=c.style.value if c.style else "",
                description=c.description,
            )
            for c in coaches
        ],
        sort_order=preset.sort_order or 0,
        is_active=preset.is_active,
    )


# ============= Session Endpoints =============

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new roundtable session."""
    import uuid

    coach_ids: List[str] = []

    # Get coach IDs from preset or request
    if request.preset_id:
        result = await db.execute(
            select(CoachPreset).where(CoachPreset.id == request.preset_id)
        )
        preset = result.scalar_one_or_none()
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")
        coach_ids = preset.coach_ids or []
    elif request.coach_ids:
        coach_ids = request.coach_ids
    else:
        raise HTTPException(
            status_code=400,
            detail="Either preset_id or coach_ids is required"
        )

    # Validate coach count
    if len(coach_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 coaches are required")
    if len(coach_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 coaches allowed")

    # Verify all coaches exist
    coaches = await _get_coaches_by_ids(db, coach_ids)
    if len(coaches) != len(coach_ids):
        raise HTTPException(status_code=400, detail="Some coaches not found")

    # Validate moderator if in moderated mode
    moderator = None
    moderator_id = None
    if request.discussion_mode == "moderated":
        moderator_id = request.moderator_id or "host"
        # Get moderator coach
        result = await db.execute(
            select(Coach).where(Coach.id == moderator_id, Coach.is_active == True)
        )
        moderator = result.scalar_one_or_none()
        if not moderator:
            raise HTTPException(status_code=400, detail=f"Moderator '{moderator_id}' not found")

    # Create session
    session = RoundtableSession(
        id=uuid.uuid4(),
        user_id=current_user.id,
        project_id=request.project_id,
        preset_id=request.preset_id,
        title=request.title or f"圆桌讨论 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        coach_ids=coach_ids,
        turn_order=coach_ids,
        current_turn=0,
        discussion_mode=request.discussion_mode,
        moderator_id=moderator_id,
        llm_config_id=(request.config_id or "").strip() or None,
        llm_provider=(request.provider or "").strip() or None,
        llm_model=(request.model or "").strip() or None,
        llm_temperature=request.temperature,
        llm_max_tokens=request.max_tokens,
        kb_timing=(request.kb_timing or "off").strip(),
        kb_top_k=request.kb_top_k,
        kb_max_candidates=request.kb_max_candidates,
        message_count=0,
        round_count=0,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        project_id=session.project_id,
        preset_id=session.preset_id,
        title=session.title,
        coach_ids=session.coach_ids,
        coaches=[
            CoachBrief(
                id=c.id,
                name=c.name,
                avatar_url=c.avatar_url,
                style=c.style.value if c.style else "",
                description=c.description,
            )
            for c in coaches
        ],
        turn_order=session.turn_order,
        current_turn=session.current_turn,
        message_count=session.message_count,
        round_count=session.round_count,
        is_active=session.is_active,
        discussion_mode=session.discussion_mode or "free",
        moderator_id=session.moderator_id,
        moderator=CoachBrief(
            id=moderator.id,
            name=moderator.name,
            avatar_url=moderator.avatar_url,
            style=moderator.style.value if moderator.style else "",
            description=moderator.description,
        ) if moderator else None,
        llm_config_id=session.llm_config_id,
        llm_provider=session.llm_provider,
        llm_model=session.llm_model,
        llm_temperature=session.llm_temperature,
        llm_max_tokens=session.llm_max_tokens,
        kb_timing=session.kb_timing or "off",
        kb_top_k=session.kb_top_k or 5,
        kb_max_candidates=session.kb_max_candidates or 400,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    project_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List user's roundtable sessions."""
    query = select(RoundtableSession).where(
        RoundtableSession.user_id == current_user.id
    )

    if project_id:
        query = query.where(RoundtableSession.project_id == project_id)
    if is_active is not None:
        query = query.where(RoundtableSession.is_active == is_active)

    query = query.order_by(desc(RoundtableSession.created_at)).limit(limit)

    result = await db.execute(query)
    sessions = result.scalars().all()

    response = []
    for session in sessions:
        coaches = await _get_coaches_by_ids(db, session.coach_ids or [])
        # Get moderator if in moderated mode
        moderator = None
        if session.moderator_id:
            mod_result = await db.execute(
                select(Coach).where(Coach.id == session.moderator_id)
            )
            moderator = mod_result.scalar_one_or_none()

        response.append(
            SessionResponse(
                id=session.id,
                user_id=session.user_id,
                project_id=session.project_id,
                preset_id=session.preset_id,
                title=session.title,
                coach_ids=session.coach_ids,
                coaches=[
                    CoachBrief(
                        id=c.id,
                        name=c.name,
                        avatar_url=c.avatar_url,
                        style=c.style.value if c.style else "",
                        description=c.description,
                    )
                    for c in coaches
                ],
                turn_order=session.turn_order,
                current_turn=session.current_turn,
                message_count=session.message_count,
                round_count=session.round_count,
                is_active=session.is_active,
                discussion_mode=session.discussion_mode or "free",
                moderator_id=session.moderator_id,
                moderator=CoachBrief(
                    id=moderator.id,
                    name=moderator.name,
                    avatar_url=moderator.avatar_url,
                    style=moderator.style.value if moderator.style else "",
                    description=moderator.description,
                ) if moderator else None,
                llm_config_id=session.llm_config_id,
                llm_provider=session.llm_provider,
                llm_model=session.llm_model,
                llm_temperature=session.llm_temperature,
                llm_max_tokens=session.llm_max_tokens,
                kb_timing=session.kb_timing or "off",
                kb_top_k=session.kb_top_k or 5,
                kb_max_candidates=session.kb_max_candidates or 400,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
        )

    return response


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get session details with messages."""
    result = await db.execute(
        select(RoundtableSession).where(RoundtableSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get coaches
    coaches = await _get_coaches_by_ids(db, session.coach_ids or [])
    coaches_map = {c.id: c for c in coaches}

    # Get moderator if in moderated mode
    moderator = None
    if session.moderator_id:
        mod_result = await db.execute(
            select(Coach).where(Coach.id == session.moderator_id)
        )
        moderator = mod_result.scalar_one_or_none()
        # Add moderator to coaches_map for message rendering
        if moderator:
            coaches_map[moderator.id] = moderator

    # Get messages
    msg_result = await db.execute(
        select(RoundtableMessage)
        .where(RoundtableMessage.session_id == session_id)
        .order_by(RoundtableMessage.created_at)
    )
    messages = msg_result.scalars().all()

    session_response = SessionResponse(
        id=session.id,
        user_id=session.user_id,
        project_id=session.project_id,
        preset_id=session.preset_id,
        title=session.title,
        coach_ids=session.coach_ids,
        coaches=[
            CoachBrief(
                id=c.id,
                name=c.name,
                avatar_url=c.avatar_url,
                style=c.style.value if c.style else "",
                description=c.description,
            )
            for c in coaches
        ],
        turn_order=session.turn_order,
        current_turn=session.current_turn,
        message_count=session.message_count,
        round_count=session.round_count,
        is_active=session.is_active,
        discussion_mode=session.discussion_mode or "free",
        moderator_id=session.moderator_id,
        moderator=CoachBrief(
            id=moderator.id,
            name=moderator.name,
            avatar_url=moderator.avatar_url,
            style=moderator.style.value if moderator.style else "",
            description=moderator.description,
        ) if moderator else None,
        llm_config_id=session.llm_config_id,
        llm_provider=session.llm_provider,
        llm_model=session.llm_model,
        llm_temperature=session.llm_temperature,
        llm_max_tokens=session.llm_max_tokens,
        kb_timing=session.kb_timing or "off",
        kb_top_k=session.kb_top_k or 5,
        kb_max_candidates=session.kb_max_candidates or 400,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )

    message_responses = []
    for msg in messages:
        coach = coaches_map.get(msg.coach_id) if msg.coach_id else None
        message_responses.append(
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                coach_id=msg.coach_id,
                coach=CoachBrief(
                    id=coach.id,
                    name=coach.name,
                    avatar_url=coach.avatar_url,
                    style=coach.style.value if coach.style else "",
                    description=coach.description,
                ) if coach else None,
                role=msg.role,
                content=msg.content,
                attachments=msg.attachments,
                message_type=msg.message_type or "response",
                turn_number=msg.turn_number,
                sequence_in_turn=msg.sequence_in_turn,
                created_at=msg.created_at,
            )
        )

    return SessionDetailResponse(session=session_response, messages=message_responses)


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session_settings(
    session_id: UUID,
    request: UpdateSessionSettingsRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update session-level settings (persisted)."""
    result = await db.execute(select(RoundtableSession).where(RoundtableSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if request.config_id is not None:
        session.llm_config_id = (request.config_id or "").strip() or None
    if request.provider is not None:
        session.llm_provider = (request.provider or "").strip() or None
    if request.model is not None:
        session.llm_model = (request.model or "").strip() or None
    if request.temperature is not None:
        session.llm_temperature = request.temperature
    if request.max_tokens is not None:
        session.llm_max_tokens = request.max_tokens

    if request.kb_timing is not None:
        session.kb_timing = (request.kb_timing or "off").strip()
    if request.kb_top_k is not None:
        session.kb_top_k = request.kb_top_k
    if request.kb_max_candidates is not None:
        session.kb_max_candidates = request.kb_max_candidates

    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)

    coaches = await _get_coaches_by_ids(db, session.coach_ids or [])
    moderator = None
    if session.moderator_id:
        mod_result = await db.execute(select(Coach).where(Coach.id == session.moderator_id))
        moderator = mod_result.scalar_one_or_none()

    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        project_id=session.project_id,
        preset_id=session.preset_id,
        title=session.title,
        coach_ids=session.coach_ids,
        coaches=[
            CoachBrief(
                id=c.id,
                name=c.name,
                avatar_url=c.avatar_url,
                style=c.style.value if c.style else "",
                description=c.description,
            )
            for c in coaches
        ],
        turn_order=session.turn_order,
        current_turn=session.current_turn,
        message_count=session.message_count,
        round_count=session.round_count,
        is_active=session.is_active,
        discussion_mode=session.discussion_mode or "free",
        moderator_id=session.moderator_id,
        moderator=CoachBrief(
            id=moderator.id,
            name=moderator.name,
            avatar_url=moderator.avatar_url,
            style=moderator.style.value if moderator.style else "",
            description=moderator.description,
        )
        if moderator
        else None,
        llm_config_id=session.llm_config_id,
        llm_provider=session.llm_provider,
        llm_model=session.llm_model,
        llm_temperature=session.llm_temperature,
        llm_max_tokens=session.llm_max_tokens,
        kb_timing=session.kb_timing or "off",
        kb_top_k=session.kb_top_k or 5,
        kb_max_candidates=session.kb_max_candidates or 400,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """End a roundtable session."""
    result = await db.execute(
        select(RoundtableSession).where(RoundtableSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    session.is_active = False
    session.ended_at = datetime.utcnow()
    session.updated_at = datetime.utcnow()

    await db.commit()

    return {"status": "ok", "message": "Session ended"}


# ============= Chat Endpoint =============

@router.post("/chat")
async def roundtable_chat(
    request: RoundtableChatRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Send a message and get responses from all coaches in turn.

    Returns SSE stream with events:
    - round_start: {type, round}
    - coach_start: {type, coach_id, coach_name, coach_avatar}
    - content: {type, coach_id, content}
    - coach_end: {type, coach_id}
    - round_end: {type, round}
    - moderator_start: {type, message_type, coach_id, coach_name, coach_avatar}
    - moderator_end: {type, message_type, coach_id}
    - done: {type}
    - error: {type, message}
    """
    # Validate session
    result = await db.execute(
        select(RoundtableSession).where(RoundtableSession.id == request.session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is not active")

    # Get coaches
    coaches = await _get_coaches_by_ids(db, session.coach_ids or [])
    if not coaches:
        raise HTTPException(status_code=400, detail="No valid coaches in session")

    # Get moderator if in moderated mode
    moderator = None
    is_moderated = session.discussion_mode == "moderated"
    if is_moderated and session.moderator_id:
        mod_result = await db.execute(
            select(Coach).where(Coach.id == session.moderator_id, Coach.is_active == True)
        )
        moderator = mod_result.scalar_one_or_none()
        if not moderator:
            raise HTTPException(status_code=400, detail="Moderator not found")

    # Resolve session-level defaults + request-level overrides
    preferred_provider = (request.provider or session.llm_provider or "").strip() or None
    effective_config_id = (request.config_id or session.llm_config_id or "").strip() or None
    temperature_override = request.temperature if request.temperature is not None else session.llm_temperature
    max_tokens_override = request.max_tokens if request.max_tokens is not None else session.llm_max_tokens

    kb_timing = (request.kb_timing or session.kb_timing or "off").strip()
    kb_top_k = request.kb_top_k if request.kb_top_k is not None else (session.kb_top_k or 5)
    kb_max_candidates = (
        request.kb_max_candidates
        if request.kb_max_candidates is not None
        else (session.kb_max_candidates or 400)
    )
    use_kb = kb_timing != "off" and (kb_top_k or 0) > 0

    # Get LLM provider (optional user config)
    selected_provider = None
    selected_cfg = None

    if effective_config_id:
        cfg = _get_user_llm_config(current_user, effective_config_id)
        if not cfg:
            raise HTTPException(status_code=404, detail="LLM config not found")
        if cfg.get("is_active") is False:
            raise HTTPException(status_code=400, detail="LLM config is not active")
        try:
            selected_provider, _, selected_cfg = _build_provider_from_llm_config(cfg)
        except Exception as e:
            logger.error(f"Failed to build provider: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    llm_router = get_llm_router(user=current_user)

    if not selected_provider and not llm_router.providers:
        raise HTTPException(
            status_code=400,
            detail="No LLM provider configured. Please set up API keys."
        )

    # Determine model
    model: Optional[str] = (request.model or "").strip() or None
    if not model:
        model = (session.llm_model or "").strip() or None
    if not model and selected_cfg:
        model = (selected_cfg.get("default_model") or "").strip() or None
    if not model:
        model = "gpt-4o-mini"

    async def stream_llm_response(prompt: str, config: LLMConfig) -> AsyncIterator[str]:
        """Helper to stream LLM response."""
        llm_messages = [LLMMessage(role="user", content=prompt)]
        if selected_provider:
            stream = selected_provider.chat_stream(llm_messages, config)
        else:
            stream = await llm_router.chat_stream_with_fallback(
                messages=llm_messages,
                config=config,
                preferred_provider=preferred_provider,
            )
        async for chunk in stream:
            yield chunk

    async def generate_roundtable_stream() -> AsyncIterator[str]:
        """Generate SSE stream for roundtable discussion."""
        try:
            import uuid

            # Check if this is the first message in the session
            is_first_message = (session.message_count or 0) == 0

            # Save user message
            user_message = RoundtableMessage(
                id=uuid.uuid4(),
                session_id=session.id,
                coach_id=None,
                role="user",
                content=request.content.strip(),
                attachments=_sanitize_attachments_for_storage(request.attachments),
                message_type="response",
                turn_number=session.round_count + 1,
                sequence_in_turn=0,
                created_at=datetime.utcnow(),
            )
            db.add(user_message)
            session.message_count = (session.message_count or 0) + 1
            await db.commit()

            # Build conversation history
            history_result = await db.execute(
                select(RoundtableMessage)
                .where(RoundtableMessage.session_id == session.id)
                .order_by(RoundtableMessage.created_at)
            )
            history_messages = list(history_result.scalars().all())

            kb_query_base = request.content.strip()
            if request.attachments:
                extra: list[str] = []
                for att in request.attachments:
                    if att.extractedText:
                        extra.append(f"[文件: {att.fileName}]\n{att.extractedText}")
                    elif att.transcription:
                        extra.append(f"[语音转写: {att.fileName}]\n{att.transcription}")
                if extra:
                    kb_query_base = f"{kb_query_base}\n\n" + "\n\n---\n\n".join(extra)

            kb_cache: dict[str, str] = {}

            def build_kb_query_with_history(max_assistant_messages: int = 4) -> str:
                parts: list[str] = [kb_query_base]
                count = 0
                for hist in reversed(history_messages):
                    if hist.role != "assistant":
                        continue
                    if not (hist.content or "").strip():
                        continue
                    parts.append(hist.content.strip())
                    count += 1
                    if count >= max_assistant_messages:
                        break
                parts.reverse()
                return "\n\n".join(parts).strip()

            async def get_kb_text(stage_key: str, query_text: str) -> str:
                if not use_kb:
                    return ""
                cache_key = f"{kb_timing}:{stage_key}"
                if cache_key in kb_cache:
                    return kb_cache[cache_key]
                chunks = await _retrieve_kb_context(
                    db,
                    current_user,
                    session.project_id,
                    query_text=query_text,
                    top_k=kb_top_k,
                    max_candidates=kb_max_candidates,
                )
                kb_text = _format_kb_context(chunks)
                kb_cache[cache_key] = kb_text
                return kb_text

            kb_message_text = ""
            if kb_timing == "message":
                kb_message_text = await get_kb_text("message", kb_query_base)

            # ========== MODERATOR OPENING (if first message and moderated) ==========
            if is_moderated and moderator and is_first_message:
                yield f"data: {json.dumps({'type': 'moderator_start', 'message_type': 'opening', 'coach_id': moderator.id, 'coach_name': moderator.name, 'coach_avatar': moderator.avatar_url})}\n\n"

                opening_prompt = _build_moderator_opening_prompt(moderator, coaches, request.content)
                if kb_timing in ("message", "round", "moderator"):
                    kb_text = kb_message_text
                    if kb_timing == "round":
                        kb_text = await get_kb_text("round:1", build_kb_query_with_history())
                    elif kb_timing == "moderator":
                        kb_text = await get_kb_text("moderator:opening", build_kb_query_with_history())
                    if kb_text:
                        opening_prompt = f"{opening_prompt}\n\n{kb_text}"
                config = LLMConfig(
                    model=model,
                    temperature=(temperature_override if temperature_override is not None else (moderator.temperature or 0.7)),
                    max_tokens=(max_tokens_override if max_tokens_override is not None else 300),
                    stream=True,
                )

                accumulated = ""
                try:
                    async for chunk in stream_llm_response(opening_prompt, config):
                        accumulated += chunk
                        yield f"data: {json.dumps({'type': 'content', 'coach_id': moderator.id, 'content': chunk})}\n\n"
                        await asyncio.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error streaming moderator opening: {e}")
                    accumulated = "欢迎来到本次圆桌讨论。让我们请各位教练就这个问题分享自己的见解。"
                    yield f"data: {json.dumps({'type': 'content', 'coach_id': moderator.id, 'content': accumulated})}\n\n"

                # Save moderator opening message
                opening_message = RoundtableMessage(
                    id=uuid.uuid4(),
                    session_id=session.id,
                    coach_id=moderator.id,
                    role="assistant",
                    content=accumulated,
                    message_type="opening",
                    turn_number=session.round_count + 1,
                    sequence_in_turn=0,
                    created_at=datetime.utcnow(),
                )
                db.add(opening_message)
                session.message_count = (session.message_count or 0) + 1
                history_messages.append(opening_message)

                yield f"data: {json.dumps({'type': 'moderator_end', 'message_type': 'opening', 'coach_id': moderator.id})}\n\n"

            # ========== PROCESS EACH ROUND ==========
            for round_num in range(1, request.max_rounds + 1):
                yield f"data: {json.dumps({'type': 'round_start', 'round': round_num})}\n\n"

                # Track this round's messages for moderator summary
                round_messages = []

                kb_round_text = ""
                if kb_timing == "round":
                    kb_round_text = await get_kb_text(f"round:{round_num}", build_kb_query_with_history())

                # Each coach responds in turn
                for seq, coach in enumerate(coaches):
                    yield f"data: {json.dumps({'type': 'coach_start', 'coach_id': coach.id, 'coach_name': coach.name, 'coach_avatar': coach.avatar_url})}\n\n"

                    # Build messages for this coach
                    system_prompt = _build_roundtable_system_prompt(coach, coaches)
                    llm_messages = [LLMMessage(role="system", content=system_prompt)]

                    # In free mode, encourage cross-coach multi-round debate automatically.
                    if not is_moderated:
                        llm_messages.append(
                            LLMMessage(
                                role="system",
                                content=_build_debate_round_instruction(round_num, request.debate_style),
                            )
                        )

                    # Inject knowledge base context according to timing policy
                    if kb_timing == "message" and kb_message_text:
                        llm_messages.append(LLMMessage(role="system", content=kb_message_text))
                    elif kb_timing == "round" and kb_round_text:
                        llm_messages.append(LLMMessage(role="system", content=kb_round_text))
                    elif kb_timing == "coach":
                        kb_text = await get_kb_text(
                            f"coach:{round_num}:{coach.id}",
                            build_kb_query_with_history(),
                        )
                        if kb_text:
                            llm_messages.append(LLMMessage(role="system", content=kb_text))

                    # Add conversation history
                    for msg in history_messages:
                        if msg.role == "user":
                            if msg.id == user_message.id:
                                llm_messages.append(_build_user_llm_message(msg.content, request.attachments))
                            else:
                                stored_attachments = None
                                if msg.attachments:
                                    stored_attachments = [
                                        MessageAttachment(**item)
                                        for item in (msg.attachments or [])
                                        if isinstance(item, dict)
                                    ]
                                llm_messages.append(_build_user_llm_message(msg.content, stored_attachments))
                        else:
                            # Coach/moderator message - indicate who said it
                            msg_coach_name = "教练"
                            if msg.coach_id == moderator.id if moderator else False:
                                msg_coach_name = moderator.name
                            else:
                                msg_coach_name = next(
                                    (c.name for c in coaches if c.id == msg.coach_id),
                                    "教练"
                                )
                            llm_messages.append(
                                LLMMessage(
                                    role="assistant",
                                    content=f"[{msg_coach_name}]: {msg.content}"
                                )
                            )

                    config = LLMConfig(
                        model=model,
                        temperature=(temperature_override if temperature_override is not None else (coach.temperature or 0.7)),
                        max_tokens=(max_tokens_override if max_tokens_override is not None else 500),
                        stream=True,
                    )

                    # Stream coach response
                    accumulated = ""
                    try:
                        if selected_provider:
                            stream = selected_provider.chat_stream(llm_messages, config)
                        else:
                            stream = llm_router.chat_stream_with_fallback(
                                messages=llm_messages,
                                config=config,
                                preferred_provider=preferred_provider,
                            )

                        async for chunk in stream:
                            accumulated += chunk
                            yield f"data: {json.dumps({'type': 'content', 'coach_id': coach.id, 'content': chunk})}\n\n"
                            await asyncio.sleep(0.01)

                    except Exception as e:
                        logger.error(f"Error streaming coach {coach.id}: {e}")
                        accumulated = f"抱歉，我暂时无法回应。请稍后再试。"
                        yield f"data: {json.dumps({'type': 'content', 'coach_id': coach.id, 'content': accumulated})}\n\n"

                    # Save coach message
                    coach_message = RoundtableMessage(
                        id=uuid.uuid4(),
                        session_id=session.id,
                        coach_id=coach.id,
                        role="assistant",
                        content=accumulated,
                        message_type="response",
                        turn_number=session.round_count + round_num,
                        sequence_in_turn=seq + 1,
                        created_at=datetime.utcnow(),
                    )
                    db.add(coach_message)
                    session.message_count = (session.message_count or 0) + 1

                    # Add to history and round messages
                    history_messages.append(coach_message)
                    round_messages.append({
                        "coach_id": coach.id,
                        "coach_name": coach.name,
                        "content": accumulated,
                        "role": "assistant",
                    })

                    yield f"data: {json.dumps({'type': 'coach_end', 'coach_id': coach.id})}\n\n"

                yield f"data: {json.dumps({'type': 'round_end', 'round': round_num})}\n\n"

                # ========== MODERATOR SUMMARY (after each round in moderated mode) ==========
                if is_moderated and moderator:
                    yield f"data: {json.dumps({'type': 'moderator_start', 'message_type': 'summary', 'coach_id': moderator.id, 'coach_name': moderator.name, 'coach_avatar': moderator.avatar_url})}\n\n"

                    summary_prompt = _build_moderator_summary_prompt(moderator, coaches, round_messages)
                    if kb_timing in ("message", "round", "moderator"):
                        kb_text = kb_message_text
                        if kb_timing == "round":
                            kb_text = kb_round_text
                        elif kb_timing == "moderator":
                            kb_text = await get_kb_text(
                                f"moderator:summary:{round_num}",
                                build_kb_query_with_history(),
                            )
                        if kb_text:
                            summary_prompt = f"{summary_prompt}\n\n{kb_text}"
                    config = LLMConfig(
                        model=model,
                        temperature=(temperature_override if temperature_override is not None else (moderator.temperature or 0.7)),
                        max_tokens=(max_tokens_override if max_tokens_override is not None else 400),
                        stream=True,
                    )

                    accumulated = ""
                    try:
                        async for chunk in stream_llm_response(summary_prompt, config):
                            accumulated += chunk
                            yield f"data: {json.dumps({'type': 'content', 'coach_id': moderator.id, 'content': chunk})}\n\n"
                            await asyncio.sleep(0.01)
                    except Exception as e:
                        logger.error(f"Error streaming moderator summary: {e}")
                        accumulated = "感谢各位教练的精彩分享。让我们继续深入探讨这个问题。"
                        yield f"data: {json.dumps({'type': 'content', 'coach_id': moderator.id, 'content': accumulated})}\n\n"

                    # Save moderator summary message
                    summary_message = RoundtableMessage(
                        id=uuid.uuid4(),
                        session_id=session.id,
                        coach_id=moderator.id,
                        role="assistant",
                        content=accumulated,
                        message_type="summary",
                        turn_number=session.round_count + round_num,
                        sequence_in_turn=len(coaches) + 1,
                        created_at=datetime.utcnow(),
                    )
                    db.add(summary_message)
                    session.message_count = (session.message_count or 0) + 1
                    history_messages.append(summary_message)

                    yield f"data: {json.dumps({'type': 'moderator_end', 'message_type': 'summary', 'coach_id': moderator.id})}\n\n"

            # ========== MODERATOR CLOSING (if requested) ==========
            if is_moderated and moderator and request.should_end:
                yield f"data: {json.dumps({'type': 'moderator_start', 'message_type': 'closing', 'coach_id': moderator.id, 'coach_name': moderator.name, 'coach_avatar': moderator.avatar_url})}\n\n"

                # Prepare all messages for closing
                all_messages = [
                    {
                        "coach_id": msg.coach_id,
                        "coach_name": next((c.name for c in coaches if c.id == msg.coach_id), moderator.name if msg.coach_id == moderator.id else "教练"),
                        "content": msg.content,
                        "role": msg.role,
                    }
                    for msg in history_messages
                ]

                closing_prompt = _build_moderator_closing_prompt(moderator, coaches, all_messages)
                if kb_timing in ("message", "moderator"):
                    kb_text = kb_message_text
                    if kb_timing == "moderator":
                        kb_text = await get_kb_text("moderator:closing", build_kb_query_with_history())
                    if kb_text:
                        closing_prompt = f"{closing_prompt}\n\n{kb_text}"
                config = LLMConfig(
                    model=model,
                    temperature=(temperature_override if temperature_override is not None else (moderator.temperature or 0.7)),
                    max_tokens=(max_tokens_override if max_tokens_override is not None else 500),
                    stream=True,
                )

                accumulated = ""
                try:
                    async for chunk in stream_llm_response(closing_prompt, config):
                        accumulated += chunk
                        yield f"data: {json.dumps({'type': 'content', 'coach_id': moderator.id, 'content': chunk})}\n\n"
                        await asyncio.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error streaming moderator closing: {e}")
                    accumulated = "感谢各位教练的精彩分享和用户的积极参与。希望今天的讨论对您有所帮助，欢迎随时开启新的讨论！"
                    yield f"data: {json.dumps({'type': 'content', 'coach_id': moderator.id, 'content': accumulated})}\n\n"

                # Save moderator closing message
                closing_message = RoundtableMessage(
                    id=uuid.uuid4(),
                    session_id=session.id,
                    coach_id=moderator.id,
                    role="assistant",
                    content=accumulated,
                    message_type="closing",
                    turn_number=session.round_count + request.max_rounds,
                    sequence_in_turn=999,
                    created_at=datetime.utcnow(),
                )
                db.add(closing_message)
                session.message_count = (session.message_count or 0) + 1

                yield f"data: {json.dumps({'type': 'moderator_end', 'message_type': 'closing', 'coach_id': moderator.id})}\n\n"

            # Update session
            session.round_count = (session.round_count or 0) + request.max_rounds
            session.updated_at = datetime.utcnow()
            await db.commit()

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Roundtable chat error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_roundtable_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
