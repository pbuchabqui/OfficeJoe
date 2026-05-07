"""
Serviço de armazenamento de objetos (MinIO / S3).
Princípio: o arquivo original NUNCA é modificado após o upload.
"""
from __future__ import annotations

import io
import logging
from typing import Optional, Tuple
from urllib.parse import urljoin

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings

logger = logging.getLogger("officejoe.storage")
settings = get_settings()


class StorageService:
    """
    Abstração sobre MinIO/S3 para upload, download e geração de URLs pré-assinadas.
    Objetos são armazenados com ServerSideEncryption quando disponível.
    """

    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._ensure_buckets()

    def _ensure_buckets(self) -> None:
        for bucket in [settings.MINIO_BUCKET_DOCUMENTS, settings.MINIO_BUCKET_EXPORTS]:
            try:
                if not self._client.bucket_exists(bucket):
                    self._client.make_bucket(bucket)
                    logger.info("Bucket criado: %s", bucket)
            except S3Error as exc:
                logger.error("Erro ao verificar/criar bucket %s: %s", bucket, exc)
                raise

    def upload_document(
        self,
        file_stream: io.IOBase,
        object_key: str,
        file_size: int,
        content_type: str = "application/pdf",
        bucket: Optional[str] = None,
    ) -> str:
        """
        Faz upload de um documento para o bucket.
        Retorna o object_key confirmado.
        O arquivo original não é modificado – apenas lido.
        """
        bucket = bucket or settings.MINIO_BUCKET_DOCUMENTS
        try:
            result = self._client.put_object(
                bucket_name=bucket,
                object_name=object_key,
                data=file_stream,
                length=file_size,
                content_type=content_type,
            )
            logger.info(
                "Upload concluído: bucket=%s key=%s etag=%s",
                bucket, object_key, result.etag,
            )
            return object_key
        except S3Error as exc:
            logger.error("Falha no upload: bucket=%s key=%s erro=%s", bucket, object_key, exc)
            raise

    def download_to_stream(
        self,
        object_key: str,
        bucket: Optional[str] = None,
    ) -> Tuple[io.BytesIO, int]:
        """Baixa um objeto para memória. Retorna (stream, tamanho)."""
        bucket = bucket or settings.MINIO_BUCKET_DOCUMENTS
        try:
            response = self._client.get_object(bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            stream = io.BytesIO(data)
            return stream, len(data)
        except S3Error as exc:
            logger.error("Falha no download: bucket=%s key=%s erro=%s", bucket, object_key, exc)
            raise

    def generate_presigned_url(
        self,
        object_key: str,
        expires_seconds: int = 3600,
        bucket: Optional[str] = None,
    ) -> str:
        """Gera URL pré-assinada para acesso temporário (somente leitura)."""
        from datetime import timedelta
        bucket = bucket or settings.MINIO_BUCKET_DOCUMENTS
        try:
            url = self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_key,
                expires=timedelta(seconds=expires_seconds),
            )
            return url
        except S3Error as exc:
            logger.error("Falha ao gerar URL pré-assinada: %s", exc)
            raise

    def object_exists(self, object_key: str, bucket: Optional[str] = None) -> bool:
        bucket = bucket or settings.MINIO_BUCKET_DOCUMENTS
        try:
            self._client.stat_object(bucket, object_key)
            return True
        except S3Error:
            return False

    def delete_object(self, object_key: str, bucket: Optional[str] = None) -> None:
        """Remove objeto do storage. Use com cuidado – ação irreversível."""
        bucket = bucket or settings.MINIO_BUCKET_DOCUMENTS
        try:
            self._client.remove_object(bucket, object_key)
            logger.info("Objeto removido: bucket=%s key=%s", bucket, object_key)
        except S3Error as exc:
            logger.error("Falha ao remover objeto: %s", exc)
            raise


# Instância singleton
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
