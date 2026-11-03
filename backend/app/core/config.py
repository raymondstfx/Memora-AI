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
    search_api_key: SecretStr = SecretStr("")
    search_base_url: str = "https://api.tavily.com"
    search_max_results: int = Field(default=5, ge=1, le=5)
    search_timeout_seconds: int = Field(default=15, ge=1, le=30)
    search_cache_ttl_seconds: int = Field(default=300, ge=0, le=3600)
    presentation_max_output_tokens: int = Field(default=6000, ge=1024, le=8192)
    presentation_job_timeout_seconds: int = Field(default=240, ge=30, le=600)
    presentation_conversion_timeout_seconds: int = Field(default=90, ge=10, le=180)
    presentation_node: str = "node"
    presentation_libreoffice: str = "libreoffice"
    llm_provider: str = "openai_compatible"
    llm_reasoning_effort: Literal["", "none", "minimal", "low", "medium", "high"] = ""
    provider_retry_max_wait_seconds: float = Field(default=15, ge=0, le=30)
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)
    llm_read_timeout_seconds: int = Field(default=30, ge=1, le=120)
    llm_total_timeout_seconds: int = Field(default=120, ge=5, le=300)
    llm_max_retries: int = Field(default=1, ge=0, le=2)
    llm_max_concurrent_requests: int = Field(default=2, ge=1, le=4)
    llm_max_output_tokens: int = Field(default=1024, ge=16, le=8192)
    llm_context_token_budget: int = Field(default=12000, ge=2048, le=64000)
    llm_token_parameter: Literal["max_completion_tokens", "max_tokens"] = (
        "max_completion_tokens"
    )
    embedding_provider: str = "openai_compatible"
    embedding_api_key: SecretStr = SecretStr("")
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = ""
    embedding_dimensions: int = Field(default=0, ge=0, le=4096)
    embedding_send_dimensions: bool = True
    embedding_timeout_seconds: int = Field(default=30, ge=1, le=120)
    embedding_max_retries: int = Field(default=1, ge=0, le=2)
    embedding_batch_size: int = Field(default=16, ge=1, le=64)
    embedding_normalize: bool = False
    embedding_max_input_bytes: int = Field(default=0, ge=0, le=12000)
    embedding_max_concurrent_requests: int = Field(default=1, ge=1, le=4)
    embedding_min_interval_seconds: float = Field(default=4, ge=0, le=60)
    embedding_cache_ttl_seconds: int = Field(default=86400, ge=60, le=604800)
    storage_root: Path = ROOT / "data" / "private"
    pdf_max_upload_bytes: int = Field(default=20971520, ge=1024, le=52428800)
    pdf_max_pages: int = Field(default=100, ge=1, le=500)
    pdf_max_text_chars: int = Field(default=1000000, ge=1000, le=2000000)
    pdf_parse_timeout_seconds: int = Field(default=30, ge=1, le=120)
    pdf_chunk_tokens: int = Field(default=600, ge=200, le=800)
    pdf_chunk_overlap: int = Field(default=100, ge=0, le=150)
    pdf_max_chunks: int = Field(default=2000, ge=1, le=5000)
    ingest_job_timeout_seconds: int = Field(default=300, ge=30, le=1800)
    ingest_max_active_jobs: int = Field(default=3, ge=1, le=10)
    rag_top_k: int = Field(default=5, ge=1, le=8)
    rag_min_similarity: float = Field(default=0.35, ge=0, le=1)
    meeting_max_upload_bytes: int = Field(default=65536, ge=1024, le=262144)
    meeting_max_input_bytes: int = Field(default=8000, ge=1000, le=24000)
    meeting_max_output_tokens: int = Field(default=3000, ge=512, le=8192)
    meeting_repair_attempts: int = Field(default=1, ge=0, le=1)
    smtp_mode: Literal["disabled", "local", "external"] = "disabled"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "memora@example.test"
    smtp_security: Literal["none", "starttls", "ssl"] = "starttls"
    smtp_timeout_seconds: int = Field(default=10, ge=1, le=30)
    smtp_external_send_enabled: bool = False
    demo_allowed_recipients: str = ""

    @field_validator("embedding_dimensions", mode="before")
    @classmethod
    def empty_dimension(cls, value: object) -> object:
        return 0 if value == "" else value

    @field_validator("storage_root")
    @classmethod
    def resolve_storage(cls, value: Path) -> Path:
        return value if value.is_absolute() else (ROOT / value).resolve()

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
