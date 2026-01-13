"""Journal repository implementation."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger

from .models import Journal, TradeResult
from .schemas import JournalFilter, JournalStatistics

logger = get_logger(__name__)


class JournalRepository:
    """Repository for journal operations."""

    def __init__(self, session: AsyncSession):
        """Initialize journal repository."""
        self.session = session

    async def create(self, journal: Journal) -> Journal:
        """Create a new journal entry."""
        try:
            self.session.add(journal)
            await self.session.commit()
            await self.session.refresh(journal)
            logger.info(
                f"Created journal entry {journal.id} for user {journal.user_id}"
            )
            return journal
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create journal entry: {e}")
            raise

    async def get_by_id(self, journal_id: UUID, user_id: UUID) -> Optional[Journal]:
        """Get journal entry by ID for a specific user."""
        query = select(Journal).where(
            and_(
                Journal.id == journal_id,
                Journal.user_id == user_id,
                Journal.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_journals(
        self,
        user_id: UUID,
        filter_params: Optional[JournalFilter] = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "trade_date",
    ) -> tuple[List[Journal], int]:
        """Get journals for a user with optional filtering."""
        # Base query
        base_filter = and_(Journal.user_id == user_id, Journal.deleted_at.is_(None))
        query = select(Journal).where(base_filter)
        count_query = select(func.count()).select_from(Journal).where(base_filter)

        # Apply filters if provided
        if filter_params:
            conditions = []

            if filter_params.symbol:
                # Escape SQL LIKE wildcards to prevent injection
                symbol_escaped = (
                    filter_params.symbol.replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                )
                conditions.append(Journal.symbol.ilike(f"%{symbol_escaped}%", escape="\\"))

            if filter_params.project_id:
                conditions.append(Journal.project_id == filter_params.project_id)

            if filter_params.market:
                conditions.append(Journal.market == filter_params.market)

            if filter_params.direction:
                conditions.append(Journal.direction == filter_params.direction)

            if filter_params.result:
                conditions.append(Journal.result == filter_params.result)

            if filter_params.date_from:
                conditions.append(Journal.trade_date >= filter_params.date_from)

            if filter_params.date_to:
                conditions.append(Journal.trade_date <= filter_params.date_to)

            if filter_params.followed_rules is not None:
                conditions.append(
                    Journal.followed_rules == filter_params.followed_rules
                )

            if conditions:
                filter_clause = and_(*conditions)
                query = query.where(filter_clause)
                count_query = count_query.where(filter_clause)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Apply ordering
        if order_by == "trade_date":
            query = query.order_by(desc(Journal.trade_date))
        elif order_by == "pnl":
            query = query.order_by(desc(Journal.pnl_amount))
        else:
            query = query.order_by(desc(Journal.created_at))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(query)
        journals = result.scalars().all()

        return journals, total

    async def update(self, journal: Journal) -> Journal:
        """Update an existing journal entry."""
        try:
            journal.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(journal)
            logger.info(f"Updated journal entry {journal.id}")
            return journal
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update journal entry: {e}")
            raise

    async def delete(self, journal_id: UUID, user_id: UUID) -> bool:
        """Delete a journal entry (soft delete)."""
        journal = await self.get_by_id(journal_id, user_id)
        if not journal:
            return False

        journal.deleted_at = datetime.utcnow()
        await self.session.commit()
        logger.info(f"Soft deleted journal entry {journal_id}")
        return True

    async def get_user_statistics(self, user_id: UUID) -> JournalStatistics:
        """Get trading statistics for a user."""
        # Get all non-deleted journals for the user
        query = select(Journal).where(
            and_(Journal.user_id == user_id, Journal.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        journals = result.scalars().all()

        if not journals:
            return JournalStatistics()

        stats = JournalStatistics()
        confidence_sum = 0.0
        confidence_count = 0
        stress_sum = 0.0
        stress_count = 0
        rule_violation_count = 0

        # Count trades by result
        for journal in journals:
            stats.total_trades += 1

            if journal.pnl_amount is not None:
                stats.total_pnl += journal.pnl_amount

            if journal.result == TradeResult.WIN:
                stats.winning_trades += 1
                if journal.pnl_amount is not None:
                    stats.average_win = (
                        stats.average_win * (stats.winning_trades - 1)
                        + journal.pnl_amount
                    ) / stats.winning_trades
                    stats.best_trade = max(stats.best_trade, journal.pnl_amount)

            elif journal.result == TradeResult.LOSS:
                stats.losing_trades += 1
                if journal.pnl_amount is not None:
                    stats.average_loss = (
                        stats.average_loss * (stats.losing_trades - 1)
                        + journal.pnl_amount
                    ) / stats.losing_trades
                    stats.worst_trade = min(stats.worst_trade, journal.pnl_amount)

            elif journal.result == TradeResult.BREAKEVEN:
                stats.breakeven_trades += 1

            elif journal.result == TradeResult.OPEN:
                stats.open_trades += 1

            # Psychology metrics
            if journal.confidence_level is not None:
                confidence_sum += journal.confidence_level
                confidence_count += 1

            if journal.stress_level is not None:
                stress_sum += journal.stress_level
                stress_count += 1

            if not journal.followed_rules:
                rule_violation_count += 1

        # Calculate ratios
        closed_trades = (
            stats.winning_trades + stats.losing_trades + stats.breakeven_trades
        )
        if closed_trades > 0:
            stats.win_rate = (stats.winning_trades / closed_trades) * 100

        if stats.average_loss != 0:
            stats.profit_factor = abs(stats.average_win / stats.average_loss)

        if confidence_count > 0:
            stats.average_confidence = confidence_sum / confidence_count

        if stress_count > 0:
            stats.average_stress = stress_sum / stress_count

        if stats.total_trades > 0:
            stats.rule_violation_rate = (
                rule_violation_count / stats.total_trades
            ) * 100

        # Calculate streaks
        sorted_journals = sorted(
            [j for j in journals if j.result in [TradeResult.WIN, TradeResult.LOSS]],
            key=lambda x: x.trade_date or x.created_at,
        )

        current_streak = 0
        for journal in sorted_journals:
            if journal.result == TradeResult.WIN:
                if current_streak >= 0:
                    current_streak += 1
                else:
                    current_streak = 1
                stats.best_streak = max(stats.best_streak, current_streak)
            else:  # Loss
                if current_streak <= 0:
                    current_streak -= 1
                else:
                    current_streak = -1
                stats.worst_streak = min(stats.worst_streak, current_streak)

        stats.current_streak = current_streak

        return stats

    async def get_recent_journals(
        self, user_id: UUID, days: int = 7, limit: int = 10
    ) -> List[Journal]:
        """Get recent journal entries for a user."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(Journal)
            .where(
                and_(
                    Journal.user_id == user_id,
                    Journal.trade_date >= cutoff_date,
                    Journal.deleted_at.is_(None),
                )
            )
            .order_by(desc(Journal.trade_date))
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_journals(
        self, user_id: UUID, search_term: str, limit: int = 20
    ) -> List[Journal]:
        """Search journals by text in notes, symbols, or tags."""
        query = (
            select(Journal)
            .where(
                and_(
                    Journal.user_id == user_id,
                    Journal.deleted_at.is_(None),
                    or_(
                        Journal.symbol.ilike(f"%{search_term}%"),
                        Journal.notes.ilike(f"%{search_term}%"),
                        Journal.setup_description.ilike(f"%{search_term}%"),
                        Journal.exit_reason.ilike(f"%{search_term}%"),
                        Journal.lessons_learned.ilike(f"%{search_term}%"),
                        Journal.strategy_name.ilike(f"%{search_term}%"),
                    ),
                )
            )
            .order_by(desc(Journal.trade_date))
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()
