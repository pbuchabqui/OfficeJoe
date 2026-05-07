"""
Ponto de entrada da aplicação FastAPI — fase inicial.

Registra apenas:
  - middleware de CORS
  - middleware de headers de segurança
  - middleware de rastreamento de requisições (request-id + latência)
  - router de health check
  - handler de exceções não tratadas

Módulos de autenticação, upload, OCR, processos e IA
serão adicionados em prompts subsequentes.
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.cases import router as cases_router
from app.api.v1.custody import router as custody_router
from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("officejoe")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "Iniciando %s v%s [%s]",
        settings.APP_TITLE, settings.APP_VERSION, settings.APP_ENV,
    )
    yield
    logger.info("Encerrando aplicação.")


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    # Desabilita docs em produção
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    openapi_url="/openapi.json" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


# ── Rastreamento de requisições ───────────────────────────────────────────────
@app.middleware("http")
async def request_tracking(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}ms"
    logger.info(
        "%s %s → %d (%.1fms) [%s]",
        request.method, request.url.path,
        response.status_code, elapsed_ms, request_id,
    )
    return response


# ── Headers de segurança ──────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── Handler global de exceções ────────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Exceção não tratada em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno. Contate o suporte."},
    )


# ── Rotas ─────────────────────────────────────────────────────────────────────
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(custody_router, prefix="/api/v1")
