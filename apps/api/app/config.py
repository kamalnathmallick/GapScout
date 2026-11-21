"""Application configuration, loaded only from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    Every value can be overridden with an environment variable of the same
    name. ``.env`` is only a local convenience; production uses real env vars.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GapScout API"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://gapscout:gapscout@db:5432/gapscout"
    redis_url: str = "redis://redis:6379/0"
    scraper_base_url: str = "http://scraper:8080"
    secret_key: str = "dev-only-change-me"
    scraper_concurrency: int = 2
    max_cells_per_job: int = 200
    max_places_per_job: int = 5000
    geocoder_user_agent: str = "gapscout/1.0 (you@example.com)"

    # LLM Settings
    gemini_api_key: str = ""
    llm_model_fast: str = "gemini-2.5-flash"
    llm_model_quality: str = "gemini-2.5-pro"
    llm_daily_cost_cap_usd: float = 2.0

    # Comma-separated list, kept as a string so pydantic-settings does not try
    # to JSON-decode a plain env var.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
