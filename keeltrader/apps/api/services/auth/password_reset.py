"""Password reset flow helpers."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.auth import hash_password
from core.cache import get_redis_client
from domain.user.models import User
from services.auth.sessions import AuthSessionService

RESET_TTL_SECONDS = 3600


@dataclass(frozen=True)
class PasswordResetRequestResult:
    enabled: bool
    user_exists: bool
    token: Optional[str] = None


class PasswordResetService:
    """Generate and consume password reset tokens when explicitly enabled."""

    def __init__(self, session_service: AuthSessionService | None = None):
        self.settings = get_settings()
        self.session_service = session_service or AuthSessionService()

    def _redis_key(self, token: str) -> str:
        return f"password_reset:{token}"

    async def request_reset(self, session: AsyncSession, email: str) -> PasswordResetRequestResult:
        if not self.settings.password_reset_enabled:
            return PasswordResetRequestResult(enabled=False, user_exists=False)

        result = await session.execute(select(User).where(User.email == email, User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            return PasswordResetRequestResult(enabled=True, user_exists=False)

        token = secrets.token_urlsafe(32)
        get_redis_client().setex(self._redis_key(token), RESET_TTL_SECONDS, str(user.id))
        return PasswordResetRequestResult(enabled=True, user_exists=True, token=token)

    async def reset_password(self, session: AsyncSession, token: str, new_password: str) -> bool:
        if not self.settings.password_reset_enabled:
            return False

        redis_client = get_redis_client()
        token_key = self._redis_key(token)
        user_id = redis_client.get(token_key)
        if not user_id:
            return False

        result = await session.execute(select(User).where(User.id == str(user_id), User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            redis_client.delete(token_key)
            return False

        user.hashed_password = hash_password(new_password)
        await session.commit()
        redis_client.delete(token_key)
        await self.session_service.revoke_all_user_sessions(session, user.id)
        return True
