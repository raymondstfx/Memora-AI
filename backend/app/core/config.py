from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://memora:memora_local_only@127.0.0.1:5432/memora"
    )
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    dependency_timeout_seconds: int = Field(default=3, ge=1, le=10)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: SecretStr) -> SecretStr:
        try:
            valid = (
                make_url(value.get_secret_value()).drivername == "postgresql+psycopg"
            )
        except Exception:
            valid = False
        if not valid:
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value

    @field_validator("redis_url")
    @classmethod
    def redis_only(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must use redis:// or rediss://")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
