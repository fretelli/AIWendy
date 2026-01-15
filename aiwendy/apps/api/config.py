"""Application configuration management."""

from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ========== Application ==========
    app_name: str = "KeelTrader"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # ========== Deployment Mode ==========
    # "self-hosted" for open-source self-hosted deployments
    # "cloud" for managed SaaS deployments
    deployment_mode: str = Field(
        default="self-hosted",
        validation_alias=AliasChoices("DEPLOYMENT_MODE", "deployment_mode"),
    )

    # ========== Database ==========
    database_url: str = "postgresql+asyncpg://keeltrader:password@localhost:5432/keeltrader"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ========== Redis ==========
    redis_url: str = "redis://localhost:6379"
    redis_decode_responses: bool = True

    # ========== API URLs ==========
    # Base application URL (used for SSO metadata, callbacks, etc.)
    app_url: str = "http://localhost:8000"
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # ========== Auth ==========
    jwt_secret: str = Field(
        default="INSECURE-DEFAULT-CHANGE-ME-32CHARS-MIN",
        min_length=32,
        description="JWT secret key - MUST be changed in production (min 32 chars)",
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    auth_required: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "KEELTRADER_AUTH_REQUIRED",
            "AUTH_REQUIRED"
        ),
    )

    # Encryption key for API keys (separate from JWT secret)
    encryption_key: Optional[str] = Field(
        default=None,
        min_length=32,
        description="Encryption key for sensitive data (min 32 chars, base64 encoded)",
    )

    # ========== LLM API Keys ==========
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # ========== Market Data API Keys ==========
    twelve_data_api_key: Optional[str] = None

    # ========== Exchange API Keys ==========
    # Binance
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    # OKX
    okx_api_key: Optional[str] = None
    okx_api_secret: Optional[str] = None
    okx_passphrase: Optional[str] = None
    # Bybit
    bybit_api_key: Optional[str] = None
    bybit_api_secret: Optional[str] = None

    # ========== LLM Settings ==========
    llm_default_provider: str = "openai"
    llm_default_model: str = "gpt-4o-mini"
    llm_max_tokens: int = 2000
    llm_temperature: float = 0.7
    llm_stream_enabled: bool = True

    # ========== Rate Limiting ==========
    rate_limit_enabled: bool = True
    rate_limit_free_chat_hourly: int = 10
    rate_limit_free_journal_daily: int = 3
    rate_limit_pro_chat_hourly: int = 100
    rate_limit_pro_journal_daily: int = 999

    # ========== Monitoring ==========
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.1

    # ========== CORS ==========
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: list[str] = ["*"]

    # ========== Logging ==========
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"

    # ========== Celery ==========
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: list[str] = ["json"]
    celery_timezone: str = "UTC"

    # ========== Feature Flags ==========
    feature_analytics_enabled: bool = True
    feature_multi_coach_enabled: bool = True
    feature_voice_enabled: bool = False

    # ========== Cloud-Only Features ==========
    # Multi-tenancy (enabled only in cloud mode)
    multi_tenancy_enabled: bool = Field(default=False)
    tenant_isolation_strict: bool = Field(default=True)

    # Usage Analytics (PostHog, Mixpanel, etc.)
    analytics_provider: Optional[str] = None  # "posthog", "mixpanel", "amplitude"
    posthog_api_key: Optional[str] = None
    posthog_host: str = "https://app.posthog.com"
    mixpanel_token: Optional[str] = None

    # Enterprise SSO
    enterprise_sso_enabled: bool = Field(default=False)
    saml_enabled: bool = Field(default=False)
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_x509_cert: Optional[str] = None
    oauth_providers: list[str] = []  # ["google", "github", "azure", "okta"]

    def is_cloud_mode(self) -> bool:
        """Check if running in cloud/SaaS mode."""
        return self.deployment_mode == "cloud"

    def is_self_hosted(self) -> bool:
        """Check if running in self-hosted mode."""
        return self.deployment_mode == "self-hosted"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
