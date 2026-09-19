"""Extraction service — orchestrates OCR + structured extraction + AI suggestion.

Responsibilities:
1. Invoke OCR provider (pluggable: aws_textract, google_document_ai, mock)
2. Run structured extraction (supplier, dates, amounts, line items, tax)
3. Look up AccountingMappings for AI suggestion (BR-DI-007)
4. Compute confidence score + evidence (BR-DI-006, BR-DI-008)
5. If confidence < threshold, create ReviewQueue entry
6. Create NEW DocumentExtraction row (never mutate previous — BR-DI-003, BR-DI-009)
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol, TypedDict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import (
    Document,
    DocumentExtraction,
    ExtractionStatus,
    ExtractionVersion,
    MappingSuggestion,
    ReviewQueue,
    ReviewStatus,
)

logger = logging.getLogger(__name__)


class OCRResult(TypedDict):
    raw_text: str
    blocks: list[dict]
    provider: str
    model_version: str


class ExtractionResult(TypedDict):
    supplier_name: str | None
    supplier_party_id: uuid.UUID | None
    customer_name: str | None
    invoice_number: str | None
    invoice_date: str | None
    due_date: str | None
    currency: str | None
    total_amount: str | None
    tax_amount: str | None
    line_items: list[dict]


class OCRProvider(Protocol):
    """Pluggable OCR provider interface."""

    def extract(self, *, document: Document) -> OCRResult: ...


class ExtractionEngine(Protocol):
    """Pluggable structured-extraction engine."""

    def extract(self, *, ocr_result: OCRResult, document: Document) -> ExtractionResult: ...


class AISuggester(Protocol):
    """Pluggable AI suggester (returns suggestions + evidence)."""

    def suggest(
        self,
        *,
        tenant_id: uuid.UUID,
        extraction_result: ExtractionResult,
        document: Document,
    ) -> tuple[dict, float, dict]: ...


class ExtractionService:
    """Orchestrates OCR + extraction + AI suggestion."""

    def __init__(
        self,
        ocr_provider: OCRProvider,
        extraction_engine: ExtractionEngine,
        ai_suggester: AISuggester | None = None,
    ) -> None:
        self.ocr_provider = ocr_provider
        self.extraction_engine = extraction_engine
        self.ai_suggester = ai_suggester
        self.conf = settings.DOCUMENT_INTELLIGENCE

    def run_extraction(self, document: Document) -> DocumentExtraction:
        """Run full extraction pipeline on a document.

        Always creates a NEW DocumentExtraction row with version+1.
        Never mutates a previous extraction (BR-DI-003, BR-DI-009).
        """
        with transaction.atomic():
            # Get or create version counter
            version_counter, _ = ExtractionVersion.objects.select_for_update().get_or_create(
                document=document,
                defaults={"current_version": 0},
            )
            new_version = version_counter.next_version()

            # Create extraction row in QUEUED state
            extraction = DocumentExtraction.objects.create(
                document=document,
                version=new_version,
                ocr_provider=self.conf.get("OCR_PROVIDER", "unknown"),
                ocr_model_version="",
                extraction_model_version="",
                status=ExtractionStatus.QUEUED,
            )

        try:
            # Step 1: OCR
            extraction.status = ExtractionStatus.OCR_IN_PROGRESS
            extraction.save(update_fields=["status"])

            ocr_result = self.ocr_provider.extract(document=document)

            # Step 2: Structured extraction
            extraction.status = ExtractionStatus.EXTRACTION_IN_PROGRESS
            extraction.ocr_model_version = ocr_result["model_version"]
            extraction.save(update_fields=["status", "ocr_model_version"])

            extraction_result = self.extraction_engine.extract(
                ocr_result=ocr_result, document=document
            )

            # Step 3: AI suggestion (if enabled)
            ai_suggestion = None
            confidence_score = None
            confidence_evidence = None
            if self.ai_suggester and self.conf.get("AI_SUGGESTIONS_ENABLED"):
                ai_suggestion, confidence_score, confidence_evidence = (
                    self.ai_suggester.suggest(
                        tenant_id=document.tenant_id,
                        extraction_result=extraction_result,
                        document=document,
                    )
                )

            # Step 4: Persist completed extraction
            extraction.extraction_result = extraction_result
            extraction.ai_suggestion = ai_suggestion
            extraction.confidence_score = confidence_score
            extraction.confidence_evidence = confidence_evidence
            extraction.status = ExtractionStatus.COMPLETED
            extraction.save()

            # Step 5: Route to review queue if low confidence (BR-DI-006)
            threshold = self.conf.get("AI_CONFIDENCE_THRESHOLD", 0.80)
            if confidence_score is not None and confidence_score < threshold:
                ReviewQueue.objects.create(
                    tenant_id=document.tenant_id,
                    document=document,
                    extraction=extraction,
                    status=ReviewStatus.OPEN,
                    priority=int((threshold - confidence_score) * 100),
                    reason="low_confidence",
                )
                document.status = "in_review"
                document.save(update_fields=["status"])

            logger.info(
                "Extraction %s v%s completed (conf=%s)",
                extraction.guid,
                new_version,
                confidence_score,
            )
            return extraction

        except Exception as e:
            logger.exception("Extraction failed for document %s", document.guid)
            extraction.status = ExtractionStatus.OCR_FAILED
            extraction.save(update_fields=["status"])
            raise

    def apply_human_correction(
        self,
        *,
        extraction: DocumentExtraction,
        correction: dict,
        reviewer_id: uuid.UUID,
        note: str = "",
    ) -> DocumentExtraction:
        """Apply a human correction by creating a NEW extraction version.

        BR-DI-004: corrections create v+1, never mutate previous.
        """
        with transaction.atomic():
            version_counter = ExtractionVersion.objects.select_for_update().get(
                document=extraction.document
            )
            new_version = version_counter.next_version()

            # Mark previous extraction as reviewed
            extraction.reviewed_by = reviewer_id
            extraction.reviewed_at = timezone.now()
            extraction.save(update_fields=["reviewed_by", "reviewed_at"])

            # Create new extraction with corrections
            corrected_extraction = DocumentExtraction.objects.create(
                document=extraction.document,
                version=new_version,
                ocr_provider=extraction.ocr_provider,
                ocr_model_version=extraction.ocr_model_version,
                extraction_model_version=extraction.extraction_model_version,
                extraction_result=extraction.extraction_result,
                ai_suggestion=extraction.ai_suggestion,
                confidence_score=extraction.confidence_score,
                confidence_evidence=extraction.confidence_evidence,
                is_human_correction=True,
                human_correction=correction,
                correction_note=note,
                reviewed_by=reviewer_id,
                reviewed_at=timezone.now(),
                status=ExtractionStatus.COMPLETED,
            )

            # Close review queue item
            ReviewQueue.objects.filter(extraction=extraction).update(
                status=ReviewStatus.CORRECTED,
                decided_by=reviewer_id,
                decided_at=timezone.now(),
            )

            logger.info(
                "Human correction applied: extraction %s v%s -> v%s",
                extraction.guid,
                extraction.version,
                new_version,
            )
            return corrected_extraction
