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
    app_version: str = "0.3.0"
    debug: bool = False
    environment: str = "development"

    # ========== Deployment Mode ==========
    # "self-hosted" for open-source self-hosted deployments
    # "cloud" for managed SaaS deployments
    deployment_mode: str = Field(
        default="self-hosted",
        validation_alias=AliasChoices("DEPLOYMENT_MODE", "deployment_mode"),
    )
    bind_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("KEELTRADER_BIND_HOST", "BIND_HOST"),
    )
    exposure_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("KEELTRADER_EXPOSURE_HOST", "EXPOSURE_HOST"),
    )
    web_exposure_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("KEELTRADER_WEB_EXPOSURE_HOST", "WEB_EXPOSURE_HOST"),
    )

    # ========== Database ==========
    database_url: str = "postgresql+asyncpg://keeltrader:password@localhost:5432/keeltrader"
    tushare_database_url: Optional[str] = None
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout_seconds: int = 15
    database_application_name: str = "keeltrader-api"
    tushare_database_pool_size: int = 3
    tushare_database_max_overflow: int = 1
    tushare_database_pool_timeout_seconds: int = 15
    tushare_database_pool_recycle_seconds: int = 1800
    tushare_database_statement_timeout_ms: int = 30000

    # ========== Redis ==========
    redis_url: str = "redis://localhost:6379"
    redis_decode_responses: bool = True

    # ========== API URLs ==========
    # Base application URL (used for SSO metadata, callbacks, etc.)
    app_url: str = "http://localhost:8000"
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    report_kb_url: Optional[str] = None
    report_kb_service_key: Optional[str] = None
    report_kb_timeout_seconds: float = 6.0
    market_publication_status_path: str = "/app/market-publication/publication-status.json"
    market_capability_manifest_path: str = "/app/market-publication/capability-manifest.json"
    agent_learning_bridge_path: str = "/app/agent-os-bridge"
    agent_knowledge_snapshot_path: str = "/app/agent-os-bridge/knowledge-snapshot.json"

    # Optional Research Cloud connection. Self-hosted deployments are offline
    # unless this is explicitly enabled by the administrator and then linked
    # by an individual user.
    research_cloud_enabled: bool = False
    research_cloud_base_url: Optional[str] = None
    research_cloud_timeout_seconds: float = 12.0

    # Optional deployment-owned content brief sink. The open-source default is
    # fully disabled; operators provide the endpoint, credentials and mapping.
    content_brief_sink_enabled: bool = False
    content_brief_sink_url: Optional[str] = None
    content_brief_sink_token: Optional[str] = None
    content_brief_sink_workspace_id: Optional[str] = None
    content_brief_sink_brand_profile_id: Optional[str] = None
    content_brief_sink_source_ref_prefix: Optional[str] = None
    content_brief_sink_actor_header: str = "X-Content-Actor"
    content_brief_sink_actor_prefix: str = "service:keeltrader"
    content_brief_sink_timeout_seconds: float = 8.0

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
    password_reset_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "KEELTRADER_PASSWORD_RESET_ENABLED",
            "PASSWORD_RESET_ENABLED",
            "password_reset_enabled",
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

    # Deployment-owned Agent model. Self-hosted installs must provide their own
    # values; there is deliberately no hosted fallback.
    agent_managed_provider: str = "openai"
    agent_managed_model: Optional[str] = None
    agent_managed_base_url: Optional[str] = None
    agent_managed_api_key: Optional[str] = None
    agent_managed_context_window: int = 128000
    agent_managed_max_output_tokens: int = 4096
    agent_model_timeout_seconds: float = 300.0

    # ========== CORS ==========
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: list[str] = ["*"]

    # ========== Logging ==========
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"

    def is_self_hosted(self) -> bool:
        return self.deployment_mode == "self-hosted"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
