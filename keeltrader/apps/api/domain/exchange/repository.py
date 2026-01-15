"""Exchange connection repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ExchangeConnection, ExchangeType


class ExchangeConnectionRepository:
    """Repository for exchange connection operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, connection: ExchangeConnection) -> ExchangeConnection:
        """Create a new exchange connection."""
        self.session.add(connection)
        await self.session.commit()
        await self.session.refresh(connection)
        return connection

    async def get_by_id(self, connection_id: UUID) -> Optional[ExchangeConnection]:
        """Get exchange connection by ID."""
        result = await self.session.execute(
            select(ExchangeConnection).where(ExchangeConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def get_user_connections(
        self, user_id: UUID, active_only: bool = True
    ) -> List[ExchangeConnection]:
        """Get all exchange connections for a user."""
        query = select(ExchangeConnection).where(ExchangeConnection.user_id == user_id)

        if active_only:
            query = query.where(ExchangeConnection.is_active == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_connection_by_type(
        self, user_id: UUID, exchange_type: ExchangeType
    ) -> Optional[ExchangeConnection]:
        """Get a specific exchange connection for a user."""
        result = await self.session.execute(
            select(ExchangeConnection).where(
                ExchangeConnection.user_id == user_id,
                ExchangeConnection.exchange_type == exchange_type,
                ExchangeConnection.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, connection: ExchangeConnection) -> ExchangeConnection:
        """Update an exchange connection."""
        await self.session.commit()
        await self.session.refresh(connection)
        return connection

    async def delete(self, connection_id: UUID) -> bool:
        """Delete an exchange connection."""
        connection = await self.get_by_id(connection_id)
        if not connection:
            return False

        await self.session.delete(connection)
        await self.session.commit()
        return True

    async def deactivate(self, connection_id: UUID) -> Optional[ExchangeConnection]:
        """Deactivate an exchange connection (soft delete)."""
        connection = await self.get_by_id(connection_id)
        if not connection:
            return None

        connection.is_active = False
        await self.session.commit()
        await self.session.refresh(connection)
        return connection
