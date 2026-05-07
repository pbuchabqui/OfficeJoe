"""Serviço simples de chunking de texto."""
from __future__ import annotations


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Divide texto em chunks com sobreposição opcional.

    Args:
        text: Texto a dividir
        chunk_size: Tamanho máximo de cada chunk em caracteres
        overlap: Sobreposição entre chunks para preservar contexto

    Returns:
        Lista de chunks de texto
    """
    if not text or len(text) == 0:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(text):
        # Pega até chunk_size caracteres
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]

        # Tenta quebrar no final de uma sentença se possível
        if end < len(text):
            # Procura pelo último ponto, exclamação ou interrogação
            for sep in ['. ', '! ', '? ', '\n']:
                pos = chunk.rfind(sep)
                if pos > chunk_size // 2:  # Apenas se estiver no segundo meio do chunk
                    end = start + pos + len(sep)
                    chunk = text[start:end]
                    break

        chunks.append(chunk.strip())

        # Move para próxima posição com overlap
        start = end - overlap if overlap > 0 and end < len(text) else end

    return [c for c in chunks if c]  # Remove chunks vazios
