"""PrepAI Backend – Core configuration using pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Application
    APP_NAME: str = "PrepAI Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Gemini AI
    GEMINI_API_KEY: str

    # Database
    DATABASE_URL: str

    # CORS – allowed origins (comma-separated in .env)
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()  # type: ignore[call-arg]
