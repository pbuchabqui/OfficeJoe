"""
Testes do endpoint de health check.

Testa a rota GET /api/v1/health sem dependência de banco, Redis ou MinIO —
usa o TestClient síncrono para verificar estrutura de resposta e status code.

As rotas /health/db, /health/redis e /health/storage são testadas
com mocks para evitar dependência de infraestrutura em CI.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# ── /health ───────────────────────────────────────────────────────────────────

def test_health_returns_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_body_has_required_fields():
    response = client.get("/api/v1/health")
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "env" in data


def test_health_status_is_ok():
    response = client.get("/api/v1/health")
    assert response.json()["status"] == "ok"


def test_health_has_request_id_header():
    response = client.get("/api/v1/health")
    assert "x-request-id" in response.headers


def test_health_has_process_time_header():
    response = client.get("/api/v1/health")
    assert "x-process-time" in response.headers


def test_health_content_type_is_json():
    response = client.get("/api/v1/health")
    assert "application/json" in response.headers["content-type"]


# ── /health/db ────────────────────────────────────────────────────────────────

def test_health_db_ok_when_db_responds():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=None)
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.health.AsyncSessionLocal", return_value=mock_ctx):
        response = client.get("/api/v1/health/db")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "postgresql"


def test_health_db_503_when_db_unreachable():
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(
        side_effect=ConnectionRefusedError("Banco indisponível")
    )
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.health.AsyncSessionLocal", return_value=mock_ctx):
        response = client.get("/api/v1/health/db")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["service"] == "postgresql"
    assert "detail" in data


# ── /health/redis ─────────────────────────────────────────────────────────────

def test_health_redis_ok_when_redis_responds():
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.aclose = AsyncMock()

    with patch("app.api.v1.health.aioredis.from_url", return_value=mock_client):
        response = client.get("/api/v1/health/redis")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "redis"


def test_health_redis_503_when_redis_unreachable():
    with patch(
        "app.api.v1.health.aioredis.from_url",
        side_effect=ConnectionRefusedError("Redis indisponível"),
    ):
        response = client.get("/api/v1/health/redis")

    assert response.status_code == 503
    assert response.json()["service"] == "redis"


# ── /health/storage ───────────────────────────────────────────────────────────

def test_health_storage_ok_when_minio_responds():
    mock_minio = MagicMock()
    mock_minio.bucket_exists = MagicMock(return_value=True)

    with patch("app.api.v1.health.Minio", return_value=mock_minio):
        response = client.get("/api/v1/health/storage")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "minio"
    assert data["bucket_exists"] is True


def test_health_storage_reports_bucket_not_created():
    mock_minio = MagicMock()
    mock_minio.bucket_exists = MagicMock(return_value=False)

    with patch("app.api.v1.health.Minio", return_value=mock_minio):
        response = client.get("/api/v1/health/storage")

    # Serviço acessível mesmo sem o bucket criado ainda
    assert response.status_code == 200
    assert response.json()["bucket_exists"] is False


def test_health_storage_503_when_minio_unreachable():
    with patch(
        "app.api.v1.health.Minio",
        side_effect=Exception("MinIO indisponível"),
    ):
        response = client.get("/api/v1/health/storage")

    assert response.status_code == 503
    assert response.json()["service"] == "minio"


# ── Rota inexistente ──────────────────────────────────────────────────────────

def test_unknown_route_returns_404():
    response = client.get("/api/v1/rota-inexistente")
    assert response.status_code == 404
