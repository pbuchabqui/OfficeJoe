"""
Configurações da aplicação lidas de variáveis de ambiente / arquivo .env.
Apenas os parâmetros necessários para inicializar a API nesta fase.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Aplicação ─────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    APP_TITLE: str = "OfficeJoe API"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str
    APP_ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("APP_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v: str | list) -> list:
        return json.loads(v) if isinstance(v, str) else v

    # ── PostgreSQL ────────────────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:5432/db

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── MinIO / S3 ────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_DOCUMENTS: str = "officejoe-documents"
    MINIO_SECURE: bool = False

    @model_validator(mode="after")
    def _validate_secret_strength(self) -> "Settings":
        if len(self.APP_SECRET_KEY) < 32:
            raise ValueError("APP_SECRET_KEY precisa ter ao menos 32 caracteres")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
