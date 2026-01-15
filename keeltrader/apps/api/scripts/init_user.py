#!/usr/bin/env python
"""
Initialize test user for development environment.

Usage:
    python scripts/init_user.py

This will create a test user with:
    Email: test@example.com
    Password: Test@1234
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

# Test user credentials
TEST_USERS = [
    {
        "email": "test@example.com",
        "password": "Test@1234",
        "full_name": "Test User",
        "subscription_tier": "free",
    },
    {
        "email": "admin@keeltrader.com",
        "password": "Admin@123",
        "full_name": "Admin User",
        "subscription_tier": "elite",
        "is_admin": True,  # Note: You may need to add this field to the User model
    },
]


async def create_test_users():
    """Create test users if they don't exist."""
    settings = get_settings()

    # Create database engine
    engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created_users = []
    skipped_users = []

    async with async_session() as session:
        for user_data in TEST_USERS:
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
    print("=" * 50)
    print("KeelTrader - Initialize Test Users")
    print("=" * 50)

    try:
        created, skipped = await create_test_users()

        print("\n✅ Script completed successfully!")

        if created:
            print(f"\n📝 Created {len(created)} user(s):")
            for email in created:
                user = next(u for u in TEST_USERS if u["email"] == email)
                print(f"   - Email: {email}")
                print(f"     Password: {user['password']}")
                print(f"     Name: {user['full_name']}")
                print(f"     Tier: {user.get('subscription_tier', 'free')}")

        if skipped:
            print(f"\n⏩ Skipped {len(skipped)} existing user(s):")
            for email in skipped:
                print(f"   - {email}")

        print("\n🚀 You can now login with the test credentials:")
        print("   URL: http://localhost:3000/auth/login")
        for user in TEST_USERS:
            print(f"\n   User {TEST_USERS.index(user) + 1}:")
            print(f"   Email: {user['email']}")
            print(f"   Password: {user['password']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
