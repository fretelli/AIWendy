"""Trading intervention service for real-time trade blocking and alerts."""

from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.analysis.models import BehaviorPattern
from domain.intervention.models import (
    PreTradeChecklist,
    PreTradeChecklistCompletion,
    TradingIntervention,
    TradingSession,
    InterventionAction,
    InterventionReason,
)
from domain.journal.models import Journal
from services.notification_service import NotificationService

logger = structlog.get_logger()


class InterventionService:
    """Service for managing trading interventions and pre-trade checklists."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_trade_allowed(
        self,
        user_id: UUID,
        trade_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check if a trade should be allowed or blocked.

        Returns:
            {
                "allowed": bool,
                "action": InterventionAction,
                "reason": Optional[InterventionReason],
                "message": str,
                "intervention_id": Optional[UUID]
            }
        """
        # Get active trading session
        session = await self._get_or_create_session(user_id)
        gate_token = trade_data.get("gate_token")
        if gate_token:
            gate_result = await self._consume_trade_gate(user_id, gate_token)
            if gate_result:
                return {
                    "allowed": True,
                    "action": InterventionAction.NONE,
                    "reason": None,
                    "message": "Trade allowed (gate confirmed)",
                    "intervention_id": None,
                    "gate_required": False,
                    "gate_token": gate_token,
                    "gate_expires_at": None,
                }

        # Check 1: Daily loss limit
        if session.max_daily_loss_limit and session.session_pnl <= -session.max_daily_loss_limit:
            intervention = await self._create_intervention(
                user_id=user_id,
                reason=InterventionReason.DAILY_LOSS_LIMIT_REACHED,
                action=InterventionAction.BLOCK_TRADE,
                message=f"Daily loss limit reached (${abs(session.session_pnl / 100):.2f}). Trading blocked for today.",
            )
            return self._build_intervention_response(
                intervention=intervention,
                session=session,
            )

        # Check 2: Max trades per day
        if session.max_trades_per_day and session.trades_count >= session.max_trades_per_day:
            intervention = await self._create_intervention(
                user_id=user_id,
                reason=InterventionReason.OVERTRADING_DETECTED,
                action=InterventionAction.BLOCK_TRADE,
                message=f"Maximum trades per day reached ({session.trades_count}). Take a break.",
            )
            return self._build_intervention_response(
                intervention=intervention,
                session=session,
            )

        # Check 3: Position size check
        position_size = trade_data.get("position_size", 0)
        entry_price = trade_data.get("entry_price", 0)
        trade_value = position_size * entry_price

        # Warn if position size is unusually large (>2x of typical)
        avg_position_value = await self._get_average_position_value(user_id)
        if avg_position_value > 0 and trade_value > avg_position_value * 2:
            intervention = await self._create_intervention(
                user_id=user_id,
                reason=InterventionReason.POSITION_SIZE_TOO_LARGE,
                action=InterventionAction.REQUIRE_CONFIRMATION,
                message=f"Position size (${trade_value:.2f}) is 2x larger than your average. Please confirm.",
                details={"trade_value": trade_value, "avg_value": avg_position_value},
            )
            return self._build_intervention_response(
                intervention=intervention,
                session=session,
            )

        # Check 4: Recent behavior patterns (risk)
        behavior_risk = await self._get_recent_behavior_risk(user_id)
        if behavior_risk:
            intervention = await self._create_intervention(
                user_id=user_id,
                reason=InterventionReason.EMOTIONAL_STATE_POOR,
                action=InterventionAction.WARN_USER,
                message=behavior_risk["message"],
                details=behavior_risk["details"],
            )
            return self._build_intervention_response(
                intervention=intervention,
                session=session,
            )

        # Check 5: Recent losses (revenge trading detection)
        recent_losses = await self._count_recent_consecutive_losses(user_id)
        if recent_losses >= 3:
            intervention = await self._create_intervention(
                user_id=user_id,
                reason=InterventionReason.REVENGE_TRADING_DETECTED,
                action=InterventionAction.WARN_USER,
                message=f"You've had {recent_losses} consecutive losses. Take a break to avoid revenge trading.",
            )
            return self._build_intervention_response(
                intervention=intervention,
                session=session,
            )

        # Check 6: Required checklist completion
        checklist_result = await self._check_required_checklists(user_id)
        if not checklist_result["completed"]:
            intervention = await self._create_intervention(
                user_id=user_id,
                reason=InterventionReason.CHECKLIST_INCOMPLETE,
                action=InterventionAction.BLOCK_TRADE,
                message="Please complete your pre-trade checklist before trading.",
                details=checklist_result,
            )
            response = self._build_intervention_response(
                intervention=intervention,
                session=session,
            )
            response["checklist_required"] = True
            return response

        # All checks passed
        return {
            "allowed": True,
            "action": InterventionAction.NONE,
            "reason": None,
            "message": "Trade allowed",
            "intervention_id": None,
            "gate_required": False,
            "gate_token": None,
            "gate_expires_at": None,
        }

    async def acknowledge_intervention(
        self,
        intervention_id: UUID,
        user_proceeded: bool = False,
        user_notes: Optional[str] = None,
    ):
        """Acknowledge an intervention."""
        intervention = await self.db.get(TradingIntervention, intervention_id)
        if not intervention:
            return False

        intervention.user_acknowledged = True
        intervention.user_proceeded = user_proceeded
        intervention.user_notes = user_notes
        intervention.acknowledged_at = datetime.utcnow()

        await self.db.commit()
        return True

    def _build_intervention_response(
        self,
        intervention: TradingIntervention,
        session: TradingSession,
    ) -> Dict[str, Any]:
        """Build response payload for an intervention, honoring gate settings."""
        enforce_gate = (
            session.enforce_trade_block
            and intervention.action in [InterventionAction.WARN_USER, InterventionAction.REQUIRE_CONFIRMATION]
        )

        action = (
            InterventionAction.REQUIRE_CONFIRMATION
            if enforce_gate
            else intervention.action
        )

        allowed = action == InterventionAction.WARN_USER and not enforce_gate
        if intervention.action == InterventionAction.BLOCK_TRADE:
            allowed = False

        return {
            "allowed": allowed,
            "action": action,
            "reason": intervention.reason,
            "message": intervention.message,
            "intervention_id": intervention.id,
            "gate_required": action == InterventionAction.REQUIRE_CONFIRMATION,
            "gate_token": None,
            "gate_expires_at": None,
        }

    async def open_trade_gate(
        self,
        intervention_id: UUID,
        user_id: UUID,
        user_notes: Optional[str] = None,
    ) -> Optional[TradingIntervention]:
        """Open a temporary trade gate for an intervention."""
        intervention = await self.db.get(TradingIntervention, intervention_id)
        if not intervention or intervention.user_id != user_id:
            return None
        if intervention.action == InterventionAction.BLOCK_TRADE:
            return None

        now = datetime.utcnow()
        if (
            intervention.gate_token
            and intervention.gate_expires_at
            and intervention.gate_expires_at > now
            and intervention.gate_used_at is None
        ):
            return intervention

        session = await self._get_or_create_session(user_id)
        intervention.user_acknowledged = True
        intervention.user_proceeded = True
        intervention.user_notes = user_notes
        intervention.acknowledged_at = now
        intervention.gate_token = uuid4()
        intervention.gate_expires_at = now + timedelta(
            minutes=session.gate_timeout_minutes or 15
        )
        intervention.gate_used_at = None

        await self.db.commit()
        await self.db.refresh(intervention)
        return intervention

    async def create_checklist(
        self,
        user_id: UUID,
        name: str,
        items: List[Dict[str, Any]],
        description: Optional[str] = None,
        is_required: bool = False,
    ) -> PreTradeChecklist:
        """Create a pre-trade checklist."""
        checklist = PreTradeChecklist(
            user_id=user_id,
            name=name,
            description=description,
            items=items,
            is_required=is_required,
        )
        self.db.add(checklist)
        await self.db.commit()
        await self.db.refresh(checklist)
        return checklist

    async def complete_checklist(
        self,
        user_id: UUID,
        checklist_id: UUID,
        responses: Dict[str, Any],
    ) -> PreTradeChecklistCompletion:
        """Record checklist completion."""
        checklist = await self.db.get(PreTradeChecklist, checklist_id)
        if not checklist:
            raise ValueError("Checklist not found")

        # Check if all required items are completed
        all_required_completed = True
        for item in checklist.items:
            if item.get("required", False):
                item_id = item.get("id")
                if not responses.get(item_id, {}).get("checked", False):
                    all_required_completed = False
                    break

        completion = PreTradeChecklistCompletion(
            user_id=user_id,
            checklist_id=checklist_id,
            responses=responses,
            all_required_completed=all_required_completed,
        )
        self.db.add(completion)
        await self.db.commit()
        await self.db.refresh(completion)
        return completion

    async def get_user_checklists(self, user_id: UUID) -> List[PreTradeChecklist]:
        """Get user's checklists."""
        query = select(PreTradeChecklist).where(
            PreTradeChecklist.user_id == user_id,
            PreTradeChecklist.is_active == True,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def start_trading_session(
        self,
        user_id: UUID,
        max_daily_loss_limit: Optional[int] = None,
        max_trades_per_day: Optional[int] = None,
        enforce_trade_block: bool = False,
        gate_timeout_minutes: Optional[int] = None,
    ) -> TradingSession:
        """Start a new trading session."""
        # End any existing active sessions
        await self._end_active_sessions(user_id)

        session = TradingSession(
            user_id=user_id,
            max_daily_loss_limit=max_daily_loss_limit,
            max_trades_per_day=max_trades_per_day,
            enforce_trade_block=enforce_trade_block,
            gate_timeout_minutes=gate_timeout_minutes or 15,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def update_session_stats(
        self,
        user_id: UUID,
        trade_pnl: int,
    ):
        """Update trading session statistics."""
        session = await self._get_or_create_session(user_id)
        session.trades_count += 1
        session.session_pnl += trade_pnl
        await self.db.commit()

    async def _get_or_create_session(self, user_id: UUID) -> TradingSession:
        """Get or create active trading session."""
        # Check for active session today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        query = select(TradingSession).where(
            and_(
                TradingSession.user_id == user_id,
                TradingSession.is_active == True,
                TradingSession.started_at >= today_start,
            )
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            session = TradingSession(user_id=user_id)
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

        return session

    async def _end_active_sessions(self, user_id: UUID):
        """End all active sessions for user."""
        query = select(TradingSession).where(
            TradingSession.user_id == user_id,
            TradingSession.is_active == True,
        )
        result = await self.db.execute(query)
        sessions = result.scalars().all()

        for session in sessions:
            session.is_active = False
            session.ended_at = datetime.utcnow()

        await self.db.commit()

    async def _create_intervention(
        self,
        user_id: UUID,
        reason: InterventionReason,
        action: InterventionAction,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> TradingIntervention:
        """Create an intervention record."""
        intervention = TradingIntervention(
            user_id=user_id,
            reason=reason,
            action=action,
            message=message,
            details=details,
        )
        self.db.add(intervention)
        await self.db.commit()
        await self.db.refresh(intervention)

        # Send notification if action is blocking or warning
        if action in [InterventionAction.BLOCK_TRADE, InterventionAction.WARN_USER]:
            notification_service = NotificationService(self.db)
            await notification_service.send_risk_alert(
                user_id=user_id,
                risk_level=action.value,
                message=message,
            )

        return intervention

    async def _get_average_position_value(self, user_id: UUID) -> float:
        """Get user's average position value."""
        # Get last 20 trades
        query = (
            select(Journal)
            .where(Journal.user_id == user_id)
            .order_by(Journal.created_at.desc())
            .limit(20)
        )
        result = await self.db.execute(query)
        trades = list(result.scalars().all())

        if not trades:
            return 0

        total_value = sum(
            t.entry_price * t.position_size
            for t in trades
            if t.entry_price and t.position_size
        )
        return total_value / len(trades)

    async def _count_recent_consecutive_losses(self, user_id: UUID) -> int:
        """Count recent consecutive losing trades."""
        query = (
            select(Journal)
            .where(Journal.user_id == user_id)
            .order_by(Journal.created_at.desc())
            .limit(10)
        )
        result = await self.db.execute(query)
        trades = list(result.scalars().all())

        consecutive_losses = 0
        for trade in trades:
            if trade.pnl_amount is not None and trade.pnl_amount < 0:
                consecutive_losses += 1
            else:
                break

        return consecutive_losses

    async def _consume_trade_gate(self, user_id: UUID, gate_token: str) -> bool:
        """Validate and consume a gate token."""
        try:
            token_uuid = UUID(str(gate_token))
        except Exception:
            return False

        now = datetime.utcnow()
        query = select(TradingIntervention).where(
            TradingIntervention.user_id == user_id,
            TradingIntervention.gate_token == token_uuid,
            TradingIntervention.gate_expires_at.isnot(None),
            TradingIntervention.gate_expires_at > now,
            TradingIntervention.gate_used_at.is_(None),
        )
        result = await self.db.execute(query)
        intervention = result.scalar_one_or_none()
        if not intervention:
            return False

        intervention.gate_used_at = now
        await self.db.commit()
        return True

    async def _get_recent_behavior_risk(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Return recent behavior risk summary if present."""
        since = datetime.utcnow() - timedelta(hours=24)
        query = (
            select(BehaviorPattern)
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.detected_at >= since,
                BehaviorPattern.resolved_at.is_(None),
            )
            .order_by(BehaviorPattern.detected_at.desc())
            .limit(5)
        )
        result = await self.db.execute(query)
        patterns = list(result.scalars().all())

        if not patterns:
            return None

        top = max(patterns, key=lambda p: p.severity or p.confidence_score or 0)
        severity = top.severity or max(1, int((top.confidence_score or 0) * 5))

        message = (
            f"Recent behavioral risk detected (severity {severity}/5). "
            "Consider a brief pause or checklist before trading."
        )

        details = {
            "severity": severity,
            "pattern_types": [p.pattern_type.value for p in patterns],
            "confidence_scores": [p.confidence_score for p in patterns],
        }
        return {"message": message, "details": details}

    async def _check_required_checklists(self, user_id: UUID) -> Dict[str, Any]:
        """Check if required checklists are completed today."""
        # Get required checklists
        query = select(PreTradeChecklist).where(
            PreTradeChecklist.user_id == user_id,
            PreTradeChecklist.is_active == True,
            PreTradeChecklist.is_required == True,
        )
        result = await self.db.execute(query)
        required_checklists = list(result.scalars().all())

        if not required_checklists:
            return {"completed": True, "required_checklists": []}

        # Check if completed today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        incomplete_checklists = []
        for checklist in required_checklists:
            completion_query = select(PreTradeChecklistCompletion).where(
                PreTradeChecklistCompletion.user_id == user_id,
                PreTradeChecklistCompletion.checklist_id == checklist.id,
                PreTradeChecklistCompletion.completed_at >= today_start,
                PreTradeChecklistCompletion.all_required_completed == True,
            )
            completion_result = await self.db.execute(completion_query)
            completion = completion_result.scalar_one_or_none()

            if not completion:
                incomplete_checklists.append({
                    "id": str(checklist.id),
                    "name": checklist.name,
                })

        return {
            "completed": len(incomplete_checklists) == 0,
            "required_checklists": incomplete_checklists,
        }
