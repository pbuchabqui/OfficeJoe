"""
Configurações centralizadas via Pydantic BaseSettings.
Lê variáveis de ambiente e do arquivo .env.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import List, Literal

from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Aplicação ────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_SECRET_KEY: str
    APP_DEBUG: bool = False
    APP_VERSION: str = "1.0.0"
    APP_TITLE: str = "OfficeJoe – Plataforma de Perícias Contábeis"
    APP_ALLOWED_HOSTS: List[str] = ["http://localhost:3000"]

    @field_validator("APP_ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: str | list) -> list:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ── JWT ──────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── PostgreSQL ───────────────────────────────────────────────────────
    DATABASE_URL: str
    POSTGRES_DB: str = "officejoe"

    # ── Redis / Celery ───────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # ── MinIO / S3 ───────────────────────────────────────────────────────
    STORAGE_BACKEND: Literal["minio", "s3"] = "minio"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_DOCUMENTS: str = "officejoe-documents"
    MINIO_BUCKET_EXPORTS: str = "officejoe-exports"
    MINIO_SECURE: bool = False

    # ── OCR ──────────────────────────────────────────────────────────────
    OCR_ENGINE: Literal["paddleocr", "tesseract", "auto"] = "paddleocr"
    OCR_LANGUAGE: str = "por+eng"
    OCR_DPI: int = 300
    OCR_MAX_PAGES_PER_TASK: int = 50
    OCR_CONFIDENCE_THRESHOLD: float = 0.6

    # ── IA ───────────────────────────────────────────────────────────────
    AI_PROVIDER: Literal["anthropic", "openai", "local"] = "anthropic"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-6"
    AI_MAX_TOKENS: int = 4096
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    PGVECTOR_DIMENSIONS: int = 1536

    VECTOR_BACKEND: Literal["pgvector", "qdrant"] = "pgvector"
    QDRANT_URL: str = "http://qdrant:6333"

    # ── Segurança ─────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = ["pdf"]
    BCRYPT_ROUNDS: int = 12

    @field_validator("ALLOWED_UPLOAD_EXTENSIONS", mode="before")
    @classmethod
    def parse_extensions(cls, v: str | list) -> list:
        if isinstance(v, str):
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def validate_secrets_strength(self) -> "Settings":
        if len(self.APP_SECRET_KEY) < 32:
            raise ValueError("APP_SECRET_KEY deve ter ao menos 32 caracteres")
        if len(self.JWT_SECRET_KEY) < 32:
            raise ValueError("JWT_SECRET_KEY deve ter ao menos 32 caracteres")
        return self

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
