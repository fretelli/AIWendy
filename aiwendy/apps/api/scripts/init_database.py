#!/usr/bin/env python
"""
Initialize database tables.

Usage:
    python scripts/init_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from sqlalchemy.ext.asyncio import create_async_engine

from config import get_settings
from core.database import Base
from domain.analysis.models import AnalysisReport
from domain.journal.models import Journal

# Import all models to register them with Base
from domain.user.models import User

# Avoid importing ChatSession due to metadata conflict
# from domain.coach.models import ChatSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Create all database tables."""
    settings = get_settings()

    # Create database engine
    engine = create_async_engine(settings.database_url, echo=True, pool_pre_ping=True)

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    logger.info("Database tables created successfully!")


async def main():
    """Main function."""
    print("=" * 50)
    print("AIWendy - Initialize Database")
    print("=" * 50)

    try:
        await init_database()
        print("\n✅ Database initialized successfully!")
        print("\nYou can now run the user initialization script:")
        print("  python scripts/init_user_simple.py")

    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
