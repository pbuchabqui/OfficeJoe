"""
Hashing SHA-256 de documentos para garantia de integridade.
Princípio: o PDF original NUNCA é alterado; todo arquivo recebe hash auditável.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Union


CHUNK_SIZE = 65536  # 64 KB


def compute_sha256_bytes(data: bytes) -> str:
    """Calcula SHA-256 de um bytes objeto."""
    return hashlib.sha256(data).hexdigest()


def compute_sha256_stream(stream: io.IOBase) -> str:
    """
    Calcula SHA-256 lendo o stream em chunks sem carregar tudo em memória.
    Restaura a posição do stream após a leitura.
    """
    h = hashlib.sha256()
    pos = stream.tell() if hasattr(stream, "tell") else None
    try:
        while chunk := stream.read(CHUNK_SIZE):
            h.update(chunk)
    finally:
        if pos is not None:
            stream.seek(pos)
    return h.hexdigest()


def compute_sha256_file(path: Union[str, Path]) -> str:
    """Calcula SHA-256 de um arquivo em disco."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def verify_integrity(
    data: Union[bytes, io.IOBase, Path],
    expected_hash: str,
) -> bool:
    """
    Verifica se o hash do dado confere com o esperado.
    Retorna True apenas se os hashes correspondem exatamente.
    """
    if isinstance(data, bytes):
        actual = compute_sha256_bytes(data)
    elif isinstance(data, Path):
        actual = compute_sha256_file(data)
    else:
        actual = compute_sha256_stream(data)
    return actual.lower() == expected_hash.lower()


def hash_summary(hash_hex: str) -> str:
    """Retorna representação curta do hash para exibição (primeiros 12 chars)."""
    return hash_hex[:12] + "..."
