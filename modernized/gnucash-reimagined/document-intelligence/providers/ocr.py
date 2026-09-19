"""OCR provider interface and factory.

Pluggable OCR backends: AWS Textract, Google Document AI, Mock (for tests).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from django.conf import settings

from ..models import Document


class OCRResult(dict):
    """Structured OCR output."""

    raw_text: str
    blocks: list[dict]
    provider: str
    model_version: str


class OCRProvider(Protocol):
    """OCR provider interface."""

    def extract(self, *, document: Document) -> OCRResult: ...


class BaseOCRProvider(ABC):
    """Base class for OCR providers."""

    @abstractmethod
    def extract(self, *, document: Document) -> OCRResult:
        pass


class MockOCRProvider(BaseOCRProvider):
    """Mock OCR provider for testing."""

    def extract(self, *, document: Document) -> OCRResult:
        return OCRResult(
            raw_text="Mock OCR text",
            blocks=[],
            provider="mock",
            model_version="1.0.0",
        )


class AWSTextractProvider(BaseOCRProvider):
    """AWS Textract OCR provider.

    Requires AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY environment variables.
    """

    def __init__(self) -> None:
        import boto3

        self.client = boto3.client("textract")

    def extract(self, *, document: Document) -> OCRResult:
        # Download document from S3
        from .storage import get_storage_client

        storage = get_storage_client()
        file_bytes = storage.download_file(
            bucket=settings.DOCUMENT_INTELLIGENCE["S3_BUCKET"],
            key=document.original_file_key,
        )

        # Call Textract
        response = self.client.detect_document_text(Document={"Bytes": file_bytes})

        # Parse response
        blocks = response.get("Blocks", [])
        raw_text = " ".join(
            b.get("Text", "") for b in blocks if b.get("BlockType") == "LINE"
        )

        return OCRResult(
            raw_text=raw_text,
            blocks=blocks,
            provider="aws_textract",
            model_version="textract-2024",
        )


def get_ocr_provider() -> BaseOCRProvider:
    """Factory function to get the configured OCR provider."""
    provider_name = settings.DOCUMENT_INTELLIGENCE.get("OCR_PROVIDER", "mock")

    if provider_name == "mock":
        return MockOCRProvider()
    elif provider_name == "aws_textract":
        return AWSTextractProvider()
    else:
        raise ValueError(f"Unknown OCR provider: {provider_name}")
