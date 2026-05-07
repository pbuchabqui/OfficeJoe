from __future__ import annotations

import hashlib
import io

from app.core.hashing import compute_sha256_bytes, compute_sha256_stream, verify_integrity


def test_compute_sha256_bytes_matches_hashlib():
    content = b"documento pericial inicial"

    assert compute_sha256_bytes(content) == hashlib.sha256(content).hexdigest()


def test_compute_sha256_stream_preserves_position():
    stream = io.BytesIO(b"conteudo com posicao preservada")
    stream.seek(8)

    digest = compute_sha256_stream(stream)

    assert digest == hashlib.sha256(stream.getvalue()[8:]).hexdigest()
    assert stream.tell() == 8


def test_verify_integrity_detects_tampering():
    original = b"arquivo original"
    expected_hash = hashlib.sha256(original).hexdigest()

    assert verify_integrity(original, expected_hash) is True
    assert verify_integrity(original + b" alterado", expected_hash) is False
