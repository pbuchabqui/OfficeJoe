"""
Endpoints de health check.

Quatro verificações independentes:
  GET /api/v1/health          — status da aplicação (sempre rápido)
  GET /api/v1/health/db       — conectividade com PostgreSQL
  GET /api/v1/health/redis    — conectividade com Redis
  GET /api/v1/health/storage  — conectividade com MinIO

Cada endpoint retorna 200 em caso de sucesso e 503 em caso de falha,
com detalhes do erro para facilitar diagnóstico em desenvolvimento.
Não requer autenticação — usado por balanceadores de carga e probes k8s.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings

logger = logging.getLogger("officejoe.health")
settings = get_settings()
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Status da aplicação")
async def health() -> dict:
    """Retorna 200 imediatamente. Indica que o processo está de pé."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }


@router.get("/db", summary="Conectividade com PostgreSQL")
async def health_db() -> JSONResponse:
    """Executa SELECT 1 para validar a conexão com o banco."""
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok", "service": "postgresql"})
    except Exception as exc:
        logger.error("health/db falhou: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "service": "postgresql", "detail": str(exc)},
        )


@router.get("/redis", summary="Conectividade com Redis")
async def health_redis() -> JSONResponse:
    """Executa PING para validar a conexão com o Redis."""
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        pong = await client.ping()
        await client.aclose()
        if not pong:
            raise RuntimeError("PING retornou falso")
        return JSONResponse({"status": "ok", "service": "redis"})
    except Exception as exc:
        logger.error("health/redis falhou: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "service": "redis", "detail": str(exc)},
        )


@router.get("/storage", summary="Conectividade com MinIO / S3")
async def health_storage() -> JSONResponse:
    """Verifica se o bucket principal existe e está acessível."""
    try:
        from minio import Minio

        client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        exists = client.bucket_exists(settings.MINIO_BUCKET_DOCUMENTS)
        return JSONResponse({
            "status": "ok",
            "service": "minio",
            "bucket": settings.MINIO_BUCKET_DOCUMENTS,
            "bucket_exists": exists,
        })
    except Exception as exc:
        logger.error("health/storage falhou: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "service": "minio", "detail": str(exc)},
        )
