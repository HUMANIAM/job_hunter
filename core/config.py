import logging
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
POSTGRES_ENV_FILE = ROOT_DIR / ".env.postgres"
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    ENVIRONMENT: str = "dev"

    # Base URLs
    BACKEND_BASE_URL: str = "http://localhost:8000"
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    DATABASE_URL: str = ""
    SQLALCHEMY_ECHO: bool = False

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.4-mini"

    model_config = SettingsConfigDict(
        env_file=str(POSTGRES_ENV_FILE),
        extra="ignore",
    )

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        if value:
            return value

        logger.critical(
            "Failed to load settings: DATABASE_URL is required. Checked %s.",
            POSTGRES_ENV_FILE,
        )
        raise ValueError("DATABASE_URL is required")


@lru_cache
def get_settings() -> Settings:
    return Settings()
