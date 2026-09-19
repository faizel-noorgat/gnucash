"""Extraction service — structured extraction from OCR results.

Responsibilities:
1. Convert raw OCR output into structured extraction (supplier, dates, amounts, etc.)
2. Persist structured result in DocumentExtraction (append-only, BR-DI-003)
3. Trigger AI suggestion pipeline (if enabled)
4. Route to review queue if confidence < threshold (BR-DI-006)
5. NEVER mutate previous extractions - always create new version

Design:
- Extraction engine is injected via Protocol (dependency inversion)
- Supports pluggable engines: rule-based, LLM-based, hybrid
- All extractions preserve full provenance (BR-DI-008)
- Workflow: document → extraction → matching → mapping/suggestion → review

Implements behavior-contract rules:
- BR-DI-003: extraction is append-only (version field, never modify previous)
- BR-DI-004: human corrections create new version, never mutate
- BR-DI-006: low confidence routes to review queue
- BR-DI-008: full provenance captured
- BR-DI-009: AI outputs never directly post journals
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
)
from .ocr import OCRProvider, OCRResult

logger = logging.getLogger(__name__)


class ExtractionResult(TypedDict):
    """Structured extraction output."""

    supplier_name: str | None
    supplier_party_id: uuid.UUID | None
    customer_name: str | None
    customer_party_id: uuid.UUID | None
    invoice_number: str | None
    invoice_date: str | None
    due_date: str | None
    currency: str | None
    total_amount: str | None
    tax_amount: str | None
    subtotal_amount: str | None
    line_items: list[dict]
    payment_terms: str | None
    notes: str | None


class ExtractionEngine(Protocol):
    """Pluggable structured-extraction engine."""

    def extract(
        self, *, ocr_result: OCRResult, document: Document
    ) -> ExtractionResult:
        """Extract structured data from OCR result.

        Args:
            ocr_result: Raw OCR output
            document: Source document

        Returns:
            ExtractionResult with structured fields
        """
        ...


class MockExtractionEngine:
    """Mock extraction engine for testing."""

    def extract(
        self, *, ocr_result: OCRResult, document: Document
    ) -> ExtractionResult:
        logger.info("MockExtractionEngine: extracting from document %s", document.guid)
        return ExtractionResult(
            supplier_name="Mock Supplier",
            supplier_party_id=None,
            customer_name=None,
            customer_party_id=None,
            invoice_number="INV-001",
            invoice_date="2024-01-15",
            due_date="2024-02-15",
            currency="SGD",
            total_amount="100.00",
            tax_amount="7.00",
            subtotal_amount="93.00",
            line_items=[
                {
                    "description": "Item 1",
                    "quantity": "1",
                    "unit_price": "100.00",
                    "total": "100.00",
                }
            ],
            payment_terms="Net 30",
            notes=None,
        )


class RuleBasedExtractionEngine:
    """Rule-based extraction engine using regex patterns.

    This is a simplified implementation. Production would use more
    sophisticated NLP or call an external extraction service.
    """

    def extract(
        self, *, ocr_result: OCRResult, document: Document
    ) -> ExtractionResult:
        import re

        text = ocr_result["raw_text"]

        # Simple regex patterns (very naive — real impl would be more robust)
        invoice_match = re.search(r"Invoice[:\s#]+([A-Z0-9-]+)", text, re.IGNORECASE)
        date_match = re.search(r"Date[:\s]+(\d{4}-\d{2}-\d{2})", text)
        amount_match = re.search(r"Total[:\s]+\$?([\d,]+\.\d{2})", text, re.IGNORECASE)

        logger.info("RuleBasedExtractionEngine: extracting from %d chars", len(text))

        return ExtractionResult(
            supplier_name=None,  # Would need NER
            supplier_party_id=None,
            customer_name=None,
            customer_party_id=None,
            invoice_number=invoice_match.group(1) if invoice_match else None,
            invoice_date=date_match.group(1) if date_match else None,
            due_date=None,
            currency="SGD",  # Default
            total_amount=amount_match.group(1) if amount_match else None,
            tax_amount=None,
            subtotal_amount=None,
            line_items=[],
            payment_terms=None,
            notes=None,
        )


class LLMExtractionEngine:
    """LLM-based extraction engine using external LLM API.

    Requires LLM_API_KEY environment variable.
    Supports OpenAI, Anthropic, etc.
    """

    def __init__(self, llm_provider: str = "openai") -> None:
        self.llm_provider = llm_provider
        # TODO: Initialize LLM client

    def extract(
        self, *, ocr_result: OCRResult, document: Document
    ) -> ExtractionResult:
        logger.warning(
            "LLMExtractionEngine: not yet implemented for document %s", document.guid
        )
        # TODO: Implement LLM-based extraction
        return ExtractionResult(
            supplier_name=None,
            supplier_party_id=None,
            customer_name=None,
            customer_party_id=None,
            invoice_number=None,
            invoice_date=None,
            due_date=None,
            currency=None,
            total_amount=None,
            tax_amount=None,
            subtotal_amount=None,
            line_items=[],
            payment_terms=None,
            notes=None,
        )


def get_extraction_engine() -> ExtractionEngine:
    """Factory function to get the configured extraction engine.

    Dispatches on `settings.DOCUMENT_INTELLIGENCE["EXTRACTION_ENGINE"]` so no
    particular extraction vendor is hard-wired into the orchestration code.

    Recognised values:
        "mock" (default), "rule_based", "llm"

    Unknown values fall back to the mock engine with a warning rather than
    raising, matching `services.storage.get_storage_client`.

    Returns:
        ExtractionEngine instance
    """
    conf = settings.DOCUMENT_INTELLIGENCE
    engine_name = conf.get("EXTRACTION_ENGINE", "mock")

    if engine_name == "mock":
        return MockExtractionEngine()
    elif engine_name == "rule_based":
        return RuleBasedExtractionEngine()
    elif engine_name == "llm":
        return LLMExtractionEngine(llm_provider=conf.get("LLM_PROVIDER", "openai"))
    else:
        logger.warning(
            "Unknown extraction engine '%s', falling back to mock", engine_name
        )
        return MockExtractionEngine()


class ExtractionService:
    """Orchestrates structured extraction from OCR results.

    Usage (unified — caller supplies a pre-computed OCR result):
        service = ExtractionService()
        extraction = service.run_extraction(document, ocr_result)

    Usage (legacy — service owns the OCR step):
        service = ExtractionService(
            extraction_engine=get_extraction_engine(),
            ocr_provider=get_ocr_provider(),
            ai_suggester=get_ai_suggester(),
        )
        extraction = service.run_extraction(document)
    """

    def __init__(
        self,
        engine: ExtractionEngine | None = None,
        ai_suggester: "AISuggester | None" = None,
        *,
        extraction_engine: ExtractionEngine | None = None,
        ocr_provider: OCRProvider | None = None,
    ) -> None:
        """Initialize extraction service.

        Args:
            engine: Extraction engine to use. If None, uses configured default.
            ai_suggester: Optional AI suggester for accounting suggestions.
            extraction_engine: Legacy alias for `engine` (accepted so callers
                migrated from the standalone service keep working).
            ocr_provider: Legacy optional OCR provider. When supplied,
                `run_extraction` may be called without a pre-computed OCR
                result and will run OCR itself.
        """
        if engine is not None and extraction_engine is not None:
            raise TypeError(
                "ExtractionService got both 'engine' and its alias "
                "'extraction_engine'; pass only one."
            )

        self.conf = settings.DOCUMENT_INTELLIGENCE
        self.engine = engine or extraction_engine or self._get_default_engine()
        self.ai_suggester = ai_suggester
        self.ocr_provider = ocr_provider

    @property
    def extraction_engine(self) -> ExtractionEngine:
        """Legacy alias for `engine`."""
        return self.engine

    def _get_default_engine(self) -> ExtractionEngine:
        """Get default extraction engine from settings (see the factory)."""
        return get_extraction_engine()

    def run_extraction(
        self,
        document: Document,
        ocr_result: OCRResult | None = None,
    ) -> DocumentExtraction:
        """Run structured extraction on OCR result.

        Always creates a NEW DocumentExtraction row with version+1.
        Never mutates a previous extraction (BR-DI-003, BR-DI-009).
        The result is a *proposal*: nothing is posted downstream (BR-DI-009).

        Args:
            document: Document to extract from
            ocr_result: OCR result to process. If None, the injected
                `ocr_provider` is used to produce one.

        Returns:
            DocumentExtraction with structured result
        """
        if ocr_result is None:
            if self.ocr_provider is None:
                raise ValueError(
                    "run_extraction requires an ocr_result or an injected "
                    "ocr_provider to produce one."
                )
            ocr_result = self.ocr_provider.extract(document=document)

        logger.info(
            "ExtractionService: running extraction on document %s (tenant=%s)",
            document.guid,
            document.tenant_id,
        )

        with transaction.atomic():
            # Get or create version counter
            version_counter, _ = ExtractionVersion.objects.select_for_update().get_or_create(
                document=document,
                defaults={"current_version": 0},
            )
            new_version = version_counter.next_version()

            # Create extraction row in OCR_IN_PROGRESS state
            extraction = DocumentExtraction.objects.create(
                document=document,
                version=new_version,
                ocr_provider=ocr_result["provider"],
                ocr_model_version=ocr_result["model_version"],
                extraction_model_version="",
                status=ExtractionStatus.OCR_IN_PROGRESS,
            )

        try:
            # Step 1: Structured extraction
            extraction.status = ExtractionStatus.EXTRACTION_IN_PROGRESS
            extraction.save(update_fields=["status"])

            extraction_result = self.engine.extract(
                ocr_result=ocr_result, document=document
            )

            # Step 2: AI suggestion (if enabled)
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

            # Step 3: Persist completed extraction
            extraction.extraction_result = extraction_result
            extraction.ai_suggestion = ai_suggestion
            extraction.confidence_score = confidence_score
            extraction.confidence_evidence = confidence_evidence
            extraction.status = ExtractionStatus.COMPLETED
            extraction.save()

            # Step 4: Route to review queue if low confidence (BR-DI-006)
            threshold = self.conf.get("AI_CONFIDENCE_THRESHOLD", 0.80)
            if confidence_score is not None and confidence_score < threshold:
                from ..models import ReviewQueue, ReviewStatus

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
                "ExtractionService: extraction %s v%s completed (conf=%s)",
                extraction.guid,
                new_version,
                confidence_score,
            )
            return extraction

        except Exception as e:
            logger.exception(
                "ExtractionService: extraction failed for document %s", document.guid
            )
            extraction.status = ExtractionStatus.EXTRACTION_FAILED
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

        Args:
            extraction: Extraction to correct
            correction: Correction payload
            reviewer_id: User ID of reviewer
            note: Optional correction note

        Returns:
            New DocumentExtraction with corrections
        """
        logger.info(
            "ExtractionService: applying human correction to extraction %s v%s",
            extraction.guid,
            extraction.version,
        )

        with transaction.atomic():
            # The version counter is normally created by run_extraction. A
            # correction can also be applied to an extraction that was created
            # outside that path (BR-DI-004 seeds a v1 row directly), so the
            # counter is recreated from the highest existing version. The new
            # row then still gets MAX(version) + 1 and never collides.
            latest_version = (
                DocumentExtraction.objects.filter(document=extraction.document)
                .order_by("-version")
                .values_list("version", flat=True)
                .first()
            ) or 0
            version_counter, _ = (
                ExtractionVersion.objects.select_for_update().get_or_create(
                    document=extraction.document,
                    defaults={"current_version": latest_version},
                )
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
            from ..models import ReviewQueue, ReviewStatus

            ReviewQueue.objects.filter(extraction=extraction).update(
                status=ReviewStatus.CORRECTED,
                decided_by=reviewer_id,
                decided_at=timezone.now(),
            )

            logger.info(
                "ExtractionService: human correction applied: extraction %s v%s -> v%s",
                extraction.guid,
                extraction.version,
                new_version,
            )
            return corrected_extraction
