from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import quote_plus

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url

LogFormat = Literal["json", "text"]
GITHUB_WEBHOOK_PLACEHOLDER = "whsec_your_github_webhook_secret_here"


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

    # NoDecode: Render sets CORS_ORIGINS=https://app.vercel.app (not JSON array).
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    database_url: str = Field(
        default="postgresql+asyncpg://synapse:synapse@localhost:5432/synapse"
    )
    # Prefer these on Render/Supabase — password is not URL-encoded manually.
    db_host: str = ""
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = ""
    db_name: str = "postgres"
    db_pool_size_async: int = 3
    db_pool_size_sync: int = 2

    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    celery_worker_concurrency: int = Field(
        default=2,
        validation_alias=AliasChoices(
            "celery_worker_concurrency",
            "CELERY_WORKER_CONCURRENCY",
            "CELERYD_CONCURRENCY",
        ),
    )

    review_lock_processing_ttl_seconds: int = 3_600
    review_lock_completed_ttl_seconds: int = 86_400

    github_webhook_secret: str = ""
    github_app_id: str = ""
    github_app_private_key_path: str = ""
    github_app_private_key: str = ""
    # Single-line base64 of the .pem file — best for Render env vars.
    github_app_private_key_b64: str = ""

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    # OpenAI-compatible base URL for Groq (https://api.groq.com/openai/v1).
    groq_api_base: str = "https://api.groq.com/openai/v1"

    llm_default_provider: Literal["openai", "groq"] = "openai"
    llm_default_model: str = "gpt-4o"
    llm_max_retries: int = 3
    llm_retry_base_delay_seconds: float = 1.0
    llm_max_diff_chars: int = 120_000
    # Render free tier (512MB): run reviews in-process instead of a Celery worker.
    run_reviews_inline: bool = False

    @field_validator("run_reviews_inline", mode="before")
    @classmethod
    def parse_run_reviews_inline(cls, value: str | bool) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Accept Supabase `postgresql://` URLs and ensure SSL for hosted Postgres."""
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql://"):
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
        parsed = make_url(value)
        host = (parsed.host or "").lower()
        if "supabase.com" in host and "ssl=" not in value and "sslmode=" not in value:
            separator = "&" if "?" in value else "?"
            value = f"{value}{separator}ssl=require"
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("github_app_private_key_b64", mode="before")
    @classmethod
    def strip_private_key_b64_quotes(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                return value[1:-1]
        return value

    @staticmethod
    def _build_database_url(host: str, port: int, user: str, password: str, name: str) -> str:
        url = (
            f"postgresql+asyncpg://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{name}"
        )
        if "supabase.com" in host.lower():
            url += "?ssl=require"
        return url

    @model_validator(mode="after")
    def assemble_and_validate_urls(self) -> Settings:
        if (
            not self.github_webhook_secret.strip()
            or self.github_webhook_secret == GITHUB_WEBHOOK_PLACEHOLDER
        ):
            raise ValueError(
                "GitHub webhook secret missing or still a placeholder. Set "
                "GITHUB_WEBHOOK_SECRET from your GitHub App settings page."
            )

        if not self.github_app_id.strip():
            raise ValueError(
                "GitHub App ID missing. Set GITHUB_APP_ID from your GitHub App settings page."
            )

        if self.llm_default_provider == "openai" and not self.openai_api_key.strip():
            raise ValueError("OPENAI_API_KEY is required when LLM_DEFAULT_PROVIDER=openai.")

        if self.llm_default_provider == "groq" and not self.groq_api_key.strip():
            raise ValueError("GROQ_API_KEY is required when LLM_DEFAULT_PROVIDER=groq.")

        if self.db_password and self.db_host:
            self.database_url = self._build_database_url(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                name=self.db_name,
            )

        parsed = make_url(self.database_url)
        password = parsed.password or ""
        username = parsed.username or ""
        host = (parsed.host or "").lower()

        if "[" in self.database_url or password in {"", "[YOUR-PASSWORD]"}:
            raise ValueError(
                "Database password missing or still a placeholder. On Render, set "
                "DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (recommended) or a "
                "complete DATABASE_URL with the real Supabase database password."
            )

        if "pooler.supabase.com" in host:
            if username == "postgres":
                raise ValueError(
                    "Supabase pooler username must be postgres.<project-ref>, not 'postgres'. "
                    "Set DB_USER from Supabase → Database → Connection string (Transaction, 6543)."
                )
            if not username.startswith("postgres."):
                raise ValueError(
                    f"Supabase pooler DB_USER must be postgres.<project-ref>, got '{username}'."
                )

        if not self.celery_broker_url:
            self.celery_broker_url = self.redis_url
        if not self.celery_result_backend:
            self.celery_result_backend = self.redis_url

        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
