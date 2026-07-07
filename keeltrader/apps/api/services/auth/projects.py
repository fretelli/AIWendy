"""Auth-related project helpers."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import t
from domain.user.models import User


async def ensure_default_project(session: AsyncSession, user: User, locale: str) -> None:
    """Best-effort creation of a user's default project."""
    try:
        from domain.project.models import Project

        default_project = Project(
            user_id=user.id,
            name=t("projects.default.name", locale),
            description=t("projects.default.description", locale),
            is_default=True,
        )
        session.add(default_project)
        await session.commit()
    except Exception:
        await session.rollback()
