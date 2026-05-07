"""Provider de embeddings mockado para busca semântica."""
from __future__ import annotations

import hashlib
import math


class MockEmbedding:
    """Provider de embedding que gera vetores determinísticos baseados no hash do texto."""

    DIMENSION = 384

    @staticmethod
    def embed(text: str) -> list[float]:
        """
        Gera um vetor de embedding determinístico a partir do texto.

        Usa hash SHA-256 do texto para gerar uma sequência pseudo-aleatória
        que é expandida para DIMENSION elementos.

        Args:
            text: Texto a embeddar

        Returns:
            Lista com DIMENSION elementos normalizados entre -1 e 1
        """
        # Gera hash determinístico
        hash_bytes = hashlib.sha256(text.encode()).digest()

        # Expande hash para 384 dimensões usando valores trigonométricos
        embedding: list[float] = []
        for i in range(MockEmbedding.DIMENSION):
            # Usa bytes do hash como seed
            seed = int.from_bytes(hash_bytes[(i % len(hash_bytes)) : (i % len(hash_bytes)) + 1], 'big')
            # Gera valor usando sin/cos para variedade
            value = math.sin(seed + i) if i % 2 == 0 else math.cos(seed + i)
            embedding.append(value)

        # Normaliza para magnitude 1 (L2 normalization)
        magnitude = math.sqrt(sum(x ** 2 for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding

    @staticmethod
    def similarity(embedding1: list[float], embedding2: list[float]) -> float:
        """
        Calcula similaridade de cosseno entre dois embeddings.

        Args:
            embedding1: Primeiro vetor
            embedding2: Segundo vetor

        Returns:
            Score de similaridade entre 0 e 1
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings devem ter mesma dimensionalidade")

        # Produto escalar (dot product)
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

        # Ambos já estão normalizados, então similaridade = dot product
        return max(0.0, min(1.0, (dot_product + 1) / 2))  # Normaliza para [0, 1]
