"""Duplicate detection service — identifies likely duplicate documents.

BR-DI-005: Detect duplicates based on:
1. Content hash (exact byte-for-byte duplicate)
2. Supplier + invoice_number + amount + date window (semantic duplicate)

When a duplicate is detected, the document is flagged and linked to the
original. Downstream processing may reject it or route to review.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from ..models import Document

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """Detects duplicate documents."""

    def __init__(self) -> None:
        self.conf = settings.DOCUMENT_INTELLIGENCE

    def detect_and_mark(self, document: Document) -> bool:
        """Check if document is a duplicate and mark it.

        Returns True if duplicate detected, False otherwise.
        """
        # 1. Content-hash duplicate (exact byte-for-byte)
        content_hash_dup = self._check_content_hash_duplicate(document)
        if content_hash_dup:
            document.is_duplicate = True
            document.duplicate_of = content_hash_dup
            document.save(update_fields=["is_duplicate", "duplicate_of"])
            logger.info(
                "Document %s is content-hash duplicate of %s",
                document.guid,
                content_hash_dup.guid,
            )
            return True

        # 2. Semantic duplicate (supplier + invoice + amount + date)
        semantic_dup = self._check_semantic_duplicate(document)
        if semantic_dup:
            document.is_duplicate = True
            document.duplicate_of = semantic_dup
            document.save(update_fields=["is_duplicate", "duplicate_of"])
            logger.info(
                "Document %s is semantic duplicate of %s",
                document.guid,
                semantic_dup.guid,
            )
            return True

        return False

    def _check_content_hash_duplicate(self, document: Document) -> Document | None:
        """Check for exact content-hash duplicate within same tenant."""
        return (
            Document.objects.filter(
                tenant_id=document.tenant_id,
                content_hash=document.content_hash,
            )
            .exclude(pk=document.pk)
            .first()
        )

    def _check_semantic_duplicate(self, document: Document) -> Document | None:
        """Check for semantic duplicate based on extraction result.

        Requires the document to have been extracted first. If no extraction
        exists yet, returns None (will be re-checked after extraction).
        """
        # Get latest extraction
        extraction = document.extractions.order_by("-version").first()
        if not extraction or not extraction.extraction_result:
            return None

        result = extraction.extraction_result
        supplier_name = result.get("supplier_name")
        invoice_number = result.get("invoice_number")
        total_amount = result.get("total_amount")
        invoice_date = result.get("invoice_date")

        # Need at least supplier + invoice_number + amount
        if not (supplier_name and invoice_number and total_amount):
            return None

        # Date window (default 90 days)
        window_days = self.conf.get("DUPLICATE_INVOICE_WINDOW_DAYS", 90)
        date_cutoff = timezone.now() - timedelta(days=window_days)

        # Query for documents with same supplier + invoice + amount in date window
        # This requires joining to extractions, which is complex in Django ORM.
        # For now, we do a simple content-hash check and defer semantic dedup
        # to a post-extraction task.
        # TODO: implement semantic dedup after extraction pipeline

        return None
