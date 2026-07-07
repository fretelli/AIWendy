"""User session and token orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.auth import create_access_token, create_refresh_token, decode_token
from core.cache import get_redis_client
from core.exceptions import InvalidCredentialsError
from domain.user.models import User, UserSession
from domain.user.schemas import SessionInfo, SessionListResponse


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int
    session_id: str


class AuthSessionService:
    """Create, validate, list, and revoke user sessions."""

    def __init__(self):
        self.settings = get_settings()

    @property
    def ttl_seconds(self) -> int:
        return self.settings.jwt_expire_minutes * 60

    def _redis_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _redis(self):
        return get_redis_client()

    async def issue_tokens(self, session: AsyncSession, user: User) -> IssuedTokens:
        user_session = UserSession(
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(minutes=self.settings.jwt_expire_minutes),
        )
        session.add(user_session)
        await session.flush()

        token_data = {"sub": str(user.id), "session_id": str(user_session.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        user_session.access_token = access_token
        user_session.refresh_token = refresh_token
        await session.commit()

        self._redis().setex(self._redis_key(str(user_session.id)), self.ttl_seconds, str(user.id))

        return IssuedTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.ttl_seconds,
            session_id=str(user_session.id),
        )

    def validate_cached_session(self, session_id: Optional[str], user_id: str) -> None:
        if not session_id:
            return
        stored_user_id = self._redis().get(self._redis_key(str(session_id)))
        if not stored_user_id or str(stored_user_id) != str(user_id):
            raise InvalidCredentialsError()

    def revoke_cached_session(self, session_id: Optional[str]) -> None:
        if session_id:
            self._redis().delete(self._redis_key(str(session_id)))

    async def revoke_db_session(self, session: AsyncSession, session_id: str, user_id=None) -> bool:
        stmt = select(UserSession).where(UserSession.id == session_id)
        if user_id is not None:
            stmt = stmt.where(UserSession.user_id == user_id)
        result = await session.execute(stmt)
        user_session = result.scalar_one_or_none()
        if not user_session:
            return False
        user_session.revoked_at = datetime.utcnow()
        await session.commit()
        self.revoke_cached_session(session_id)
        return True

    async def revoke_all_user_sessions(self, session: AsyncSession, user_id) -> int:
        result = await session.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
        )
        sessions = result.scalars().all()
        for user_session in sessions:
            user_session.revoked_at = datetime.utcnow()
            self.revoke_cached_session(str(user_session.id))
        await session.commit()
        return len(sessions)

    async def list_active_sessions(
        self, session: AsyncSession, user_id, current_session_id: Optional[str]
    ) -> SessionListResponse:
        result = await session.execute(
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > datetime.utcnow(),
            )
            .order_by(UserSession.created_at.desc())
        )
        sessions = result.scalars().all()
        session_infos = [
            SessionInfo(
                id=item.id,
                ip_address=item.ip_address,
                user_agent=item.user_agent,
                created_at=item.created_at,
                last_activity_at=item.last_activity_at,
                expires_at=item.expires_at,
                is_current=(str(item.id) == current_session_id),
            )
            for item in sessions
        ]
        return SessionListResponse(sessions=session_infos, total=len(session_infos))

    def session_id_from_authorization(self, authorization: Optional[str]) -> Optional[str]:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        payload = decode_token(authorization.split(" ", 1)[1])
        return payload.get("session_id")
