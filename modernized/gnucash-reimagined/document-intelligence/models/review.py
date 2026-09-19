"""Review queue — documents / extractions awaiting human review.

BR-DI-006: AI suggestions below the configured confidence threshold
(`settings.DOCUMENT_INTELLIGENCE['AI_CONFIDENCE_THRESHOLD']`) MUST route to
the review queue and cannot be auto-applied.
"""

from __future__ import annotations

import uuid

from django.db import models


class ReviewStatus(models.TextChoices):
    OPEN = "open", "Open"
    ASSIGNED = "assigned", "Assigned to reviewer"
    APPROVED = "approved", "Approved by reviewer"
    CORRECTED = "corrected", "Corrected by reviewer (creates extraction v+1)"
    REJECTED = "rejected", "Rejected (no downstream action)"
    CANCELLED = "cancelled", "Cancelled (e.g. document deleted)"


class ReviewQueue(models.Model):
    """A work-item in the human-review queue."""

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    document = models.ForeignKey(
        "document_intelligence.Document",
        on_delete=models.CASCADE,
        related_name="review_items",
    )
    extraction = models.ForeignKey(
        "document_intelligence.DocumentExtraction",
        on_delete=models.CASCADE,
        related_name="review_items",
    )
    suggestion = models.ForeignKey(
        "document_intelligence.MappingSuggestion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_items",
    )

    status = models.CharField(
        max_length=32,
        choices=ReviewStatus.choices,
        default=ReviewStatus.OPEN,
        db_index=True,
    )
    priority = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Higher = more urgent. Derived from confidence gap.",
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Why this item needs review (e.g. 'low_confidence').",
    )

    assigned_to = models.UUIDField(null=True, blank=True, db_index=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.UUIDField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "review_queue"
        ordering = ["-priority", "created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def __str__(self) -> str:
        return f"Review {self.guid} ({self.status})"
