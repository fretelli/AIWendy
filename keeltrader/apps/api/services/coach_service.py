"""Coach service for managing AI coaches."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from core.database import get_db
from domain.coach.models import ChatMessage, ChatSession, Coach, CoachStyle


class CoachService:
    """Service for managing coaches and chat sessions."""

    def __init__(self, db: Session):
        self.db = db

    # Coach Management
    def get_all_coaches(
        self, is_public: bool = True, is_active: bool = True
    ) -> List[Coach]:
        """Get all available coaches."""
        query = self.db.query(Coach)

        if is_public is not None:
            query = query.filter(Coach.is_public == is_public)

        if is_active is not None:
            query = query.filter(Coach.is_active == is_active)

        return query.all()

    def get_coach_by_id(self, coach_id: str) -> Optional[Coach]:
        """Get coach by ID."""
        return self.db.query(Coach).filter(Coach.id == coach_id).first()

    def get_coaches_by_style(self, style: CoachStyle) -> List[Coach]:
        """Get coaches by interaction style."""
        return (
            self.db.query(Coach)
            .filter(
                and_(
                    Coach.style == style,
                    Coach.is_active == True,
                    Coach.is_public == True,
                )
            )
            .all()
        )

    def get_premium_coaches(self) -> List[Coach]:
        """Get premium coaches."""
        return (
            self.db.query(Coach)
            .filter(
                and_(
                    Coach.is_premium == True,
                    Coach.is_active == True,
                    Coach.is_public == True,
                )
            )
            .all()
        )

    def get_default_coach(self) -> Optional[Coach]:
        """Get the default coach."""
        return self.db.query(Coach).filter(Coach.is_default == True).first()

    def create_coach(self, coach_data: Dict[str, Any]) -> Coach:
        """Create a new coach."""
        coach = Coach(**coach_data)
        self.db.add(coach)
        self.db.commit()
        self.db.refresh(coach)
        return coach

    def update_coach(
        self, coach_id: str, update_data: Dict[str, Any]
    ) -> Optional[Coach]:
        """Update coach information."""
        coach = self.get_coach_by_id(coach_id)
        if not coach:
            return None

        for key, value in update_data.items():
            if hasattr(coach, key):
                setattr(coach, key, value)

        coach.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(coach)
        return coach

    def update_coach_stats(
        self,
        coach_id: str,
        new_session: bool = False,
        new_messages: int = 0,
        rating: Optional[int] = None,
    ) -> None:
        """Update coach statistics."""
        coach = self.get_coach_by_id(coach_id)
        if not coach:
            return

        if new_session:
            coach.total_sessions += 1

        if new_messages > 0:
            coach.total_messages += new_messages

        if rating is not None and 1 <= rating <= 5:
            if coach.avg_rating is None:
                coach.avg_rating = float(rating)
                coach.rating_count = 1
            else:
                total_rating = coach.avg_rating * coach.rating_count + rating
                coach.rating_count += 1
                coach.avg_rating = total_rating / coach.rating_count

        self.db.commit()

    # Chat Session Management
    def create_chat_session(
        self,
        user_id: UUID,
        coach_id: str,
        title: Optional[str] = None,
        context: Optional[Dict] = None,
        project_id: Optional[UUID] = None,
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            user_id=user_id,
            coach_id=coach_id,
            title=title,
            context=context,
            project_id=project_id,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # Update coach stats
        self.update_coach_stats(coach_id, new_session=True)

        return session

    def get_user_sessions(
        self,
        user_id: UUID,
        coach_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        project_id: Optional[UUID] = None,
    ) -> List[ChatSession]:
        """Get user's chat sessions."""
        query = self.db.query(ChatSession).filter(ChatSession.user_id == user_id)

        if coach_id:
            query = query.filter(ChatSession.coach_id == coach_id)

        if project_id:
            query = query.filter(ChatSession.project_id == project_id)

        if is_active is not None:
            query = query.filter(ChatSession.is_active == is_active)

        return query.order_by(ChatSession.created_at.desc()).all()

    def get_session_by_id(self, session_id: UUID) -> Optional[ChatSession]:
        """Get chat session by ID."""
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

    def end_chat_session(
        self,
        session_id: UUID,
        mood_after: Optional[int] = None,
        user_rating: Optional[int] = None,
        user_feedback: Optional[str] = None,
    ) -> Optional[ChatSession]:
        """End a chat session."""
        session = self.get_session_by_id(session_id)
        if not session:
            return None

        session.is_active = False
        session.ended_at = datetime.utcnow()

        if mood_after:
            session.mood_after = mood_after

        if user_rating:
            session.user_rating = user_rating
            # Update coach rating
            self.update_coach_stats(session.coach_id, rating=user_rating)

        if user_feedback:
            session.user_feedback = user_feedback

        self.db.commit()
        self.db.refresh(session)
        return session

    # Message Management
    def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        token_count: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> ChatMessage:
        """Add a message to a chat session."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            token_count=token_count,
            message_metadata=metadata,
        )
        self.db.add(message)

        # Update session stats
        session = self.get_session_by_id(session_id)
        if session:
            session.message_count += 1
            if token_count:
                session.total_tokens += token_count
            session.updated_at = datetime.utcnow()

            # Update coach stats
            if role == "assistant":
                self.update_coach_stats(session.coach_id, new_messages=1)

        self.db.commit()
        self.db.refresh(message)
        return message

    def get_session_messages(
        self, session_id: UUID, limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get messages from a chat session."""
        query = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_recent_messages(
        self, session_id: UUID, count: int = 10
    ) -> List[ChatMessage]:
        """Get recent messages from a session."""
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(count)
            .all()[::-1]
        )


def get_coach_service(db: Session = None) -> CoachService:
    """Factory function to create CoachService instance."""
    if db is None:
        db = next(get_db())
    return CoachService(db)
