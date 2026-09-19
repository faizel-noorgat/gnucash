"""OCR Celery task — runs the extraction pipeline asynchronously."""

from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction

from ..models import Document

logger = logging.getLogger(__name__)


@shared_task(
    name="document_intelligence.tasks.ocr.run_ocr_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def run_ocr_task(self, document_guid: str) -> dict:
    """Run OCR + extraction pipeline on a document.

    This is the entry point for async document processing.
    Retries up to 3 times on transient failures.
    """
    from ..services.extraction import ExtractionService
    from ..providers.ocr import get_ocr_provider
    from ..providers.extraction import get_extraction_engine
    from ..providers.ai import get_ai_suggester

    try:
        document = Document.objects.get(guid=document_guid)
    except Document.DoesNotExist:
        logger.error("Document %s not found", document_guid)
        return {"status": "error", "message": "Document not found"}

    # Skip if already duplicate
    if document.is_duplicate:
        logger.info("Skipping duplicate document %s", document_guid)
        return {"status": "skipped", "reason": "duplicate"}

    # Build services
    ocr_provider = get_ocr_provider()
    extraction_engine = get_extraction_engine()
    ai_suggester = get_ai_suggester()

    service = ExtractionService(
        ocr_provider=ocr_provider,
        extraction_engine=extraction_engine,
        ai_suggester=ai_suggester,
    )

    try:
        extraction = service.run_extraction(document)
        return {
            "status": "success",
            "extraction_guid": str(extraction.guid),
            "version": extraction.version,
            "confidence": str(extraction.confidence_score) if extraction.confidence_score else None,
        }
    except Exception as e:
        logger.exception("OCR task failed for document %s", document_guid)
        # Retry on transient failures
        raise self.retry(exc=e)
