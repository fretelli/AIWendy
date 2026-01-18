"""Coach management endpoints."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from core.i18n import Locale, get_request_locale, t
from domain.coach.models import ChatMessage, ChatSession, Coach, CoachStyle, LLMProvider
from domain.user.models import User
from services.coach_service import CoachService


# Pydantic models for request/response
class CoachResponse(BaseModel):
    id: str
    name: str
    avatar_url: Optional[str]
    description: Optional[str]
    bio: Optional[str]
    style: str
    personality_traits: List[str]
    specialty: List[str]
    language: str
    is_premium: bool
    is_public: bool
    total_sessions: int
    avg_rating: Optional[float]
    rating_count: int

    class Config:
        orm_mode = True


class CreateSessionRequest(BaseModel):
    coach_id: str
    project_id: Optional[UUID] = None
    title: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    mood_before: Optional[int] = None


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    coach_id: str
    project_id: Optional[UUID]
    title: Optional[str]
    context: Optional[Dict]
    mood_before: Optional[int]
    mood_after: Optional[int]
    message_count: int
    total_tokens: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class EndSessionRequest(BaseModel):
    mood_after: Optional[int] = None
    user_rating: Optional[int] = None
    user_feedback: Optional[str] = None


class MessageRequest(BaseModel):
    content: str
    metadata: Optional[Dict] = None


class CreateCustomCoachRequest(BaseModel):
    """Create a custom coach (self-hosted friendly)."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    bio: Optional[str] = Field(None, max_length=5000)
    avatar_url: Optional[str] = None

    style: CoachStyle = CoachStyle.EMPATHETIC
    personality_traits: List[str] = Field(default_factory=list)
    specialty: List[str] = Field(default_factory=list)
    language: str = Field(default="en", max_length=10)

    llm_provider: LLMProvider = LLMProvider.OPENAI
    llm_model: str = Field(default="gpt-4o-mini", min_length=1, max_length=100)
    system_prompt: str = Field(..., min_length=20, max_length=10000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=100, le=8000)

    is_public: bool = False


class UpdateCustomCoachRequest(BaseModel):
    """Update a custom coach."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    bio: Optional[str] = Field(None, max_length=5000)
    avatar_url: Optional[str] = None

    style: Optional[CoachStyle] = None
    personality_traits: Optional[List[str]] = None
    specialty: Optional[List[str]] = None
    language: Optional[str] = Field(None, max_length=10)

    llm_provider: Optional[LLMProvider] = None
    llm_model: Optional[str] = Field(None, min_length=1, max_length=100)
    system_prompt: Optional[str] = Field(None, min_length=20, max_length=10000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=8000)

    is_public: Optional[bool] = None
    is_active: Optional[bool] = None


class CustomCoachResponse(BaseModel):
    id: str
    name: str
    avatar_url: Optional[str]
    description: Optional[str]
    bio: Optional[str]
    style: str
    personality_traits: List[str]
    specialty: List[str]
    language: str
    is_public: bool
    is_active: bool

    llm_provider: str
    llm_model: str
    system_prompt: str
    temperature: float
    max_tokens: int

    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


router = APIRouter()

_DEFAULT_COACH_TRAITS_EN: dict[str, list[str]] = {
    "wendy": ["Warm", "Patient", "Empathetic", "Insightful", "Supportive"],
    "marcus": ["Strict", "Direct", "Decisive", "High standards", "Results-driven"],
    "sophia": ["Rational", "Precise", "Objective", "Systematic", "Data-driven"],
    "alex": ["Passionate", "Optimistic", "Encouraging", "High energy", "Positive"],
    "socrates": ["Wise", "Patient", "Deep", "Guiding", "Reflective"],
}

_DEFAULT_COACH_SPECIALTY_EN: dict[str, list[str]] = {
    "wendy": [
        "Emotional regulation",
        "Mental resilience",
        "Confidence rebuilding",
        "Stress management",
        "Recovery after setbacks",
    ],
    "marcus": [
        "Risk management",
        "Discipline & execution",
        "Stop-loss rules",
        "Process design",
        "Habit building",
    ],
    "sophia": [
        "Performance analytics",
        "Pattern recognition",
        "Statistical optimization",
        "Backtesting",
        "Quant improvement",
    ],
    "alex": [
        "Confidence building",
        "Goal setting",
        "Motivation",
        "Winning mindset",
        "Breaking limiting beliefs",
    ],
    "socrates": [
        "Self-awareness",
        "Critical thinking",
        "Deep reflection",
        "Belief challenging",
        "Mental clarity",
    ],
}


def _localize_default_coach_response(coach: Coach, locale: Locale) -> CoachResponse:
    response = CoachResponse.from_orm(coach)
    if not getattr(coach, "is_default", False):
        return response

    updates = {
        "name": t(f"coaches.{coach.id}.name", locale),
        "description": t(f"coaches.{coach.id}.description", locale),
        "bio": t(f"coaches.{coach.id}.bio", locale),
        "language": "zh" if locale == "zh" else "en",
    }

    if locale == "en":
        traits = _DEFAULT_COACH_TRAITS_EN.get(coach.id)
        specialty = _DEFAULT_COACH_SPECIALTY_EN.get(coach.id)
        if traits is not None:
            updates["personality_traits"] = traits
        if specialty is not None:
            updates["specialty"] = specialty

    return response.copy(
        update={
            **updates,
        }
    )


@router.get("", response_model=List[CoachResponse])
@router.get("/", response_model=List[CoachResponse])
async def list_coaches(
    http_request: Request,
    style: Optional[CoachStyle] = Query(None, description="Filter by coach style"),
    is_premium: Optional[bool] = Query(None, description="Filter by premium status"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List available coaches."""
    from sqlalchemy import or_, select

    locale = get_request_locale(http_request)

    # Build query
    query = select(Coach).where(
        Coach.is_active == True,
        or_(
            Coach.is_public == True,
            Coach.created_by == current_user.id,
        ),
    )

    if style:
        query = query.where(Coach.style == style)
    if is_premium is not None:
        query = query.where(Coach.is_premium == is_premium)

    # Execute query
    result = await db.execute(query)
    coaches = result.scalars().all()

    # Filter coaches based on user subscription tier
    tier_levels = {"free": 0, "pro": 1, "elite": 2, "enterprise": 3}
    user_tier_level = tier_levels.get(current_user.subscription_tier.value, 0)

    filtered_coaches = []
    for coach in coaches:
        coach_min_tier = coach.min_subscription_tier or "free"
        coach_tier_level = tier_levels.get(coach_min_tier, 0)

        # User can access coach if their tier is >= coach's minimum tier
        if user_tier_level >= coach_tier_level:
            filtered_coaches.append(coach)

    return [
        _localize_default_coach_response(coach, locale) for coach in filtered_coaches
    ]


