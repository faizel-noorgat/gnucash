"""Document model — the central entity of the Document Intelligence context.

A Document represents an uploaded file (receipt, invoice, bill, statement,
contract, ...). Its original object-storage reference and SHA-256 content
hash are immutable from the moment of upload — any subsequent OCR/AI work
produces new DocumentExtraction rows rather than mutating the Document.

Implements behavior-contract rules:
- BR-DI-001: content hash is immutable after upload
- BR-DI-002: original object-storage file is immutable after upload
- BR-DI-008: provenance fields are complete
- BR-DI-010: tenant-scoped via RLS
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from django.db import models
from django.utils import timezone


class DocumentSource(models.TextChoices):
    """How the document entered the system."""

    WEB_UPLOAD = "web_upload", "Web upload (drag-drop)"
    EMAIL = "email", "Email inbound"
    API = "api", "External API"
    MOBILE = "mobile", "Mobile app"
    BANK_FEED = "bank_feed", "Bank statement feed"


class DocumentStatus(models.TextChoices):
    """High-level lifecycle status of a document."""

    UPLOADED = "uploaded", "Uploaded (awaiting extraction)"
    EXTRACTING = "extracting", "OCR/extraction in progress"
    EXTRACTED = "extracted", "Extraction complete (pending match)"
    MATCHING = "matching", "Matching in progress"
    MATCHED = "matched", "Matched to party / accounting document"
    IN_REVIEW = "in_review", "Awaiting human review"
    APPROVED = "approved", "Human-approved (ready for posting)"
    POSTED = "posted", "Downstream accounting document posted"
    REJECTED = "rejected", "Rejected during review"
    ARCHIVED = "archived", "Archived (no action pending)"


class Document(models.Model):
    """Uploaded document with full provenance.

    BR-DI-001 / BR-DI-002: Once an upload has been committed, `content_hash`
    and `original_file_key` must NEVER be overwritten. This is enforced by:
      1. Application-layer guard in Document.save() (raises if the fields
         change on an existing row).
      2. PostgreSQL BEFORE UPDATE trigger on the `documents` table (see
         triggers/immutability.sql) that rejects the UPDATE when is_posted=False
         but the column is one of the immutable set.
    """

    # --- Identity -----------------------------------------------------------
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- Multi-tenancy (BR-DI-010) -----------------------------------------
    # The actual tenant FK is provided by the shared identity-access schema;
    # we reference it by UUID to keep this bounded context decoupled at the
    # ORM layer while RLS enforces isolation at the database layer.
    tenant_id = models.UUIDField(db_index=True)
    legal_entity_id = models.UUIDField(db_index=True, null=True, blank=True)

    # --- Provenance (BR-DI-008) ---------------------------------------------
    original_file_key = models.CharField(
        max_length=512,
        help_text="S3 object key of the original uploaded file. IMMUTABLE.",
    )
    content_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 of the original uploaded file. IMMUTABLE.",
    )
    mime_type = models.CharField(max_length=128)
    original_filename = models.CharField(max_length=512)
    size_bytes = models.BigIntegerField()

    # --- Ingest metadata ----------------------------------------------------
    source = models.CharField(
        max_length=32,
        choices=DocumentSource.choices,
        default=DocumentSource.WEB_UPLOAD,
    )
    uploaded_at = models.DateTimeField(default=timezone.now, db_index=True)
    uploaded_by = models.UUIDField(null=True, blank=True)  # User.guid

    # --- Lifecycle ----------------------------------------------------------
    status = models.CharField(
        max_length=32,
        choices=DocumentStatus.choices,
        default=DocumentStatus.UPLOADED,
        db_index=True,
    )

    # --- Duplicate tracking -------------------------------------------------
    # Candidate duplicates (BR-DI-005) are detected on (content_hash, tenant)
    # and separately on (supplier + invoice_number + amount + date window).
    is_duplicate = models.BooleanField(default=False, db_index=True)
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicate_copies",
    )

    # --- Downstream linkage -------------------------------------------------
    # Populated when the approved extraction results in a posted accounting
    # document. Set only by the business-documents service via an event.
    resulting_accounting_document_id = models.UUIDField(null=True, blank=True)

    # --- Audit --------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "document_intelligence"
        db_table = "documents"
        ordering = ["-uploaded_at"]
        indexes = [
            # Supports BR-DI-005 (content-hash duplicate detection per tenant)
            models.Index(fields=["tenant_id", "content_hash"]),
            # Supports BR-DI-010 (RLS + query scoping)
            models.Index(fields=["tenant_id", "status"]),
        ]
        # Declarative marker: these columns are immutable once set.
        # The PostgreSQL trigger in triggers/immutability.sql enforces it.
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    # --- Immutability guards (BR-DI-001, BR-DI-002) -------------------------
    IMMUTABLE_FIELDS = frozenset(
        {
            "original_file_key",
            "content_hash",
            "mime_type",
            "original_filename",
            "size_bytes",
            "uploaded_at",
            "uploaded_by",
            "tenant_id",
        }
    )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            try:
                existing = type(self).objects.get(pk=self.pk)
            except type(self).DoesNotExist:
                pass
            else:
                changed_immutable = [
                    field
                    for field in self.IMMUTABLE_FIELDS
                    if getattr(self, field) != getattr(existing, field)
                ]
                if changed_immutable:
                    raise ValueError(
                        f"BR-DI-001/002: cannot mutate immutable fields on "
                        f"Document {self.pk}: {changed_immutable}"
                    )
        super().save(*args, **kwargs)

    # --- Helpers ------------------------------------------------------------
    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        """Compute SHA-256 hex digest of raw bytes.

        Pure function — no side effects, no database access. Used by the
        upload service to compute `content_hash` BEFORE persisting.
        """
        return hashlib.sha256(file_bytes).hexdigest()

    def __str__(self) -> str:
        return f"Document {self.guid} ({self.original_filename})"
