"""Application settings.

The original code built the database URL from bare ``os.environ.get()`` calls
at import time, so a missing variable silently became the string ``"None"``
inside the DSN. Here the values are validated on first access and a
misconfigured deployment fails at startup instead of on the first request.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_db: str
    pgport: int = 5432

    celery_broker_url: str = "redis://backend-redis:6379/0"

    # Browser origins allowed to call the API. Read as a comma-separated list:
    # an env file is written by hand more often than generated.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    storage_dir: Path = BACKEND_DIR / "storage" / "files"

    # Uploads used to be unbounded and read into memory in one call.
    max_upload_bytes: int = 1024 * 1024 * 1024
    upload_chunk_bytes: int = 1024 * 1024

    # Both list endpoints used to return the whole table.
    default_page_size: int = 50
    max_page_size: int = 200

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.pgport}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached, so nothing is read from the environment at import time."""
    return Settings()
