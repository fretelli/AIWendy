"""
User exchange connection management service
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.encryption import get_encryption_service
from domain.exchange.models import ExchangeConnection, ExchangeType
from domain.exchange.repository import ExchangeConnectionRepository

logger = logging.getLogger(__name__)


class UserExchangeService:
    """Service for managing user exchange connections"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ExchangeConnectionRepository(session)
        self.encryption = get_encryption_service()

    async def create_connection(
        self,
        user_id: UUID,
        exchange_type: ExchangeType,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        name: Optional[str] = None,
        is_testnet: bool = False,
        sync_symbols: Optional[List[str]] = None,
    ) -> ExchangeConnection:
        """
        Create a new exchange connection for a user

        Args:
            user_id: User ID
            exchange_type: Type of exchange
            api_key: API key (will be encrypted)
            api_secret: API secret (will be encrypted)
            passphrase: Optional passphrase for exchanges like OKX
            name: Optional user-defined name
            is_testnet: Whether this is a testnet connection

        Returns:
            Created exchange connection
        """
        # Encrypt credentials
        api_key_encrypted = self.encryption.encrypt(api_key)
        api_secret_encrypted = self.encryption.encrypt(api_secret)
        passphrase_encrypted = (
            self.encryption.encrypt(passphrase) if passphrase else None
        )

        # Create connection
        connection = ExchangeConnection(
            user_id=user_id,
            exchange_type=exchange_type,
            name=name or f"My {exchange_type.value.title()} Account",
            api_key_encrypted=api_key_encrypted,
            api_secret_encrypted=api_secret_encrypted,
            passphrase_encrypted=passphrase_encrypted,
            is_testnet=is_testnet,
            sync_symbols=sync_symbols or [],
        )

        connection = await self.repository.create(connection)
        logger.info(
            f"Created exchange connection for user {user_id}: {exchange_type.value}"
        )

        return connection

    async def get_user_connections(
        self, user_id: UUID, active_only: bool = True
    ) -> List[ExchangeConnection]:
        """
        Get all exchange connections for a user

        Args:
            user_id: User ID
            active_only: Only return active connections

        Returns:
            List of exchange connections
        """
        return await self.repository.get_user_connections(user_id, active_only)

    async def get_connection(
        self, connection_id: UUID, user_id: UUID
    ) -> Optional[ExchangeConnection]:
        """
        Get a specific exchange connection

        Args:
            connection_id: Connection ID
            user_id: User ID (for security check)

        Returns:
            Exchange connection if found and owned by user
        """
        connection = await self.repository.get_by_id(connection_id)

        # Security check: ensure connection belongs to user
        if connection and connection.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to access connection {connection_id} owned by {connection.user_id}"
            )
            return None

        return connection

    async def update_connection(
        self,
        connection_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        is_active: Optional[bool] = None,
        sync_symbols: Optional[List[str]] = None,
    ) -> Optional[ExchangeConnection]:
        """
        Update an exchange connection

        Args:
            connection_id: Connection ID
            user_id: User ID (for security check)
            name: Optional new name
            api_key: Optional new API key
            api_secret: Optional new API secret
            passphrase: Optional new passphrase
            is_active: Optional new active status

        Returns:
            Updated connection if successful
        """
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            return None

        # Update fields
        if name is not None:
            connection.name = name

        if api_key is not None:
            connection.api_key_encrypted = self.encryption.encrypt(api_key)

        if api_secret is not None:
            connection.api_secret_encrypted = self.encryption.encrypt(api_secret)

        if passphrase is not None:
            connection.passphrase_encrypted = self.encryption.encrypt(passphrase)

        if is_active is not None:
            connection.is_active = is_active

        if sync_symbols is not None:
            connection.sync_symbols = sync_symbols

        connection = await self.repository.update(connection)
        logger.info(f"Updated exchange connection {connection_id} for user {user_id}")

        return connection

    async def delete_connection(
        self, connection_id: UUID, user_id: UUID
    ) -> bool:
        """
        Delete an exchange connection

        Args:
            connection_id: Connection ID
            user_id: User ID (for security check)

        Returns:
            True if deleted successfully
        """
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            return False

        success = await self.repository.delete(connection_id)
        if success:
            logger.info(f"Deleted exchange connection {connection_id} for user {user_id}")

        return success

    async def test_connection(
        self, connection_id: UUID, user_id: UUID
    ) -> dict:
        """
        Test an exchange connection by attempting to fetch account balance

        Args:
            connection_id: Connection ID
            user_id: User ID (for security check)

        Returns:
            Test result with status and message
        """
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            return {"success": False, "message": "Connection not found"}

        try:
            # Decrypt credentials
            api_key = self.encryption.decrypt(connection.api_key_encrypted)
            api_secret = self.encryption.decrypt(connection.api_secret_encrypted)
            passphrase = (
                self.encryption.decrypt(connection.passphrase_encrypted)
                if connection.passphrase_encrypted
                else None
            )

            # Try to create exchange instance and fetch balance
            import ccxt

            exchange_class = getattr(ccxt, connection.exchange_type.value)
            exchange_config = {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
            }

            if passphrase:
                exchange_config["password"] = passphrase

            if connection.is_testnet:
                exchange_config["options"] = {"defaultType": "future"}
                # Enable testnet mode if supported
                if hasattr(exchange_class, "set_sandbox_mode"):
                    exchange_config["sandbox"] = True

            exchange = exchange_class(exchange_config)

            # Test API call
            balance = exchange.fetch_balance()

            # Update last_sync_at
            connection.last_sync_at = datetime.utcnow()
            connection.last_error = None
            await self.repository.update(connection)

            return {
                "success": True,
                "message": "Connection successful",
                "data": {
                    "exchange": connection.exchange_type.value,
                    "currencies_count": len([c for c, v in balance["total"].items() if v > 0]),
                },
            }

        except Exception as e:
            error_message = str(e)
            logger.error(f"Connection test failed for {connection_id}: {error_message}")

            # Update last_error
            connection.last_error = error_message[:500]  # Truncate long errors
            await self.repository.update(connection)

            return {
                "success": False,
                "message": f"Connection failed: {error_message}",
            }

    async def get_decrypted_credentials(
        self, connection_id: UUID, user_id: UUID
    ) -> Optional[dict]:
        """
        Get decrypted credentials for an exchange connection

        WARNING: Only use this internally. Never expose decrypted credentials to the client!

        Args:
            connection_id: Connection ID
            user_id: User ID (for security check)

        Returns:
            Dict with decrypted credentials
        """
        connection = await self.get_connection(connection_id, user_id)
        if not connection:
            return None

        return {
            "exchange_type": connection.exchange_type.value,
            "api_key": self.encryption.decrypt(connection.api_key_encrypted),
            "api_secret": self.encryption.decrypt(connection.api_secret_encrypted),
            "passphrase": (
                self.encryption.decrypt(connection.passphrase_encrypted)
                if connection.passphrase_encrypted
                else None
            ),
            "is_testnet": connection.is_testnet,
        }

    def mask_connection(self, connection: ExchangeConnection) -> dict:
        """
        Convert connection to safe dict for API response (with masked keys)

        Args:
            connection: Exchange connection

        Returns:
            Dict with masked sensitive data
        """
        # Decrypt just to mask
        api_key = self.encryption.decrypt(connection.api_key_encrypted)

        return {
            "id": str(connection.id),
            "exchange_type": connection.exchange_type.value,
            "name": connection.name,
            "api_key_masked": self.encryption.mask_api_key(api_key),
            "is_active": connection.is_active,
            "is_testnet": connection.is_testnet,
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "last_trade_sync_at": connection.last_trade_sync_at.isoformat()
            if connection.last_trade_sync_at
            else None,
            "last_error": connection.last_error,
            "sync_symbols": connection.sync_symbols or [],
            "created_at": connection.created_at.isoformat(),
            "updated_at": connection.updated_at.isoformat(),
        }
