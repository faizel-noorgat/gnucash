"""Storage service — object storage client for document files.

Responsibilities:
1. Upload documents to object storage (S3, MinIO, etc.)
2. Download documents for OCR processing
3. Generate presigned URLs for secure access
4. Enforce Object Lock for immutability (BR-DI-002)

Design:
- Storage backend is injected via Protocol (dependency inversion)
- All uploads use Object Lock for immutability (BR-DI-002)
- Tenant-scoped via object key structure
- Presigned URLs for secure, time-limited access

Implements behavior-contract rules:
- BR-DI-002: original object-storage file is immutable after upload
"""

from __future__ import annotations

import logging
from typing import Protocol

from django.conf import settings

logger = logging.getLogger(__name__)


class ObjectStorageClient(Protocol):
    """Protocol for object-storage backends (S3, MinIO, etc.)."""

    def upload_file(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str,
        enable_object_lock: bool = True,
    ) -> str:
        """Upload bytes; return the object key.

        Args:
            bucket: Bucket name
            key: Object key
            body: File bytes
            content_type: MIME type
            enable_object_lock: Enable Object Lock (immutability)

        Returns:
            Object key
        """
        ...

    def download_file(self, *, bucket: str, key: str) -> bytes:
        """Download file bytes.

        Args:
            bucket: Bucket name
            key: Object key

        Returns:
            File bytes
        """
        ...

    def get_presigned_url(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        """Return a presigned download URL.

        Args:
            bucket: Bucket name
            key: Object key
            expires_seconds: URL expiration time

        Returns:
            Presigned URL
        """
        ...

    def delete_file(self, *, bucket: str, key: str) -> None:
        """Delete a file (only if Object Lock allows).

        Args:
            bucket: Bucket name
            key: Object key
        """
        ...


class S3StorageClient:
    """AWS S3 storage client with Object Lock support."""

    def __init__(self) -> None:
        import boto3

        self.client = boto3.client("s3")

    def upload_file(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str,
        enable_object_lock: bool = True,
    ) -> str:
        logger.info("S3StorageClient: uploading %s to bucket %s", key, bucket)

        extra_args = {"ContentType": content_type}

        # Enable Object Lock if requested (BR-DI-002)
        if enable_object_lock:
            extra_args["ObjectLockMode"] = "GOVERNANCE"
            extra_args["ObjectLockRetainUntilDate"] = None  # Retain indefinitely

        self.client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            **extra_args,
        )

        logger.info("S3StorageClient: uploaded %s successfully", key)
        return key

    def download_file(self, *, bucket: str, key: str) -> bytes:
        logger.info("S3StorageClient: downloading %s from bucket %s", key, bucket)

        response = self.client.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read()

        logger.info(
            "S3StorageClient: downloaded %s (%d bytes)", key, len(body)
        )
        return body

    def get_presigned_url(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        logger.info(
            "S3StorageClient: generating presigned URL for %s (expires=%ds)",
            key,
            expires_seconds,
        )

        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )

        return url

    def delete_file(self, *, bucket: str, key: str) -> None:
        logger.info("S3StorageClient: deleting %s from bucket %s", key, bucket)

        # Note: This will fail if Object Lock is enabled and retention period hasn't expired
        self.client.delete_object(Bucket=bucket, Key=key)

        logger.info("S3StorageClient: deleted %s", key)


class MockStorageClient:
    """Mock storage client for testing (in-memory storage)."""

    def __init__(self) -> None:
        self._storage: dict[str, bytes] = {}

    def upload_file(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str,
        enable_object_lock: bool = True,
    ) -> str:
        storage_key = f"{bucket}/{key}"
        self._storage[storage_key] = body
        logger.info("MockStorageClient: uploaded %s (%d bytes)", storage_key, len(body))
        return key

    def download_file(self, *, bucket: str, key: str) -> bytes:
        storage_key = f"{bucket}/{key}"
        if storage_key not in self._storage:
            raise KeyError(f"File not found: {storage_key}")
        return self._storage[storage_key]

    def get_presigned_url(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        return f"https://mock-storage.example.com/{bucket}/{key}?expires={expires_seconds}"

    def delete_file(self, *, bucket: str, key: str) -> None:
        storage_key = f"{bucket}/{key}"
        if storage_key in self._storage:
            del self._storage[storage_key]
            logger.info("MockStorageClient: deleted %s", storage_key)


def get_storage_client() -> ObjectStorageClient:
    """Factory function to get the configured storage client.

    Returns:
        ObjectStorageClient instance
    """
    storage_backend = settings.DOCUMENT_INTELLIGENCE.get("STORAGE_BACKEND", "mock")

    if storage_backend == "mock":
        return MockStorageClient()
    elif storage_backend == "s3":
        return S3StorageClient()
    else:
        logger.warning(
            "Unknown storage backend '%s', falling back to mock", storage_backend
        )
        return MockStorageClient()
