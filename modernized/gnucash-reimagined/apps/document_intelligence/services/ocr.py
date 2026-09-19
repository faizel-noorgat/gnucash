"""OCR service — calls external OCR provider and captures provenance.

Responsibilities:
1. Invoke OCR provider (pluggable: aws_textract, google_document_ai, mock)
2. Capture full OCR provenance (provider, model version, timestamp)
3. Return structured OCR result for downstream extraction
4. NEVER mutate Document - only create DocumentExtraction rows

Design:
- OCR provider is injected via Protocol (dependency inversion)
- All OCR calls are logged for audit trail (BR-DI-008)
- Provider failures are caught and logged, not swallowed
- Returns OCRResult TypedDict for type safety

Implements behavior-contract rules:
- BR-DI-008: provenance fields are complete (provider, model_version, timestamp)
- BR-DI-003: OCR outputs are append-only (never modify previous extractions)
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol, TypedDict

from django.conf import settings

from ..models import Document

logger = logging.getLogger(__name__)


class OCRResult(TypedDict):
    """Structured OCR output from provider."""

    raw_text: str
    blocks: list[dict]
    provider: str
    model_version: str
    processing_time_ms: float


class OCRProvider(Protocol):
    """Pluggable OCR provider interface."""

    def extract(self, *, document: Document) -> OCRResult:
        """Extract text from document.

        Args:
            document: Document to extract text from

        Returns:
            OCRResult with raw_text, blocks, provider, model_version

        Raises:
            Exception: If OCR fails (caller handles retry/fallback)
        """
        ...


class BaseOCRProvider:
    """Base class for OCR providers with common functionality."""

    def __init__(self, provider_name: str, model_version: str) -> None:
        self.provider_name = provider_name
        self.model_version = model_version

    def _build_result(
        self, raw_text: str, blocks: list[dict], processing_time_ms: float
    ) -> OCRResult:
        """Build OCRResult with provenance."""
        return OCRResult(
            raw_text=raw_text,
            blocks=blocks,
            provider=self.provider_name,
            model_version=self.model_version,
            processing_time_ms=processing_time_ms,
        )


class MockOCRProvider(BaseOCRProvider):
    """Mock OCR provider for testing."""

    def __init__(self) -> None:
        super().__init__("mock", "1.0.0")

    def extract(self, *, document: Document) -> OCRResult:
        logger.info("MockOCRProvider: extracting document %s", document.guid)
        return self._build_result(
            raw_text="Mock OCR text for testing",
            blocks=[{"type": "LINE", "text": "Mock line 1"}],
            processing_time_ms=10.0,
        )


class AWSTextractProvider(BaseOCRProvider):
    """AWS Textract OCR provider.

    Requires AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY environment variables.
    Requires boto3 package installed.
    """

    def __init__(self) -> None:
        super().__init__("aws_textract", "textract-2024")
        import boto3

        self.client = boto3.client("textract")

    def extract(self, *, document: Document) -> OCRResult:
        import time

        start_time = time.time()

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

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "AWSTextractProvider: extracted %d blocks in %.2fms for document %s",
            len(blocks),
            processing_time_ms,
            document.guid,
        )

        return self._build_result(
            raw_text=raw_text,
            blocks=blocks,
            processing_time_ms=processing_time_ms,
        )


class GoogleDocumentAIProvider(BaseOCRProvider):
    """Google Document AI OCR provider.

    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable.
    Requires google-cloud-documentai package installed.
    """

    def __init__(self) -> None:
        super().__init__("google_document_ai", "document-ai-v1")
        from google.cloud import documentai

        self.client = documentai.DocumentProcessorServiceClient()

    def extract(self, *, document: Document) -> OCRResult:
        import time

        start_time = time.time()

        # Download document from S3
        from .storage import get_storage_client

        storage = get_storage_client()
        file_bytes = storage.download_file(
            bucket=settings.DOCUMENT_INTELLIGENCE["S3_BUCKET"],
            key=document.original_file_key,
        )

        # Call Document AI
        # TODO: Implement Google Document AI processing
        # This is a placeholder - real implementation would use the Document AI API

        processing_time_ms = (time.time() - start_time) * 1000

        logger.warning(
            "GoogleDocumentAIProvider: not yet implemented for document %s",
            document.guid,
        )

        return self._build_result(
            raw_text="",
            blocks=[],
            processing_time_ms=processing_time_ms,
        )


def get_ocr_provider() -> OCRProvider:
    """Factory function to get the configured OCR provider.

    Dispatches on `settings.DOCUMENT_INTELLIGENCE["OCR_PROVIDER"]` so no
    particular OCR vendor is hard-wired into the orchestration code.

    Recognised values:
        "mock" (default), "aws_textract", "google_document_ai"
        ("google_documentai" is accepted as an alias of the latter).

    Unknown values fall back to the mock provider with a warning rather than
    raising, matching `services.storage.get_storage_client`.

    Returns:
        OCRProvider instance
    """
    conf = settings.DOCUMENT_INTELLIGENCE
    provider_name = conf.get("OCR_PROVIDER", "mock")

    if provider_name == "mock":
        return MockOCRProvider()
    elif provider_name == "aws_textract":
        return AWSTextractProvider()
    elif provider_name in ("google_document_ai", "google_documentai"):
        return GoogleDocumentAIProvider()
    else:
        logger.warning(
            "Unknown OCR provider '%s', falling back to mock", provider_name
        )
        return MockOCRProvider()


class OCRService:
    """Orchestrates OCR extraction with provider selection and fallback.

    Usage:
        service = OCRService()
        ocr_result = service.run_ocr(document)
    """

    def __init__(self, provider: OCRProvider | None = None) -> None:
        """Initialize OCR service.

        Args:
            provider: OCR provider to use. If None, uses configured default.
        """
        self.provider = provider or self._get_default_provider()

    def _get_default_provider(self) -> OCRProvider:
        """Get default OCR provider from settings (see `get_ocr_provider`)."""
        return get_ocr_provider()

    def run_ocr(self, document: Document) -> OCRResult:
        """Run OCR on a document.

        Args:
            document: Document to process

        Returns:
            OCRResult with extracted text and provenance

        Raises:
            Exception: If OCR fails (caller should handle and create failed extraction)
        """
        logger.info(
            "OCRService: running OCR on document %s (tenant=%s)",
            document.guid,
            document.tenant_id,
        )

        try:
            result = self.provider.extract(document=document)

            logger.info(
                "OCRService: OCR completed for document %s (provider=%s, "
                "model=%s, time=%.2fms)",
                document.guid,
                result["provider"],
                result["model_version"],
                result["processing_time_ms"],
            )

            return result

        except Exception as e:
            logger.exception(
                "OCRService: OCR failed for document %s", document.guid
            )
            raise
