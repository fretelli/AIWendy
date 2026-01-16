"""Trading intervention API routes."""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from domain.user.models import User
from services.intervention_service import InterventionService

router = APIRouter(prefix="/intervention", tags=["intervention"])


# Request/Response models
class CheckTradeRequest(BaseModel):
    symbol: str
    direction: str
    position_size: float
    entry_price: float


class CheckTradeResponse(BaseModel):
    allowed: bool
    action: str
    reason: Optional[str]
    message: str
    intervention_id: Optional[UUID]
    checklist_required: bool = False


class AcknowledgeInterventionRequest(BaseModel):
    user_proceeded: bool = False
    user_notes: Optional[str] = None


class ChecklistItemRequest(BaseModel):
    id: str
    type: str
    question: str
    required: bool = False


class CreateChecklistRequest(BaseModel):
    name: str
    description: Optional[str] = None
    items: List[Dict[str, Any]]
    is_required: bool = False


class ChecklistResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    items: List[Dict[str, Any]]
    is_required: bool
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class CompleteChecklistRequest(BaseModel):
    checklist_id: UUID
    responses: Dict[str, Any]


class StartSessionRequest(BaseModel):
    max_daily_loss_limit: Optional[int] = None  # In cents
    max_trades_per_day: Optional[int] = None


class SessionResponse(BaseModel):
    id: UUID
    is_active: bool
    trades_count: int
    session_pnl: int
    max_daily_loss_limit: Optional[int]
    max_trades_per_day: Optional[int]
    started_at: str

    class Config:
        from_attributes = True


@router.post("/check-trade", response_model=CheckTradeResponse)
async def check_trade(
    request: CheckTradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a trade should be allowed or blocked."""
    service = InterventionService(db)

    trade_data = {
        "symbol": request.symbol,
        "direction": request.direction,
        "position_size": request.position_size,
        "entry_price": request.entry_price,
    }

    result = await service.check_trade_allowed(
        user_id=current_user.id,
        trade_data=trade_data,
    )

    return CheckTradeResponse(**result)


@router.post("/interventions/{intervention_id}/acknowledge")
async def acknowledge_intervention(
    intervention_id: UUID,
    request: AcknowledgeInterventionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge an intervention."""
    service = InterventionService(db)

    success = await service.acknowledge_intervention(
        intervention_id=intervention_id,
        user_proceeded=request.user_proceeded,
        user_notes=request.user_notes,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intervention not found",
        )

    return {"message": "Intervention acknowledged"}


@router.post("/checklists", response_model=ChecklistResponse)
async def create_checklist(
    request: CreateChecklistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a pre-trade checklist."""
    service = InterventionService(db)

    checklist = await service.create_checklist(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        items=request.items,
        is_required=request.is_required,
    )

    return ChecklistResponse(
        id=checklist.id,
        name=checklist.name,
        description=checklist.description,
        items=checklist.items,
        is_required=checklist.is_required,
        is_active=checklist.is_active,
        created_at=checklist.created_at.isoformat(),
    )


@router.get("/checklists", response_model=List[ChecklistResponse])
async def get_checklists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's checklists."""
    service = InterventionService(db)
    checklists = await service.get_user_checklists(user_id=current_user.id)

    return [
        ChecklistResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            items=c.items,
            is_required=c.is_required,
            is_active=c.is_active,
            created_at=c.created_at.isoformat(),
        )
        for c in checklists
    ]


@router.post("/checklists/complete")
async def complete_checklist(
    request: CompleteChecklistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete a checklist."""
    service = InterventionService(db)

    try:
        completion = await service.complete_checklist(
            user_id=current_user.id,
            checklist_id=request.checklist_id,
            responses=request.responses,
        )

        return {
            "id": completion.id,
            "all_required_completed": completion.all_required_completed,
            "completed_at": completion.completed_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/session/start", response_model=SessionResponse)
async def start_session(
    request: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a trading session."""
    service = InterventionService(db)

    session = await service.start_trading_session(
        user_id=current_user.id,
        max_daily_loss_limit=request.max_daily_loss_limit,
        max_trades_per_day=request.max_trades_per_day,
    )

    return SessionResponse(
        id=session.id,
        is_active=session.is_active,
        trades_count=session.trades_count,
        session_pnl=session.session_pnl,
        max_daily_loss_limit=session.max_daily_loss_limit,
        max_trades_per_day=session.max_trades_per_day,
        started_at=session.started_at.isoformat(),
    )
