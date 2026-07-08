#!/usr/bin/env python
"""
Simple user initialization script - creates test users directly without importing all models.

Usage:
    python scripts/init_user_simple.py

This will create test users with:
    - test@example.com / KEELTRADER_DEV_USER_PASSWORD
    - admin@keeltrader.com / KEELTRADER_DEV_ADMIN_PASSWORD
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import get_settings


def hash_password_simple(password: str) -> str:
    """Simple password hashing using bcrypt directly."""
    # Encode password to bytes and hash it
    password_bytes = password.encode("utf-8")
    # Truncate to 72 bytes if needed (bcrypt limitation)
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


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
            "is_admin": True,
        },
    ]


async def create_test_users(test_users):
    """Create test users using raw SQL."""
    settings = get_settings()

    # Create database engine
    engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

    created_users = []
    skipped_users = []

    async with engine.begin() as conn:
        for user_data in test_users:
            try:
                # Check if user already exists
                result = await conn.execute(
                    text("SELECT id FROM users WHERE email = :email"),
                    {"email": user_data["email"]},
                )
                existing_user = result.fetchone()

                if existing_user:
                    logger.info(
                        f"User {user_data['email']} already exists, skipping..."
                    )
                    skipped_users.append(user_data["email"])
                    continue

                # Create new user
                user_id = str(uuid.uuid4())
                hashed_pwd = hash_password_simple(user_data["password"])
                now = datetime.utcnow()

                await conn.execute(
                    text(
                        """
                        INSERT INTO users (
                            id, email, hashed_password, full_name,
                            subscription_tier, is_active, is_admin,
                            created_at, updated_at
                        ) VALUES (
                            :id, :email, :hashed_password, :full_name,
                            :subscription_tier, :is_active, :is_admin,
                            :created_at, :updated_at
                        )
                    """
                    ),
                    {
                        "id": user_id,
                        "email": user_data["email"],
                        "hashed_password": hashed_pwd,
                        "full_name": user_data["full_name"],
                        "subscription_tier": user_data.get("subscription_tier", "free"),
                        "is_active": True,
                        "is_admin": user_data.get("is_admin", False),
                        "created_at": now,
                        "updated_at": now,
                    },
                )

                logger.info(f"Created user: {user_data['email']}")
                created_users.append(user_data["email"])

            except Exception as e:
                logger.error(f"Error creating user {user_data['email']}: {e}")

    # Close engine
    await engine.dispose()

    return created_users, skipped_users


async def main():
    """Main function."""
    print("=" * 50)
    print("KeelTrader - Initialize Test Users (Simple Version)")
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
