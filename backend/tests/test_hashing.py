"""
Testes para o módulo de hashing SHA-256.
"""
from __future__ import annotations

import io
import hashlib
import tempfile
from pathlib import Path

import pytest

from app.core.hashing import (
    compute_sha256_bytes,
    compute_sha256_file,
    compute_sha256_stream,
    hash_summary,
    verify_integrity,
)

SAMPLE_CONTENT = b"Conteudo de teste para verificacao de integridade pericial"
EXPECTED_HASH = hashlib.sha256(SAMPLE_CONTENT).hexdigest()


def test_compute_sha256_bytes():
    result = compute_sha256_bytes(SAMPLE_CONTENT)
    assert result == EXPECTED_HASH
    assert len(result) == 64
    assert result.islower()


def test_compute_sha256_bytes_empty():
    result = compute_sha256_bytes(b"")
    assert len(result) == 64
    assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_compute_sha256_stream():
    stream = io.BytesIO(SAMPLE_CONTENT)
    result = compute_sha256_stream(stream)
    assert result == EXPECTED_HASH
    # Stream deve ser restaurado à posição original
    assert stream.tell() == 0


def test_compute_sha256_stream_restores_position():
    stream = io.BytesIO(SAMPLE_CONTENT)
    stream.seek(10)
    compute_sha256_stream(stream)
    assert stream.tell() == 10


def test_compute_sha256_file():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(SAMPLE_CONTENT)
        tmp_path = Path(tmp.name)
    try:
        result = compute_sha256_file(tmp_path)
        assert result == EXPECTED_HASH
    finally:
        tmp_path.unlink()


def test_verify_integrity_bytes_ok():
    assert verify_integrity(SAMPLE_CONTENT, EXPECTED_HASH) is True


def test_verify_integrity_bytes_fail():
    tampered = SAMPLE_CONTENT + b"ALTERADO"
    assert verify_integrity(tampered, EXPECTED_HASH) is False


def test_verify_integrity_stream_ok():
    stream = io.BytesIO(SAMPLE_CONTENT)
    assert verify_integrity(stream, EXPECTED_HASH) is True


def test_verify_integrity_case_insensitive():
    assert verify_integrity(SAMPLE_CONTENT, EXPECTED_HASH.upper()) is True


def test_hash_summary():
    summary = hash_summary(EXPECTED_HASH)
    assert summary.endswith("...")
    assert len(summary) == 15  # 12 + "..."


def test_different_content_different_hash():
    h1 = compute_sha256_bytes(b"documento_1")
    h2 = compute_sha256_bytes(b"documento_2")
    assert h1 != h2
