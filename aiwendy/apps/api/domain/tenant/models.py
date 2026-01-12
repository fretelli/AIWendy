"""Tenant/Organization models for multi-tenancy support (Cloud mode only)."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from core.database import Base
from sqlalchemy import (JSON, Boolean, Column, DateTime, Enum, ForeignKey,
                        Index, Integer, String, Text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class TenantPlan(str, enum.Enum):
    """Tenant subscription plans."""

    free = "free"
    starter = "starter"
    professional = "professional"
    enterprise = "enterprise"


class TenantStatus(str, enum.Enum):
    """Tenant account status."""

    active = "active"
    suspended = "suspended"
    trial = "trial"
    cancelled = "cancelled"


class Tenant(Base):
    """
    Tenant/Organization model for multi-tenancy.

    In cloud mode, all users belong to a tenant (organization).
    In self-hosted mode, this table is not used.
    """

    __tablename__ = "tenants"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization info
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True)  # Custom domain
    logo_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    # Subscription
    plan = Column(Enum(TenantPlan), default=TenantPlan.free, nullable=False)
    status = Column(Enum(TenantStatus), default=TenantStatus.trial, nullable=False)
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Resource limits (based on plan)
    max_users = Column(Integer, default=5)
    max_projects = Column(Integer, default=10)
    max_storage_gb = Column(Integer, default=5)
    max_api_calls_per_month = Column(Integer, default=10000)

    # Current usage
    current_users = Column(Integer, default=0)
    current_projects = Column(Integer, default=0)
    current_storage_gb = Column(Integer, default=0)
    current_api_calls_this_month = Column(Integer, default=0)

    # Settings
    settings = Column(
        JSON,
        default={
            "sso_enabled": False,
            "enforce_2fa": False,
            "ip_whitelist": [],
            "allowed_email_domains": [],
        },
    )

    # Billing contact
    billing_email = Column(String(255), nullable=True)
    billing_address = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    members = relationship("TenantMember", back_populates="tenant")

    # Indexes
    __table_args__ = (
        Index("ix_tenants_slug_active", "slug", "is_active"),
        Index("ix_tenants_status", "status", "plan"),
    )

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"

    @property
    def is_trial(self) -> bool:
        """Check if tenant is in trial period."""
        return self.status == TenantStatus.trial

    @property
    def is_subscription_active(self) -> bool:
        """Check if subscription is active."""
        if self.status != TenantStatus.active:
            return False
        if self.subscription_expires_at is None:
            return True  # Lifetime subscription
        return self.subscription_expires_at > datetime.utcnow()

    def can_add_user(self) -> bool:
        """Check if tenant can add more users."""
        return self.current_users < self.max_users

    def can_add_project(self) -> bool:
        """Check if tenant can add more projects."""
        return self.current_projects < self.max_projects


class TenantRole(str, enum.Enum):
    """Roles within a tenant/organization."""

    owner = "owner"  # Full control
    admin = "admin"  # Can manage users and settings
    member = "member"  # Regular user
    guest = "guest"  # Limited access


class TenantMember(Base):
    """
    Tenant membership - links users to tenants with roles.

    In cloud mode, users can belong to multiple tenants.
    """

    __tablename__ = "tenant_members"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Role
    role = Column(Enum(TenantRole), default=TenantRole.member, nullable=False)

    # Status
    is_active = Column(Boolean, default=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invitation_accepted_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])

    # Indexes
    __table_args__ = (
        Index("ix_tenant_members_tenant_user", "tenant_id", "user_id", unique=True),
        Index("ix_tenant_members_user_active", "user_id", "is_active"),
    )

    def __repr__(self):
        return f"<TenantMember(tenant_id={self.tenant_id}, user_id={self.user_id}, role={self.role})>"

    @property
    def is_owner(self) -> bool:
        """Check if member is owner."""
        return self.role == TenantRole.owner

    @property
    def is_admin(self) -> bool:
        """Check if member is admin or owner."""
        return self.role in (TenantRole.owner, TenantRole.admin)

    @property
    def can_manage_users(self) -> bool:
        """Check if member can manage other users."""
        return self.is_admin
