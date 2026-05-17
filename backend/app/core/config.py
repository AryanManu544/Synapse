from functools import lru_cache
from typing import Literal

LogFormat = Literal["json", "text"]

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Synapse API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    log_format: LogFormat = "json"

    api_v1_prefix: str = "/api/v1"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://synapse:synapse@localhost:5432/synapse"
    )
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    review_lock_processing_ttl_seconds: int = 3_600
    review_lock_completed_ttl_seconds: int = 86_400

    github_webhook_secret: str = ""
    github_app_id: str = ""
    github_app_private_key_path: str = ""
    github_app_private_key: str = ""

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_default_provider: Literal["openai", "anthropic"] = "openai"
    llm_default_model: str = "gpt-4o"
    llm_max_retries: int = 3
    llm_retry_base_delay_seconds: float = 1.0
    llm_max_diff_chars: int = 120_000

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Accept Supabase `postgresql://` URLs and ensure SSL for hosted Postgres."""
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql://"):
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
        host = value.split("@")[-1].split("/")[0].lower()
        if "supabase.com" in host and "ssl=" not in value and "sslmode=" not in value:
            separator = "&" if "?" in value else "?"
            value = f"{value}{separator}ssl=require"
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def default_celery_urls(self) -> Settings:
        redis = str(self.redis_url)
        if not self.celery_broker_url:
            self.celery_broker_url = redis
        if not self.celery_result_backend:
            self.celery_result_backend = redis
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
