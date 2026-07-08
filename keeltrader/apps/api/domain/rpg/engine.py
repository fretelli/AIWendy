"""RPG engine — pure Python calculations for trading character attributes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from domain.rpg.calculations import (
    calculate_consistency,
    calculate_decisiveness,
    calculate_discipline,
    calculate_level,
    calculate_patience,
    calculate_rank,
    calculate_risk_management,
    check_achievement_criteria,
)
from domain.rpg.models import (
    TradingCharacter, Achievement, UserAchievement,
    Quest, UserQuest, LeaderboardEntry,
    QuestStatus, QuestType, PeriodType,
)

logger = get_logger(__name__)

CST = timezone(timedelta(hours=8))


async def get_or_create_character(session: AsyncSession, user_id: UUID) -> TradingCharacter:
    """Get existing character or create a new one."""
    result = await session.execute(
        select(TradingCharacter).where(TradingCharacter.user_id == user_id)
    )
    character = result.scalar_one_or_none()

    if not character:
        character = TradingCharacter(user_id=user_id)
        session.add(character)
        await session.flush()

    return character


async def recalculate_character(session: AsyncSession, user_id: UUID) -> TradingCharacter:
    """Recalculate all character attributes from journal data."""
    from domain.journal.models import Journal

    character = await get_or_create_character(session, user_id)

    # Get all non-deleted journals
    result = await session.execute(
        select(Journal).where(
            Journal.user_id == user_id,
            Journal.deleted_at == None,
        ).order_by(Journal.trade_date.desc())
    )
    journals = list(result.scalars().all())

    if journals:
        character.discipline = calculate_discipline(journals)
        character.patience = calculate_patience(journals)
        character.risk_management = calculate_risk_management(journals)
        character.decisiveness = calculate_decisiveness(journals)
        character.consistency = calculate_consistency(journals)

    character.level = calculate_level(character.xp)
    character.rank = calculate_rank(character.level)

    return character


async def check_achievements(session: AsyncSession, user_id: UUID) -> list[Achievement]:
    """Check all achievements and return newly unlocked ones."""
    from domain.journal.models import Journal

    character = await get_or_create_character(session, user_id)

    # Get user's journals
    result = await session.execute(
        select(Journal).where(
            Journal.user_id == user_id,
            Journal.deleted_at == None,
        ).order_by(Journal.trade_date)
    )
    journals = list(result.scalars().all())

    # Get already unlocked achievement IDs
    result = await session.execute(
        select(UserAchievement.achievement_id).where(UserAchievement.user_id == user_id)
    )
    unlocked_ids = set(r[0] for r in result.all())

    # Get all achievement templates
    result = await session.execute(select(Achievement))
    all_achievements = result.scalars().all()

    newly_unlocked = []
    for achievement in all_achievements:
        if achievement.id in unlocked_ids:
            continue
        if check_achievement_criteria(achievement, journals, character):
            ua = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
            )
            session.add(ua)
            character.xp += achievement.xp_reward
            newly_unlocked.append(achievement)

    if newly_unlocked:
        character.level = calculate_level(character.xp)
        character.rank = calculate_rank(character.level)

    return newly_unlocked


async def check_quest_progress(session: AsyncSession, user_id: UUID) -> list[UserQuest]:
    """Check and update progress on active quests. Returns completed quests."""
    from domain.journal.models import Journal

    character = await get_or_create_character(session, user_id)

    # Get active quests
    result = await session.execute(
        select(UserQuest).where(
            UserQuest.user_id == user_id,
            UserQuest.status == QuestStatus.ACTIVE,
        )
    )
    active_quests = list(result.scalars().all())

    if not active_quests:
        return []

    # Get recent journals for quest evaluation
    now = datetime.now(CST)
    result = await session.execute(
        select(Journal).where(
            Journal.user_id == user_id,
            Journal.deleted_at == None,
            Journal.trade_date >= now - timedelta(days=7),
        ).order_by(Journal.trade_date)
    )
    recent_journals = list(result.scalars().all())

    completed = []
    for uq in active_quests:
        quest = uq.quest
        criteria = quest.criteria
        criteria_type = criteria.get("type")

        # Filter journals based on quest type timeframe
        if quest.quest_type.value == "daily":
            journals = [j for j in recent_journals
                       if j.trade_date and j.trade_date.date() == now.date()]
        else:
            journals = recent_journals

        current = 0
        target = criteria.get("count", 1)

        if criteria_type == "journal_with_notes":
            current = sum(1 for j in journals if j.notes)
        elif criteria_type == "trade_count":
            current = len(journals)
        elif criteria_type == "win_rate":
            if journals:
                wins = sum(1 for j in journals if j.result and j.result.value == "win")
                current = int(wins / len(journals) * 100) if journals else 0
                target = criteria.get("threshold", 60)
        elif criteria_type == "no_violations":
            current = sum(1 for j in journals if j.followed_rules and not j.rule_violations)
        elif criteria_type == "stop_loss_set":
            current = sum(1 for j in journals if j.stop_loss is not None)

        uq.progress = {"current": current, "target": target}

        if current >= target and uq.status == QuestStatus.ACTIVE:
            uq.status = QuestStatus.COMPLETED
            uq.completed_at = datetime.utcnow()
            character.xp += quest.xp_reward
            completed.append(uq)

    if completed:
        character.level = calculate_level(character.xp)
        character.rank = calculate_rank(character.level)

    return completed


async def refresh_daily_quests(session: AsyncSession, user_id: UUID):
    """Expire old daily quests and assign new ones."""
    now = datetime.utcnow()

    # Expire active daily quests from yesterday
    result = await session.execute(
        select(UserQuest).join(Quest).where(
            UserQuest.user_id == user_id,
            UserQuest.status == QuestStatus.ACTIVE,
            Quest.quest_type == QuestType.DAILY,
            UserQuest.started_at < now - timedelta(days=1),
        )
    )
    for uq in result.scalars().all():
        uq.status = QuestStatus.EXPIRED

    # Get all daily quest templates
    result = await session.execute(
        select(Quest).where(Quest.quest_type == QuestType.DAILY)
    )
    daily_quests = result.scalars().all()

    # Check which daily quests user already has active today
    result = await session.execute(
        select(UserQuest.quest_id).where(
            UserQuest.user_id == user_id,
            UserQuest.status == QuestStatus.ACTIVE,
        )
    )
    active_quest_ids = set(r[0] for r in result.all())

    # Assign up to 3 daily quests
    assigned = 0
    for quest in daily_quests:
        if quest.id in active_quest_ids:
            continue
        if assigned >= 3:
            break
        uq = UserQuest(
            user_id=user_id,
            quest_id=quest.id,
            progress={"current": 0, "target": quest.criteria.get("count", 1)},
        )
        session.add(uq)
        assigned += 1


async def update_leaderboard(session: AsyncSession, user_id: UUID):
    """Update leaderboard entry for current period."""
    from domain.journal.models import Journal

    now = datetime.now(CST)

    # Weekly period: Monday to Sunday
    week_start = (now - timedelta(days=now.weekday())).date()

    # Get user's journals for this week
    result = await session.execute(
        select(Journal).where(
            Journal.user_id == user_id,
            Journal.deleted_at == None,
            Journal.trade_date >= datetime.combine(week_start, datetime.min.time()),
        )
    )
    journals = list(result.scalars().all())

    # Get character
    result = await session.execute(
        select(TradingCharacter).where(TradingCharacter.user_id == user_id)
    )
    character = result.scalar_one_or_none()
    if not character:
        return

    # Get achievement count
    result = await session.execute(
        select(func.count()).select_from(UserAchievement).where(UserAchievement.user_id == user_id)
    )
    achievement_count = result.scalar() or 0

    # Calculate stats
    total = len(journals)
    wins = sum(1 for j in journals if j.result and j.result.value == "win")
    losses = sum(1 for j in journals if j.result and j.result.value == "loss")
    win_rate = (wins / total * 100) if total > 0 else 0
    total_profit = sum(j.pnl_amount for j in journals if j.pnl_amount and j.pnl_amount > 0)
    total_loss = abs(sum(j.pnl_amount for j in journals if j.pnl_amount and j.pnl_amount < 0))
    profit_factor = (total_profit / total_loss) if total_loss > 0 else total_profit

    # Upsert weekly entry
    result = await session.execute(
        select(LeaderboardEntry).where(
            LeaderboardEntry.user_id == user_id,
            LeaderboardEntry.period_type == PeriodType.WEEKLY,
            LeaderboardEntry.period_start == week_start,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        entry = LeaderboardEntry(
            user_id=user_id,
            period_type=PeriodType.WEEKLY,
            period_start=week_start,
        )
        session.add(entry)

    entry.xp = character.xp
    entry.win_rate = round(win_rate, 1)
    entry.profit_factor = round(profit_factor, 2)
    entry.achievement_count = achievement_count