@router.get("/default", response_model=CoachResponse)
async def get_default_coach(
    http_request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get the default coach."""
    from sqlalchemy import select

    locale = get_request_locale(http_request)

    # Query for default coach (wendy)
    query = select(Coach).where(Coach.id == "wendy", Coach.is_active == True)
    result = await db.execute(query)
    coach = result.scalar_one_or_none()

    if not coach:
        raise HTTPException(
            status_code=404, detail=t("errors.no_default_coach_configured", locale)
        )

    return _localize_default_coach_response(coach, locale)


@router.get("/{coach_id}", response_model=CoachResponse)
async def get_coach(
    coach_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get coach details."""
    from sqlalchemy import select

    locale = get_request_locale(http_request)

    # Query for the coach
    query = select(Coach).where(Coach.id == coach_id, Coach.is_active == True)
    result = await db.execute(query)
    coach = result.scalar_one_or_none()

    if not coach:
        raise HTTPException(status_code=404, detail=t("errors.coach_not_found", locale))

    # Access control: public coaches or the user's own custom coaches
    if not coach.is_public and coach.created_by != current_user.id:
        raise HTTPException(status_code=403, detail=t("errors.access_denied", locale))

    return _localize_default_coach_response(coach, locale)


def _generate_custom_coach_id() -> str:
    return f"custom_{uuid.uuid4().hex[:12]}"


@router.get("/custom", response_model=List[CustomCoachResponse])
async def list_custom_coaches(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List the current user's custom coaches."""
    from sqlalchemy import desc, select

    result = await db.execute(
        select(Coach)
        .where(Coach.created_by == current_user.id)
        .order_by(desc(Coach.created_at))
    )
    return result.scalars().all()


@router.post("/custom", response_model=CustomCoachResponse)
async def create_custom_coach(
    request: CreateCustomCoachRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new custom coach for the current user."""
    from sqlalchemy import select

    locale = get_request_locale(http_request)

    coach_id: Optional[str] = None
    for _ in range(8):
        candidate = _generate_custom_coach_id()
        exists = await db.execute(select(Coach.id).where(Coach.id == candidate))
        if exists.scalar_one_or_none() is None:
            coach_id = candidate
            break
    if not coach_id:
        raise HTTPException(
            status_code=500, detail=t("errors.failed_allocate_coach_id", locale)
        )

    coach = Coach(
        id=coach_id,
        name=request.name,
        avatar_url=request.avatar_url,
        description=request.description,
        bio=request.bio,
        style=request.style,
        personality_traits=request.personality_traits,
        specialty=request.specialty,
        language=request.language
        or (current_user.language if getattr(current_user, "language", None) else "en"),
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        is_premium=False,
        is_public=request.is_public,
        min_subscription_tier="free",
        created_by=current_user.id,
        is_active=True,
        is_default=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(coach)
    await db.commit()
    await db.refresh(coach)
    return coach


@router.patch("/custom/{coach_id}", response_model=CustomCoachResponse)
async def update_custom_coach(
    coach_id: str,
    request: UpdateCustomCoachRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update one of the current user's custom coaches."""
    from sqlalchemy import select

    locale = get_request_locale(http_request)

    result = await db.execute(select(Coach).where(Coach.id == coach_id))
    coach = result.scalar_one_or_none()
    if not coach:
        raise HTTPException(status_code=404, detail=t("errors.coach_not_found", locale))
    if coach.created_by != current_user.id:
        raise HTTPException(status_code=403, detail=t("errors.access_denied", locale))

    updates = request.dict(exclude_unset=True)
    for key, value in updates.items():
        setattr(coach, key, value)
    coach.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(coach)
    return coach


@router.delete("/custom/{coach_id}")
async def delete_custom_coach(
    coach_id: str,
    http_request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Deactivate a custom coach."""
    from sqlalchemy import select

    locale = get_request_locale(http_request)

    result = await db.execute(select(Coach).where(Coach.id == coach_id))
    coach = result.scalar_one_or_none()
    if not coach:
        raise HTTPException(status_code=404, detail=t("errors.coach_not_found", locale))
    if coach.created_by != current_user.id:
        raise HTTPException(status_code=403, detail=t("errors.access_denied", locale))

    coach.is_active = False
    coach.updated_at = datetime.utcnow()
    await db.commit()

    return {"ok": True}


# Session Management Endpoints
@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Start a new chat session with a coach."""
    # Quick fix: Initialize coach service without DB check for now
    import uuid
    from datetime import datetime

    from domain.coach.models import ChatSession

    locale = get_request_locale(http_request)

    # Create session directly
    session = ChatSession(
        id=uuid.uuid4(),
        user_id=current_user.id,
        coach_id=request.coach_id,
        title=request.title
        or t(
            "chat.session_title_default",
            locale,
            ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
        context=request.context,
        project_id=request.project_id,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        message_count=0,
    )

    # Save to DB
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


@router.get("/sessions/user", response_model=List[SessionResponse])
async def get_user_sessions(
    coach_id: Optional[str] = Query(None, description="Filter by coach"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get user's chat sessions."""
    from sqlalchemy import desc, select

    # Build query
    query = select(ChatSession).where(ChatSession.user_id == current_user.id)

    if coach_id:
        query = query.where(ChatSession.coach_id == coach_id)
    if project_id:
        query = query.where(ChatSession.project_id == project_id)
    if is_active is not None:
        query = query.where(ChatSession.is_active == is_active)

    # Add ordering and limit
    query = query.order_by(desc(ChatSession.created_at)).limit(limit)

    # Execute query
    result = await db.execute(query)
    sessions = result.scalars().all()

    return sessions


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: UUID,
    http_request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get session details."""
    from sqlalchemy import select

    locale = get_request_locale(http_request)

    # Query for the session
    query = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=404, detail=t("errors.session_not_found", locale)
        )

    # Verify user owns this session
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail=t("errors.access_denied", locale))

    return session


@router.post("/sessions/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
    http_request: Request,
    request: EndSessionRequest = Body(...),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """End a chat session."""
    from sqlalchemy import select

    locale = get_request_locale(http_request)

    # Verify session ownership
    query = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=404, detail=t("errors.session_not_found", locale)
        )

    # End the session
    session.is_active = False
    session.mood_after = request.mood_after
    session.user_rating = request.user_rating
    session.user_feedback = request.user_feedback
    session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    return session


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: UUID,
    http_request: Request,
    limit: Optional[int] = Query(None, le=1000),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get messages from a chat session."""
    import logging

    from sqlalchemy import select

    logger = logging.getLogger(__name__)
    locale = get_request_locale(http_request)

    try:
        # Verify session ownership
        session_query = select(ChatSession).where(ChatSession.id == session_id)
        session_result = await db.execute(session_query)
        session = session_result.scalar_one_or_none()

        if not session or session.user_id != current_user.id:
            raise HTTPException(
                status_code=404, detail=t("errors.session_not_found", locale)
            )

        # Get messages
        messages_query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )

        if limit:
            messages_query = messages_query.limit(limit)

        messages_result = await db.execute(messages_query)
        messages = messages_result.scalars().all()

        # Safely serialize messages
        serialized_messages = []
        for msg in messages:
            try:
                serialized_messages.append(
                    {
                        "id": str(msg.id),
                        "role": msg.role,
                        "content": msg.content or "",
                        "created_at": (
                            msg.created_at.isoformat() if msg.created_at else None
                        ),
                        "metadata": (
                            msg.message_metadata if msg.message_metadata else {}
                        ),
                    }
                )
            except Exception as e:
                logger.error(f"Error serializing message {msg.id}: {str(e)}")
                # Skip problematic messages or use default values
                serialized_messages.append(
                    {
                        "id": str(msg.id),
                        "role": msg.role or "user",
                        "content": msg.content or "",
                        "created_at": None,
                        "metadata": {},
                    }
                )

        return {
            "session_id": str(session_id),
            "messages": serialized_messages,
            "total_count": len(serialized_messages),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting messages for session {session_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=t("errors.failed_to_retrieve_messages", locale),
        )
