from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DOT_ENV_PATH = "/media/ibrahim/data/Apps_ideas/secrets/JobHunter/.env"

class Settings(BaseSettings):
    BACKEND_BASE_URL: str = "http://localhost:8000"
    BACKEND_TIMEOUT_SECONDS: float = 15.0

    # Read config from .env file and validate it
    model_config = SettingsConfigDict(env_file=str(DOT_ENV_PATH), extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type, call-arg]
