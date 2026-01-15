"""Session management schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SessionInfo(BaseModel):
    """User session information."""

    id: UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    is_current: bool = False

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response for session list."""

    sessions: list[SessionInfo]
    total: int
