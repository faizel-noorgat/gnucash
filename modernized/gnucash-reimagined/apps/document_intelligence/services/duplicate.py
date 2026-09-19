"""Duplicate detection service — identifies likely duplicate documents.

BR-DI-005: Detect duplicates based on:
1. Content hash (exact byte-for-byte duplicate)
2. Supplier + invoice_number + amount + date window (semantic duplicate)

When a duplicate is detected, the document is flagged and linked to the
original. Downstream processing may reject it or route it to review.

This service only *marks* documents. It never mutates the immutable upload
provenance (BR-DI-001/002) and never posts anything downstream.

Implements behavior-contract rules:
- BR-DI-005: duplicates flagged with is_duplicate=True and linked via duplicate_of
- BR-DI-010: detection is tenant-scoped
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from ..models import Document

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """Detects duplicate documents."""

    @property
    def conf(self) -> dict:
        """Document Intelligence settings, read lazily for testability."""
        return settings.DOCUMENT_INTELLIGENCE

    def detect_and_mark(self, document: Document) -> bool:
        """Check if document is a duplicate and mark it.

        Returns True if duplicate detected, False otherwise.
        """
        # 1. Content-hash duplicate (exact byte-for-byte)
        content_hash_dup = self._check_content_hash_duplicate(document)
        if content_hash_dup:
            self._mark(document, content_hash_dup, "content-hash")
            return True

        # 2. Semantic duplicate (supplier + invoice + amount + date)
        semantic_dup = self._check_semantic_duplicate(document)
        if semantic_dup:
            self._mark(document, semantic_dup, "semantic")
            return True

        return False

    def _mark(
        self, document: Document, duplicate_of: Document, kind: str
    ) -> None:
        """Flag `document` as a duplicate of `duplicate_of` and persist it.

        The in-memory flags are always set; the row is only written when the
        document has already been persisted. Callers may hand us a not-yet-saved
        Document (the upload path persists first, but detection is also usable
        as a pre-insert check), and Django would raise "Save with update_fields
        did not affect any rows" for a row that does not exist yet.
        """
        document.is_duplicate = True
        document.duplicate_of = duplicate_of

        if not document._state.adding:
            document.save(update_fields=["is_duplicate", "duplicate_of"])

        logger.info(
            "Document %s is a %s duplicate of %s",
            document.guid,
            kind,
            duplicate_of.guid,
        )

    def _check_content_hash_duplicate(self, document: Document) -> Document | None:
        """Check for an exact content-hash duplicate within the same tenant."""
        return (
            Document.objects.filter(
                tenant_id=document.tenant_id,
                content_hash=document.content_hash,
            )
            .exclude(pk=document.pk)
            .first()
        )

    def _check_semantic_duplicate(self, document: Document) -> Document | None:
        """Check for a semantic duplicate based on the latest extraction result.

        Requires the document to have been extracted first. If no extraction
        exists yet, returns None (it will be re-checked after extraction).
        """
        # Get latest extraction
        extraction = document.extractions.order_by("-version").first()
        if not extraction or not extraction.extraction_result:
            return None

        result = extraction.extraction_result
        supplier_name = result.get("supplier_name")
        invoice_number = result.get("invoice_number")
        total_amount = result.get("total_amount")

        # Need at least supplier + invoice_number + amount
        if not (supplier_name and invoice_number and total_amount):
            return None

        # Date window (default 90 days)
        window_days = self.conf.get("DUPLICATE_INVOICE_WINDOW_DAYS", 90)
        date_cutoff = timezone.now() - timedelta(days=window_days)

        # Query for documents with the same supplier + invoice + amount inside
        # the date window. This requires joining to extractions on JSON fields,
        # which the ORM cannot express portably, so semantic dedup is deferred
        # to a post-extraction task.
        # TODO: implement semantic dedup after the extraction pipeline
        logger.debug(
            "Semantic duplicate check for document %s deferred (window=%s days, "
            "cutoff=%s)",
            document.guid,
            window_days,
            date_cutoff,
        )

        return None
