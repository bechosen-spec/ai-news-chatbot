"""Environment-based application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI News Chatbot API"
    app_version: str = "0.2.0"
    app_env: str = "development"
    database_url: str = "sqlite:///./ai_news.db"
    model_path: Path = Path("ml/artifacts/selected_model.joblib")
    model_metadata_path: Path = Path("ml/artifacts/model_metadata.json")
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )
    log_level: str = "INFO"
    admin_api_key: SecretStr | None = None
    ingestion_timeout_seconds: float = Field(default=15.0, ge=1, le=60)
    ingestion_retry_limit: int = Field(default=3, ge=1, le=5)
    news_excerpt_max_characters: int = Field(default=1_500, ge=200, le=5_000)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value):
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
