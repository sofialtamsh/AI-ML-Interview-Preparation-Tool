from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from IPP_* environment variables (or backend/.env)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="IPP_", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://ipp:ipp@localhost:55432/ipp"

    # The SPA is served from the same origin as the API (Vite proxy in dev, reverse proxy in
    # prod), so CORS stays closed unless an origin is explicitly listed here.
    cors_origins: list[str] = []
    frontend_base_url: str = "http://localhost:5173"

    cookie_secure: bool = True
    admin_session_ttl_hours: int = 12
    admin_session_idle_minutes: int = 120
    student_session_ttl_days: int = 30
    password_reset_ttl_minutes: int = 30

    max_failed_logins: int = 5
    lockout_minutes: int = 15
    auth_rate_limit_per_minute: int = 20

    # AI provider. The key comes from the environment only and is never returned by the API.
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # AI spend is reported in weeks that start on this date's weekday, in this timezone.
    usage_tracking_start: date = date(2026, 10, 27)
    usage_timezone: str = "Asia/Kolkata"

    # Models are configuration, chosen per task (any OpenRouter model id that supports
    # structured outputs). Extraction runs once per record, so it defaults to a cheap model.
    model_extraction: str = "anthropic/claude-haiku-5.5"
    model_research: str = "google/gemini-3.8-flash"
    # Learning content is written once per topic and read by every student, so it uses a
    # stronger model. Narration uses OpenRouter text-to-speech.
    model_content: str = "anthropic/claude-sonnet-5.5"
    model_narration: str = "microsoft/mai-voice-2.1-flash"
    narration_voices: list[str] = [
        "en-IN-Priya:MAI-Voice-2.1-Flash",
        "en-IN-Dhruv:MAI-Voice-2.1-Flash",
    ]
    # OpenRouter's web search backend for the Market Research Agent. Exa returns page
    # excerpts, so quoted evidence can be checked against what the source says.
    research_search_engine: Literal["exa", "parallel", "perplexity", "firecrawl", "native"] = "exa"
    # Ceilings for any single agent run, whatever limit an admin enters.
    agent_max_records_per_run: int = 500
    agent_max_cost_per_run_usd: Decimal = Decimal("10")

    # Interview-source credentials are encrypted with these Fernet keys (comma-separated, newest
    # first). Rotate by prepending a new key and running `python -m app.cli rotate-credentials`.
    credentials_keys: SecretStr | None = None
    # Source fetching refuses private/internal network addresses (SSRF protection). Only turn
    # this on to test against a site running on your own machine; never in production.
    sources_allow_private_networks: bool = False
    # Background jobs (source fetches, later the agents) run in a thread inside the API process.
    # Set false when running a separate worker with `python -m app.cli run-worker`.
    embedded_worker: bool = True

    @field_validator("openrouter_api_key", "credentials_keys")
    @classmethod
    def _blank_key_is_unset(cls, value: SecretStr | None) -> SecretStr | None:
        return value if value and value.get_secret_value().strip() else None

    @field_validator("credentials_keys")
    @classmethod
    def _valid_fernet_keys(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            from cryptography.fernet import Fernet

            for key in value.get_secret_value().split(","):
                if key.strip():
                    try:
                        Fernet(key.strip().encode())
                    except (ValueError, TypeError):
                        # Never echo the key itself.
                        raise ValueError(
                            "IPP_CREDENTIALS_KEYS must be comma-separated Fernet keys; generate "
                            "one with `python -m app.cli generate-credentials-key`"
                        ) from None
        return value

    @field_validator("usage_timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        ZoneInfo(value)  # raises for an unknown zone
        return value

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("IPP_COOKIE_SECURE must be true in production")
        if self.environment == "production" and self.sources_allow_private_networks:
            raise ValueError("IPP_SOURCES_ALLOW_PRIVATE_NETWORKS must be false in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
