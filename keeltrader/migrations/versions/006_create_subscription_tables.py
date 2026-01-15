"""Create subscription tables

Revision ID: 006
Revises: 005
Create Date: 2024-12-30

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    # Create subscription_plans table
    op.create_table(
        "subscription_plans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "plan_type",
            sa.Enum("free", "pro", "elite", "enterprise", name="plantype"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Pricing
        sa.Column("monthly_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("yearly_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("monthly_price_cny", sa.Numeric(10, 2), nullable=True),
        sa.Column("yearly_price_cny", sa.Numeric(10, 2), nullable=True),
        # Stripe IDs
        sa.Column("stripe_monthly_price_id", sa.String(255), nullable=True),
        sa.Column("stripe_yearly_price_id", sa.String(255), nullable=True),
        sa.Column("stripe_product_id", sa.String(255), nullable=True),
        # Features
        sa.Column("features", sa.JSON(), default=list),
        sa.Column("limits", sa.JSON(), default=dict),
        # Limits
        sa.Column("max_journals_per_day", sa.Integer(), default=-1),
        sa.Column("max_ai_chats_per_day", sa.Integer(), default=-1),
        sa.Column("max_reports_per_month", sa.Integer(), default=-1),
        sa.Column("max_coaches", sa.Integer(), default=3),
        # Feature flags
        sa.Column("has_premium_coaches", sa.Boolean(), default=False),
        sa.Column("has_api_access", sa.Boolean(), default=False),
        sa.Column("has_priority_support", sa.Boolean(), default=False),
        sa.Column("has_custom_reports", sa.Boolean(), default=False),
        sa.Column("has_team_features", sa.Boolean(), default=False),
        sa.Column("has_white_label", sa.Boolean(), default=False),
        # Display
        sa.Column("is_popular", sa.Boolean(), default=False),
        sa.Column("display_order", sa.Integer(), default=0),
        sa.Column("badge_text", sa.String(50), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_visible", sa.Boolean(), default=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    # Create user_subscriptions table
    op.create_table(
        "user_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subscription_plans.id"),
            nullable=False,
        ),
        # Subscription details
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "trialing",
                "past_due",
                "canceled",
                "unpaid",
                "incomplete",
                "incomplete_expired",
                name="subscriptionstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "billing_interval",
            sa.Enum("monthly", "yearly", "lifetime", name="billinginterval"),
            nullable=False,
        ),
        # Stripe IDs
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True, unique=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_payment_method_id", sa.String(255), nullable=True),
        # Dates
        sa.Column("trial_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        # Payment
        sa.Column("next_payment_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("next_payment_date", sa.DateTime(timezone=True), nullable=True),
        # Metadata
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    # Create indexes for user_subscriptions
    op.create_index(
        "ix_user_subscriptions_user_status", "user_subscriptions", ["user_id", "status"]
    )
    op.create_index(
        "ix_user_subscriptions_stripe_id",
        "user_subscriptions",
        ["stripe_subscription_id"],
    )

    # Create payments table
    op.create_table(
        "payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_subscriptions.id"),
            nullable=True,
        ),
        # Payment details
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "succeeded",
                "failed",
                "canceled",
                "refunded",
                name="paymentstatus",
            ),
            nullable=False,
            default="pending",
        ),
        # Stripe IDs
        sa.Column(
            "stripe_payment_intent_id", sa.String(255), nullable=True, unique=True
        ),
        sa.Column("stripe_invoice_id", sa.String(255), nullable=True),
        sa.Column("stripe_charge_id", sa.String(255), nullable=True),
        # Payment method
        sa.Column("payment_method_type", sa.String(50), nullable=True),
        sa.Column("last_four", sa.String(4), nullable=True),
        sa.Column("card_brand", sa.String(50), nullable=True),
        # Details
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("receipt_url", sa.Text(), nullable=True),
        # Metadata
        sa.Column("metadata", sa.JSON(), nullable=True),
        # Dates
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    # Create indexes for payments
    op.create_index("ix_payments_user_status", "payments", ["user_id", "status"])
    op.create_index(
        "ix_payments_stripe_intent", "payments", ["stripe_payment_intent_id"]
    )

    # Create promo_codes table
    op.create_table(
        "promo_codes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        # Discount
        sa.Column("discount_type", sa.String(20), nullable=False),
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False),
        # Applicable plans
        sa.Column("applicable_plans", sa.JSON(), default=list),
        # Usage limits
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("uses_count", sa.Integer(), default=0),
        sa.Column("max_uses_per_user", sa.Integer(), default=1),
        # Validity
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        # Stripe
        sa.Column("stripe_coupon_id", sa.String(255), nullable=True),
        sa.Column("stripe_promotion_code_id", sa.String(255), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), default=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    # Create index for promo_codes
    op.create_index("ix_promo_codes_code_active", "promo_codes", ["code", "is_active"])

    # Add relationship columns to users table if not exists
    op.add_column(
        "users", sa.Column("stripe_subscription_id", sa.String(255), nullable=True)
    )


def downgrade():
    # Drop columns from users table
    op.drop_column("users", "stripe_subscription_id")

    # Drop indexes
    op.drop_index("ix_promo_codes_code_active", table_name="promo_codes")
    op.drop_index("ix_payments_stripe_intent", table_name="payments")
    op.drop_index("ix_payments_user_status", table_name="payments")
    op.drop_index("ix_user_subscriptions_stripe_id", table_name="user_subscriptions")
    op.drop_index("ix_user_subscriptions_user_status", table_name="user_subscriptions")

    # Drop tables
    op.drop_table("promo_codes")
    op.drop_table("payments")
    op.drop_table("user_subscriptions")
    op.drop_table("subscription_plans")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS plantype")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
    op.execute("DROP TYPE IF EXISTS billinginterval")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
