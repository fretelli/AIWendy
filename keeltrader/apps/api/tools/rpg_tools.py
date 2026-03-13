"""RPG tool implementations for MCP and REST API."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from domain.rpg.engine import (
    get_or_create_character,
    recalculate_character,
    check_achievements,
    check_quest_progress,
    update_leaderboard,
)
from domain.rpg.models import (
    Achievement,
    LeaderboardEntry,
    PeriodType,
    Quest,
    QuestStatus,
    TradingCharacter,
    UserAchievement,
    UserQuest,
)


async def get_character(session: AsyncSession, user_id: UUID, **kwargs) -> dict[str, Any]:
    """Get trading character data."""
    character = await get_or_create_character(session, user_id)
    await session.commit()

    result = await session.execute(
        select(func.count()).select_from(UserAchievement).where(UserAchievement.user_id == user_id)
    )
    achievement_count = result.scalar() or 0

    return {
        "nickname": character.nickname or "Trader",
        "level": character.level,
        "xp": character.xp,
        "rank": character.rank.value,
        "attributes": {
            "discipline": character.discipline,
            "patience": character.patience,
            "risk_management": character.risk_management,
            "decisiveness": character.decisiveness,
            "consistency": character.consistency,
        },
        "achievement_count": achievement_count,
    }


async def get_achievements_tool(session: AsyncSession, user_id: UUID, category: str = None, **kwargs) -> dict[str, Any]:
    """Get achievements list with unlock status."""
    query = select(Achievement)
    if category:
        query = query.where(Achievement.category == category)
    result = await session.execute(query)
    all_achievements = result.scalars().all()

    result = await session.execute(
        select(UserAchievement.achievement_id).where(UserAchievement.user_id == user_id)
    )
    unlocked_ids = set(r[0] for r in result.all())

    return {
        "achievements": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "category": a.category.value,
                "rarity": a.rarity.value,
                "xp_reward": a.xp_reward,
                "unlocked": a.id in unlocked_ids,
            }
            for a in all_achievements
        ],
        "total": len(all_achievements),
        "unlocked": len(unlocked_ids),
    }


async def start_quest_tool(session: AsyncSession, user_id: UUID, quest_id: str = "", **kwargs) -> dict[str, Any]:
    """Start a quest."""
    if not quest_id:
        return {"error": "quest_id is required"}

    result = await session.execute(select(Quest).where(Quest.id == quest_id))
    quest = result.scalar_one_or_none()
    if not quest:
        return {"error": f"Quest '{quest_id}' not found"}

    # Check not already active
    result = await session.execute(
        select(UserQuest).where(
            UserQuest.user_id == user_id,
            UserQuest.quest_id == quest_id,
            UserQuest.status == QuestStatus.ACTIVE,
        )
    )
    if result.scalar_one_or_none():
        return {"error": "Quest already active"}

    uq = UserQuest(
        user_id=user_id,
        quest_id=quest_id,
        progress={"current": 0, "target": quest.criteria.get("count", 1)},
    )
    session.add(uq)
    await session.commit()

    return {"status": "started", "quest": quest.name, "xp_reward": quest.xp_reward}


async def check_quest_progress_tool(session: AsyncSession, user_id: UUID, **kwargs) -> dict[str, Any]:
    """Check and update quest progress."""
    completed = await check_quest_progress(session, user_id)
    await session.commit()

    # Get all active quests
    result = await session.execute(
        select(UserQuest).where(
            UserQuest.user_id == user_id,
            UserQuest.status == QuestStatus.ACTIVE,
        )
    )
    active = result.scalars().all()

    return {
        "active_quests": [
            {
                "quest_id": uq.quest_id,
                "name": uq.quest.name,
                "progress": uq.progress,
                "status": uq.status.value,
            }
            for uq in active
        ],
        "newly_completed": [
            {"quest_id": uq.quest_id, "name": uq.quest.name, "xp_reward": uq.quest.xp_reward}
            for uq in completed
        ],
    }


async def get_leaderboard_tool(session: AsyncSession, user_id: UUID, period: str = "weekly", **kwargs) -> dict[str, Any]:
    """Get leaderboard."""
    from datetime import datetime, timedelta, timezone

    CST = timezone(timedelta(hours=8))
    now = datetime.now(CST)

    period_type = PeriodType.WEEKLY if period == "weekly" else PeriodType.MONTHLY
    if period_type == PeriodType.WEEKLY:
        period_start = (now - timedelta(days=now.weekday())).date()
    else:
        period_start = now.date().replace(day=1)

    result = await session.execute(
        select(LeaderboardEntry).where(
            LeaderboardEntry.period_type == period_type,
            LeaderboardEntry.period_start == period_start,
        ).order_by(LeaderboardEntry.xp.desc()).limit(20)
    )
    entries = result.scalars().all()

    # Get characters for names
    user_ids = [e.user_id for e in entries]
    chars_map = {}
    if user_ids:
        result = await session.execute(
            select(TradingCharacter).where(TradingCharacter.user_id.in_(user_ids))
        )
        chars_map = {c.user_id: c for c in result.scalars().all()}

    return {
        "period": period,
        "entries": [
            {
                "position": i,
                "nickname": chars_map.get(e.user_id, None) and chars_map[e.user_id].nickname or "Trader",
                "level": chars_map.get(e.user_id, None) and chars_map[e.user_id].level or 1,
                "rank": chars_map.get(e.user_id, None) and chars_map[e.user_id].rank.value or "bronze",
                "xp": e.xp,
                "win_rate": e.win_rate,
                "is_you": e.user_id == user_id,
            }
            for i, e in enumerate(entries, 1)
        ],
    }


async def generate_trading_card(session: AsyncSession, user_id: UUID, card_type: str = "character", **kwargs) -> dict[str, Any]:
    """Generate trading card data (character or weekly)."""
    character = await get_or_create_character(session, user_id)

    if card_type == "weekly":
        from datetime import datetime, timedelta, timezone
        from domain.journal.models import Journal

        CST = timezone(timedelta(hours=8))
        now = datetime.now(CST)
        week_start = now - timedelta(days=now.weekday())

        result = await session.execute(
            select(Journal).where(
                Journal.user_id == user_id,
                Journal.deleted_at == None,
                Journal.trade_date >= datetime.combine(week_start.date(), datetime.min.time()),
            )
        )
        journals = list(result.scalars().all())
        total = len(journals)
        wins = sum(1 for j in journals if j.result and j.result.value == "win")
        total_pnl = sum(j.pnl_amount or 0 for j in journals)

        return {
            "card_type": "weekly",
            "nickname": character.nickname or "Trader",
            "level": character.level,
            "rank": character.rank.value,
            "stats": {
                "total_trades": total,
                "wins": wins,
                "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
                "total_pnl": round(total_pnl, 2),
            },
        }

    # Character card
    result = await session.execute(
        select(UserAchievement).where(UserAchievement.user_id == user_id)
        .order_by(UserAchievement.unlocked_at.desc()).limit(5)
    )
    recent = [
        {"id": ua.achievement_id, "name": ua.achievement.name, "rarity": ua.achievement.rarity.value}
        for ua in result.scalars().all()
    ]

    return {
        "card_type": "character",
        "nickname": character.nickname or "Trader",
        "level": character.level,
        "xp": character.xp,
        "rank": character.rank.value,
        "attributes": {
            "discipline": character.discipline,
            "patience": character.patience,
            "risk_management": character.risk_management,
            "decisiveness": character.decisiveness,
            "consistency": character.consistency,
        },
        "recent_achievements": recent,
    }


async def sync_trades_tool(session: AsyncSession, user_id: UUID, **kwargs) -> dict[str, Any]:
    """Trigger trade sync and RPG recalculation."""
    character = await recalculate_character(session, user_id)
    newly_unlocked = await check_achievements(session, user_id)
    completed_quests = await check_quest_progress(session, user_id)
    await session.commit()

    return {
        "character": {
            "level": character.level,
            "xp": character.xp,
            "rank": character.rank.value,
        },
        "newly_unlocked_achievements": [
            {"id": a.id, "name": a.name, "xp_reward": a.xp_reward}
            for a in newly_unlocked
        ],
        "completed_quests": [
            {"quest_id": uq.quest_id, "name": uq.quest.name, "xp_reward": uq.quest.xp_reward}
            for uq in completed_quests
        ],
    }
