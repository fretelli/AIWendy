#!/usr/bin/env python
"""
Initialize test user for development environment.

Usage:
    python scripts/init_user.py

This will create a test user with:
    Email: test@example.com
    Password: set by KEELTRADER_DEV_USER_PASSWORD
"""

import asyncio
import os
import sys

from _path_setup import ensure_api_import_path
from _script_guard import require_non_production_script

ensure_api_import_path()

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import get_settings

# Import all models to ensure relationships are established
from domain.user.models import SubscriptionTier, User

try:
    from domain.journal.models import Journal
except ImportError:
    pass
try:
    from domain.coach.models import ChatSession
except ImportError:
    pass
try:
    from domain.analysis.models import AnalysisReport
except ImportError:
    pass

from core.auth import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _required_password(env_name: str) -> str:
    password = os.environ.get(env_name)
    if not password:
        raise RuntimeError(f"Missing {env_name}; set an explicit development password.")
    return password


def get_test_users():
    """Return development users with passwords supplied by environment."""
    return [
        {
            "email": os.environ.get("KEELTRADER_DEV_USER_EMAIL", "test@example.com"),
            "password": _required_password("KEELTRADER_DEV_USER_PASSWORD"),
            "password_env": "KEELTRADER_DEV_USER_PASSWORD",
            "full_name": "Test User",
            "subscription_tier": "free",
        },
        {
            "email": os.environ.get("KEELTRADER_DEV_ADMIN_EMAIL", "admin@keeltrader.com"),
            "password": _required_password("KEELTRADER_DEV_ADMIN_PASSWORD"),
            "password_env": "KEELTRADER_DEV_ADMIN_PASSWORD",
            "full_name": "Admin User",
            "subscription_tier": "elite",
            "is_admin": True,  # Note: You may need to add this field to the User model
        },
    ]


async def create_test_users(test_users):
    """Create test users if they don't exist."""
    settings = get_settings()

    # Create database engine
    engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created_users = []
    skipped_users = []

    async with async_session() as session:
        for user_data in test_users:
            try:
                # Check if user already exists
                result = await session.execute(
                    select(User).where(User.email == user_data["email"])
                )
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    logger.info(
                        f"User {user_data['email']} already exists, skipping..."
                    )
                    skipped_users.append(user_data["email"])
                    continue

                # Create new user
                tier_str = user_data.get("subscription_tier", "free")
                tier_enum = SubscriptionTier(tier_str)

                user = User(
                    email=user_data["email"],
                    hashed_password=hash_password(user_data["password"]),
                    full_name=user_data["full_name"],
                    subscription_tier=tier_enum,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )

                # Set admin flag if specified (if the field exists)
                if user_data.get("is_admin"):
                    if hasattr(user, "is_admin"):
                        user.is_admin = True

                session.add(user)
                await session.commit()

                logger.info(f"Created user: {user_data['email']}")
                created_users.append(user_data["email"])

            except Exception as e:
                logger.error(f"Error creating user {user_data['email']}: {e}")
                await session.rollback()

    # Close engine
    await engine.dispose()

    return created_users, skipped_users


async def main():
    """Main function."""
    require_non_production_script("init_user.py")

    print("=" * 50)
    print("KeelTrader - Initialize Test Users")
    print("=" * 50)

    try:
        test_users = get_test_users()
        created, skipped = await create_test_users(test_users)

        print("\n✅ Script completed successfully!")

        if created:
            print(f"\n📝 Created {len(created)} user(s):")
            for email in created:
                user = next(u for u in test_users if u["email"] == email)
                print(f"   - Email: {email}")
                print(f"     Password env: {user['password_env']}")
                print(f"     Name: {user['full_name']}")
                print(f"     Tier: {user.get('subscription_tier', 'free')}")

        if skipped:
            print(f"\n⏩ Skipped {len(skipped)} existing user(s):")
            for email in skipped:
                print(f"   - {email}")

        print("\n🚀 You can now login with the configured development credentials:")
        print("   URL: http://localhost:3000/auth/login")
        for user in test_users:
            print(f"\n   User {test_users.index(user) + 1}:")
            print(f"   Email: {user['email']}")
            print(f"   Password env: {user['password_env']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
