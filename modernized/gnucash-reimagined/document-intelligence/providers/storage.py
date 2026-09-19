"""Object storage client interface and factory.

Provides S3-compatible object storage for document uploads.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from django.conf import settings


class ObjectStorageClient(Protocol):
    """Object storage client interface."""

    def upload_file(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str,
        enable_object_lock: bool = True,
    ) -> str:
        """Upload bytes; return the object key."""
        ...

    def download_file(self, *, bucket: str, key: str) -> bytes:
        """Download bytes."""
        ...

    def get_presigned_url(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        """Return a presigned download URL."""
        ...


class BaseObjectStorageClient(ABC):
    """Base class for object storage clients."""

    @abstractmethod
    def upload_file(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str,
        enable_object_lock: bool = True,
    ) -> str:
        pass

    @abstractmethod
    def download_file(self, *, bucket: str, key: str) -> bytes:
        pass

    @abstractmethod
    def get_presigned_url(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        pass


class S3ObjectStorageClient(BaseObjectStorageClient):
    """AWS S3 / MinIO object storage client."""

    def __init__(self) -> None:
        import boto3

        conf = settings.DOCUMENT_INTELLIGENCE
        endpoint_url = conf.get("S3_ENDPOINT_URL")
        self.client = boto3.client("s3", endpoint_url=endpoint_url)

    def upload_file(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str,
        enable_object_lock: bool = True,
    ) -> str:
        extra_args = {"ContentType": content_type}
        if enable_object_lock:
            # S3 Object Lock requires bucket to be configured with Object Lock
            # For now, we just upload without explicit lock parameters
            # (the bucket-level configuration handles it)
            pass

        self.client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            **extra_args,
        )
        return key

    def download_file(self, *, bucket: str, key: str) -> bytes:
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def get_presigned_url(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )


class MockObjectStorageClient(BaseObjectStorageClient):
    """Mock object storage client for testing."""

    def __init__(self) -> None:
        self.storage: dict[str, bytes] = {}

    def upload_file(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str,
        enable_object_lock: bool = True,
    ) -> str:
        full_key = f"{bucket}/{key}"
        self.storage[full_key] = body
        return key

    def download_file(self, *, bucket: str, key: str) -> bytes:
        full_key = f"{bucket}/{key}"
        if full_key not in self.storage:
            raise FileNotFoundError(f"Object not found: {full_key}")
        return self.storage[full_key]

    def get_presigned_url(self, *, bucket: str, key: str, expires_seconds: int) -> str:
        return f"https://mock-s3.example.com/{bucket}/{key}?expires={expires_seconds}"


def get_storage_client() -> BaseObjectStorageClient:
    """Factory function to get the configured storage client."""
    # In test mode, use mock
    if settings.DOCUMENT_INTELLIGENCE.get("S3_ENDPOINT_URL") is None and settings.DEBUG:
        return MockObjectStorageClient()

    # Otherwise use real S3
    return S3ObjectStorageClient()
