import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # Application & Environment
    PROJECT_NAME: str = "YouTube Video Automation & Scheduling Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = "e9c5f8e12b7a4d6f8a9c3e2b1d0f5a7c4e8b2d6f9a1c3e5a7b9d2f4a6c8e0b2d"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./yt_automation.db"
    SYNC_DATABASE_URL: str = "sqlite:///./yt_automation.db"

    # Storage Abstraction
    STORAGE_PROVIDER: str = "local"
    TEMP_STORAGE_PATH: str = "./temp_storage"
    LOCAL_STORAGE_BASE_PATH: str = "./storage_test"

    # Google Drive & YouTube OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/drive/callback"
    YOUTUBE_REDIRECT_URI: str = "http://localhost:8000/api/v1/channels/oauth/youtube/callback"

    # Scheduler & Concurrency Engine Defaults
    SCHEDULER_HEARTBEAT_SECONDS: int = 60
    DEFAULT_UPLOAD_LEAD_MINUTES: int = 180
    MAX_UPLOAD_RETRIES: int = 5
    MAX_CONCURRENT_UPLOADS: int = 3
    PER_CHANNEL_MAX_CONCURRENT: int = 1
    CHANNEL_UPLOAD_COOLDOWN_SECONDS: int = 5

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("DATABASE_URL", mode="before")
    def format_async_db_url(cls, v):
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("SYNC_DATABASE_URL", mode="before")
    def format_sync_db_url(cls, v):
        # Check if environment variable DATABASE_URL is postgres while SYNC_DATABASE_URL is default/empty
        raw_db_url = os.environ.get("DATABASE_URL", "")
        if (not v or "sqlite" in v) and raw_db_url and ("postgres" in raw_db_url):
            v = raw_db_url

        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+psycopg2://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                return v.replace("postgresql://", "postgresql+psycopg2://", 1)
            elif v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
