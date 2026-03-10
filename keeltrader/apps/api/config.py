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
    openai_base_url: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    anthropic_base_url: Optional[str] = None

    # ========== Market Data API Keys ==========
    twelve_data_api_key: Optional[str] = None

    # ========== Exchange API Keys ==========
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

    # ========== CORS ==========
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: list[str] = ["*"]

    # ========== Logging ==========
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"

    # ========== Trade Sync ==========
    trade_sync_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("TRADE_SYNC_ENABLED", "trade_sync_enabled"),
    )
    trade_sync_interval_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "TRADE_SYNC_INTERVAL_SECONDS", "trade_sync_interval_seconds"
        ),
    )
    trade_sync_default_limit: int = Field(
        default=200,
        validation_alias=AliasChoices("TRADE_SYNC_DEFAULT_LIMIT", "trade_sync_default_limit"),
    )
    trade_sync_import_to_journal: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "TRADE_SYNC_IMPORT_TO_JOURNAL", "trade_sync_import_to_journal"
        ),
    )

    def is_self_hosted(self) -> bool:
        return self.deployment_mode == "self-hosted"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
