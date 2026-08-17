"""Registration compatibility with retained legacy schema columns."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


def test_legacy_subscription_tier_has_database_default() -> None:
    migration = (
        REPO / "migrations/versions/047_default_legacy_subscription_tier.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "047"' in migration
    assert 'down_revision = "046"' in migration
    assert "SET DEFAULT 'free'::subscriptiontier" in migration
    assert "ALTER COLUMN subscription_tier DROP DEFAULT" in migration


def test_current_user_model_does_not_restore_retired_subscription_logic() -> None:
    model = (REPO / "apps/api/domain/user/models.py").read_text(encoding="utf-8")

    assert "subscription_tier = Column" not in model
