"""Document extraction models — append-only log of OCR/AI attempts.

Each time the OCR pipeline runs on a document, a NEW DocumentExtraction row
is created with an incremented version number. A previous extraction is
NEVER updated — it is kept for the audit trail (BR-DI-003, BR-DI-004, BR-DI-009).

Human corrections also produce a new version; they never mutate the row
that captured the AI output (BR-DI-004).
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db import models
from django.utils import timezone


class ExtractionStatus(models.TextChoices):
    """Lifecycle of a single extraction attempt."""

    QUEUED = "queued", "Queued for OCR"
    OCR_IN_PROGRESS = "ocr_in_progress", "OCR in progress"
    OCR_FAILED = "ocr_failed", "OCR failed"
    EXTRACTION_IN_PROGRESS = "extraction_in_progress", "Extraction in progress"
    EXTRACTION_FAILED = "extraction_failed", "Extraction failed"
    COMPLETED = "completed", "Completed (structured result)"
    REJECTED = "rejected", "Rejected during human review"


class ExtractionVersion(models.Model):
    """Monotonically increasing version counter per document.

    Exists so that DocumentExtraction.version can be validated against
    `MAX(version) + 1` at the database layer (defense-in-depth alongside
    the application-layer increment).
    """

    document = models.OneToOneField(
        "document_intelligence.Document",
        on_delete=models.CASCADE,
        related_name="version_counter",
    )
    current_version = models.IntegerField(default=0)

    class Meta:
        db_table = "document_extraction_versions"

    def next_version(self) -> int:
        self.current_version += 1
        self.save(update_fields=["current_version"])
        return self.current_version


class DocumentExtraction(models.Model):
    """Single OCR / AI extraction attempt on a document.

    Immutability contract (BR-DI-003 / BR-DI-009):
        Once a row exists, only the following fields may transition:
            - status: forward-only along the ExtractionStatus state machine
            - human_correction: set exactly once, when a reviewer corrects
              the extraction (still producing a *new* version, not mutating)
            - reviewed_by / reviewed_at: set exactly once
            - resulting_accounting_document_id: set exactly once
        All other fields (ocr_provider, ocr_model_version, extraction_result,
        ai_suggestion, confidence_score, confidence_evidence) are immutable
        after creation. Corrections must create a NEW row with version+1.
    """

    # --- Identity -----------------------------------------------------------
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "document_intelligence.Document",
        on_delete=models.CASCADE,
        related_name="extractions",
    )
    version = models.PositiveIntegerField(
        help_text="Strictly monotonic within a document."
    )

    # --- OCR provenance (BR-DI-008) -----------------------------------------
    ocr_provider = models.CharField(
        max_length=50,
        help_text="e.g. aws_textract, google_document_ai, mock",
    )
    ocr_model_version = models.CharField(max_length=100)
    extraction_model_version = models.CharField(max_length=100)

    # --- Structured result --------------------------------------------------
    extraction_result = models.JSONField(
        default=dict,
        help_text=(
            "Structured extraction output: supplier, customer, dates, amounts, "
            "line items, tax, invoice number, etc."
        ),
    )

    # --- AI suggestion (BR-DI-007 — explicit mapping, not LLM memory) -------
    accounting_mapping_used = models.ForeignKey(
        "document_intelligence.AccountingMapping",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extractions",
    )
    ai_suggestion = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "JSON object with suggested account/tax/dimension/party plus the "
            "evidence trail (which historical mapping, which exemplars)."
        ),
    )
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="0.0000 – 1.0000",
    )
    confidence_evidence = models.JSONField(
        null=True,
        blank=True,
        help_text="Provenance of the confidence score (exemplar IDs, weights).",
    )

    # --- Human review (BR-DI-004) -------------------------------------------
    # When a human corrects an extraction, we DO NOT mutate this row.
    # Instead, a NEW row is created with version+1 and `is_human_correction=True`.
    is_human_correction = models.BooleanField(default=False)
    human_correction = models.JSONField(
        null=True,
        blank=True,
        help_text="Optional structured corrections submitted by the reviewer.",
    )
    correction_note = models.TextField(blank=True)
    reviewed_by = models.UUIDField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # --- Status machine -----------------------------------------------------
    status = models.CharField(
        max_length=32,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.QUEUED,
        db_index=True,
    )

    # --- Downstream ---------------------------------------------------------
    resulting_accounting_document_id = models.UUIDField(null=True, blank=True)

    # --- Timestamps ---------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "document_extractions"
        ordering = ["document", "version"]
        constraints = [
            # Version is unique within a document (monotonic)
            models.UniqueConstraint(
                fields=["document", "version"],
                name="uniq_extraction_per_document_version",
            ),
        ]

    # --- Status state machine -----------------------------------------------
    ALLOWED_STATUS_TRANSITIONS = {
        ExtractionStatus.QUEUED: {
            ExtractionStatus.OCR_IN_PROGRESS,
            ExtractionStatus.OCR_FAILED,
        },
        ExtractionStatus.OCR_IN_PROGRESS: {
            ExtractionStatus.EXTRACTION_IN_PROGRESS,
            ExtractionStatus.OCR_FAILED,
        },
        ExtractionStatus.EXTRACTION_IN_PROGRESS: {
            ExtractionStatus.COMPLETED,
            ExtractionStatus.EXTRACTION_FAILED,
        },
        ExtractionStatus.OCR_FAILED: {ExtractionStatus.QUEUED},  # retry
        ExtractionStatus.EXTRACTION_FAILED: {ExtractionStatus.QUEUED},  # retry
        ExtractionStatus.COMPLETED: {
            ExtractionStatus.REJECTED,
        },
        ExtractionStatus.REJECTED: set(),
    }

    # --- Immutability fields ------------------------------------------------
    IMMUTABLE_FIELDS = frozenset(
        {
            "document",
            "version",
            "ocr_provider",
            "ocr_model_version",
            "extraction_model_version",
            "extraction_result",
            "ai_suggestion",
            "confidence_score",
            "confidence_evidence",
            "is_human_correction",
        }
    )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            try:
                existing = type(self).objects.get(pk=self.pk)
            except type(self).DoesNotExist:
                pass
            else:
                # Check status transition validity
                new_status = self.status
                old_status = existing.status
                if new_status != old_status:
                    allowed = self.ALLOWED_STATUS_TRANSITIONS.get(old_status, set())
                    if new_status not in allowed:
                        raise ValueError(
                            f"Invalid extraction status transition: "
                            f"{old_status} -> {new_status}"
                        )
                # Check immutability of other fields
                changed_immutable = [
                    field
                    for field in self.IMMUTABLE_FIELDS
                    if getattr(self, field) != getattr(existing, field)
                ]
                if changed_immutable:
                    raise ValueError(
                        f"BR-DI-003/009: cannot mutate immutable fields on "
                        f"DocumentExtraction {self.pk}: {changed_immutable}. "
                        f"Create a new version instead."
                    )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Extraction {self.guid} v{self.version} on {self.document_id}"
