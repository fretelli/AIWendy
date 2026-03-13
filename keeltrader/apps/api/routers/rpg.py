"""RPG gamification routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
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
from domain.user.models import User

router = APIRouter()


@router.get("/character")
async def get_character(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get or auto-create trading character."""
    character = await get_or_create_character(session, user.id)
    await session.commit()

    # Get achievement count
    result = await session.execute(
        select(func.count()).select_from(UserAchievement).where(
            UserAchievement.user_id == user.id
        )
    )
    achievement_count = result.scalar() or 0

    return {
        "nickname": character.nickname or user.display_name or user.email.split("@")[0],
        "avatar_settings": character.avatar_settings,
        "level": character.level,
        "xp": character.xp,
        "xp_to_next_level": (character.level) * 100,  # XP needed for next level
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


@router.post("/character/recalculate")
async def recalculate(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Recalculate character attributes from journal data."""
    character = await recalculate_character(session, user.id)
    newly_unlocked = await check_achievements(session, user.id)
    await session.commit()

    return {
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
        "newly_unlocked": [
            {"id": a.id, "name": a.name, "rarity": a.rarity.value, "xp_reward": a.xp_reward}
            for a in newly_unlocked
        ],
    }


@router.get("/achievements")
async def get_achievements(
    category: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get all achievements with unlock status."""
    # Get all achievements
    query = select(Achievement)
    if category:
        query = query.where(Achievement.category == category)
    result = await session.execute(query)
    all_achievements = result.scalars().all()

    # Get user's unlocked
    result = await session.execute(
        select(UserAchievement).where(UserAchievement.user_id == user.id)
    )
    unlocked_map = {ua.achievement_id: ua for ua in result.scalars().all()}

    achievements = []
    for a in all_achievements:
        ua = unlocked_map.get(a.id)
        achievements.append({
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "category": a.category.value,
            "rarity": a.rarity.value,
            "icon": a.icon,
            "xp_reward": a.xp_reward,
            "unlocked": ua is not None,
            "unlocked_at": ua.unlocked_at.isoformat() if ua else None,
        })

    return {"achievements": achievements}


@router.get("/quests")
async def get_quests(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get available + active + completed quests."""
    # Get user's quests
    result = await session.execute(
        select(UserQuest).where(UserQuest.user_id == user.id).order_by(UserQuest.started_at.desc())
    )
    user_quests = result.scalars().all()

    active = []
    completed = []
    for uq in user_quests:
        item = {
            "id": uq.id,
            "quest_id": uq.quest_id,
            "name": uq.quest.name,
            "description": uq.quest.description,
            "quest_type": uq.quest.quest_type.value,
            "xp_reward": uq.quest.xp_reward,
            "progress": uq.progress,
            "status": uq.status.value,
            "started_at": uq.started_at.isoformat() if uq.started_at else None,
            "completed_at": uq.completed_at.isoformat() if uq.completed_at else None,
        }
        if uq.status == QuestStatus.ACTIVE:
            active.append(item)
        elif uq.status == QuestStatus.COMPLETED:
            completed.append(item)

    # Get available quests (not yet started)
    active_quest_ids = {uq.quest_id for uq in user_quests if uq.status == QuestStatus.ACTIVE}
    result = await session.execute(select(Quest))
    all_quests = result.scalars().all()

    available = []
    for q in all_quests:
        if q.id not in active_quest_ids:
            available.append({
                "quest_id": q.id,
                "name": q.name,
                "description": q.description,
                "quest_type": q.quest_type.value,
                "xp_reward": q.xp_reward,
            })

    return {"active": active, "available": available, "completed": completed[:20]}


@router.post("/quests/{quest_id}/start")
async def start_quest(
    quest_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Start a quest."""
    # Check quest exists
    result = await session.execute(select(Quest).where(Quest.id == quest_id))
    quest = result.scalar_one_or_none()
    if not quest:
        return {"error": "Quest not found"}

    # Check not already active
    result = await session.execute(
        select(UserQuest).where(
            UserQuest.user_id == user.id,
            UserQuest.quest_id == quest_id,
            UserQuest.status == QuestStatus.ACTIVE,
        )
    )
    if result.scalar_one_or_none():
        return {"error": "Quest already active"}

    uq = UserQuest(
        user_id=user.id,
        quest_id=quest_id,
        progress={"current": 0, "target": quest.criteria.get("count", 1)},
    )
    session.add(uq)
    await session.commit()

    return {
        "id": uq.id,
        "quest_id": quest_id,
        "name": quest.name,
        "status": "active",
        "progress": uq.progress,
    }


@router.get("/quests/{quest_id}/progress")
async def get_quest_progress(
    quest_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Check quest progress."""
    completed = await check_quest_progress(session, user.id)
    await session.commit()

    # Get the specific quest
    result = await session.execute(
        select(UserQuest).where(
            UserQuest.user_id == user.id,
            UserQuest.quest_id == quest_id,
            UserQuest.status.in_([QuestStatus.ACTIVE, QuestStatus.COMPLETED]),
        ).order_by(UserQuest.started_at.desc()).limit(1)
    )
    uq = result.scalar_one_or_none()
    if not uq:
        return {"error": "Quest not found or not started"}

    return {
        "quest_id": quest_id,
        "name": uq.quest.name,
        "status": uq.status.value,
        "progress": uq.progress,
        "completed_at": uq.completed_at.isoformat() if uq.completed_at else None,
    }


@router.get("/leaderboard")
async def get_leaderboard(
    period: str = Query("weekly"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get leaderboard for current period."""
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
        ).order_by(LeaderboardEntry.xp.desc()).limit(50)
    )
    entries = result.scalars().all()

    # Get user display names
    user_ids = [e.user_id for e in entries]
    if user_ids:
        result = await session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users_map = {u.id: u for u in result.scalars().all()}
    else:
        users_map = {}

    # Get characters for rank info
    if user_ids:
        result = await session.execute(
            select(TradingCharacter).where(TradingCharacter.user_id.in_(user_ids))
        )
        chars_map = {c.user_id: c for c in result.scalars().all()}
    else:
        chars_map = {}

    leaderboard = []
    for i, entry in enumerate(entries, 1):
        u = users_map.get(entry.user_id)
        c = chars_map.get(entry.user_id)
        leaderboard.append({
            "position": i,
            "nickname": (c.nickname if c and c.nickname else
                        u.display_name if u and u.display_name else
                        u.email.split("@")[0] if u else "Unknown"),
            "level": c.level if c else 1,
            "rank": c.rank.value if c else "bronze",
            "xp": entry.xp,
            "win_rate": entry.win_rate,
            "profit_factor": entry.profit_factor,
            "achievement_count": entry.achievement_count,
            "is_current_user": entry.user_id == user.id,
        })

    return {
        "period": period,
        "period_start": period_start.isoformat(),
        "entries": leaderboard,
    }


@router.get("/card/character")
async def get_character_card(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get character card data for sharing."""
    character = await get_or_create_character(session, user.id)

    # Recent achievements
    result = await session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user.id
        ).order_by(UserAchievement.unlocked_at.desc()).limit(5)
    )
    recent_achievements = [
        {"id": ua.achievement_id, "name": ua.achievement.name, "icon": ua.achievement.icon,
         "rarity": ua.achievement.rarity.value}
        for ua in result.scalars().all()
    ]

    return {
        "nickname": character.nickname or user.display_name or user.email.split("@")[0],
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
        "recent_achievements": recent_achievements,
    }


@router.get("/card/weekly")
async def get_weekly_card(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get weekly report card data for sharing."""
    from datetime import timedelta, timezone
    from domain.journal.models import Journal

    CST = timezone(timedelta(hours=8))
    now = datetime.now(CST)
    week_start = now - timedelta(days=now.weekday())

    character = await get_or_create_character(session, user.id)

    # Get this week's journals
    from datetime import datetime as dt
    result = await session.execute(
        select(Journal).where(
            Journal.user_id == user.id,
            Journal.deleted_at == None,
            Journal.trade_date >= dt.combine(week_start.date(), dt.min.time()),
        )
    )
    journals = list(result.scalars().all())

    total = len(journals)
    wins = sum(1 for j in journals if j.result and j.result.value == "win")
    losses = sum(1 for j in journals if j.result and j.result.value == "loss")
    total_pnl = sum(j.pnl_amount or 0 for j in journals)
    win_rate = (wins / total * 100) if total > 0 else 0

    return {
        "nickname": character.nickname or user.display_name or user.email.split("@")[0],
        "level": character.level,
        "rank": character.rank.value,
        "week_start": week_start.date().isoformat(),
        "stats": {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
        },
        "attributes": {
            "discipline": character.discipline,
            "patience": character.patience,
            "risk_management": character.risk_management,
            "decisiveness": character.decisiveness,
            "consistency": character.consistency,
        },
    }


# Need datetime import at module level for weekly card
from datetime import datetime
