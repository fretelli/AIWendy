"""
Migration script to convert self-hosted deployment to multi-tenant cloud mode.

This script:
1. Creates a default tenant for existing users
2. Associates all existing users with the default tenant
3. Migrates existing data to be tenant-aware

Usage:
    python scripts/migrate_to_multi_tenant.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from core.database import engine, get_db_session
from domain.tenant.models import (Tenant, TenantMember, TenantPlan, TenantRole,
                                  TenantStatus)
from domain.user.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_default_tenant(session: AsyncSession) -> Tenant:
    """Create a default tenant for existing users."""
    print("Creating default tenant...")

    tenant = Tenant(
        name="Default Organization",
        slug="default",
        plan=TenantPlan.enterprise,  # Give existing users enterprise plan
        status=TenantStatus.active,
        max_users=999,
        max_projects=999,
        max_storage_gb=999,
        max_api_calls_per_month=999999,
    )

    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    print(f"✓ Created default tenant: {tenant.name} (ID: {tenant.id})")
    return tenant


async def migrate_users_to_tenant(session: AsyncSession, tenant: Tenant):
    """Associate all existing users with the default tenant."""
    print("\nMigrating users to tenant...")

    # Get all users
    result = await session.execute(select(User))
    users = result.scalars().all()

    if not users:
        print("No users found to migrate.")
        return

    print(f"Found {len(users)} users to migrate")

    # Create tenant memberships
    for user in users:
        # Check if membership already exists
        existing = await session.execute(
            select(TenantMember).where(
                TenantMember.tenant_id == tenant.id,
                TenantMember.user_id == user.id,
            )
        )
        if existing.scalar_one_or_none():
            print(f"  - User {user.email} already has membership, skipping")
            continue

        # Determine role based on user status
        role = TenantRole.owner if user.is_admin else TenantRole.member

        membership = TenantMember(
            tenant_id=tenant.id,
            user_id=user.id,
            role=role,
            is_active=True,
        )

        session.add(membership)
        print(f"  ✓ Added {user.email} as {role.value}")

    # Update tenant user count
    tenant.current_users = len(users)

    await session.commit()
    print(f"\n✓ Migrated {len(users)} users to tenant")


async def verify_migration(session: AsyncSession, tenant: Tenant):
    """Verify the migration was successful."""
    print("\nVerifying migration...")

    # Count users
    user_result = await session.execute(select(User))
    user_count = len(user_result.scalars().all())

    # Count memberships
    membership_result = await session.execute(
        select(TenantMember).where(TenantMember.tenant_id == tenant.id)
    )
    membership_count = len(membership_result.scalars().all())

    print(f"  Users: {user_count}")
    print(f"  Memberships: {membership_count}")

    if user_count == membership_count:
        print("✓ Migration verified successfully!")
        return True
    else:
        print("✗ Migration verification failed - user count mismatch")
        return False


async def main():
    """Run the migration."""
    settings = get_settings()

    print("=" * 60)
    print("AIWendy Multi-Tenant Migration Script")
    print("=" * 60)

    # Check deployment mode
    if not settings.is_cloud_mode():
        print("\n⚠️  WARNING: DEPLOYMENT_MODE is not set to 'cloud'")
        print("This script should only be run when migrating to cloud mode.")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            return

    # Check if multi-tenancy is enabled
    if not settings.multi_tenancy_enabled:
        print("\n⚠️  WARNING: MULTI_TENANCY_ENABLED is not set to true")
        print("Please set MULTI_TENANCY_ENABLED=true in your .env file")
        return

    print("\nThis script will:")
    print("1. Create a default tenant organization")
    print("2. Associate all existing users with this tenant")
    print("3. Migrate existing data to be tenant-aware")
    print("\n⚠️  Make sure you have backed up your database before proceeding!")

    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() != "yes":
        print("Migration cancelled.")
        return

    try:
        async with get_db_session() as session:
            # Check if default tenant already exists
            result = await session.execute(
                select(Tenant).where(Tenant.slug == "default")
            )
            existing_tenant = result.scalar_one_or_none()

            if existing_tenant:
                print(f"\n✓ Default tenant already exists: {existing_tenant.name}")
                tenant = existing_tenant
            else:
                tenant = await create_default_tenant(session)

            # Migrate users
            await migrate_users_to_tenant(session, tenant)

            # Verify migration
            success = await verify_migration(session, tenant)

            if success:
                print("\n" + "=" * 60)
                print("Migration completed successfully!")
                print("=" * 60)
                print("\nNext steps:")
                print("1. Restart your application")
                print("2. Verify that users can log in")
                print("3. Check that all data is accessible")
                print("4. Configure billing and SSO if needed")
            else:
                print("\n" + "=" * 60)
                print("Migration completed with warnings")
                print("=" * 60)
                print("\nPlease review the output above and verify manually.")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
