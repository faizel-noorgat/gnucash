"""Review queue — documents / extractions awaiting human review.

BR-DI-006: AI suggestions below the configured confidence threshold
(`settings.DOCUMENT_INTELLIGENCE['AI_CONFIDENCE_THRESHOLD']`) MUST route to
the review queue and cannot be auto-applied.

Workflow:
1. ExtractionService creates ReviewQueue entry when confidence < threshold
2. Reviewer is assigned (or picks up from queue)
3. Reviewer makes decision: approve, correct, or reject
4. Decision is recorded in ReviewDecision (audit trail)
5. If approved/corrected, downstream posting can proceed
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class ReviewStatus(models.TextChoices):
    """Lifecycle of a review queue item."""

    OPEN = "open", "Open"
    ASSIGNED = "assigned", "Assigned to reviewer"
    APPROVED = "approved", "Approved by reviewer"
    CORRECTED = "corrected", "Corrected by reviewer (creates extraction v+1)"
    REJECTED = "rejected", "Rejected (no downstream action)"
    CANCELLED = "cancelled", "Cancelled (e.g. document deleted)"


class ReviewDecision(models.TextChoices):
    """The specific decision made by a reviewer."""

    APPROVE_AS_IS = "approve_as_is", "Approve extraction without changes"
    CORRECT_AND_APPROVE = "correct_and_approve", "Correct extraction then approve"
    REJECT_NO_ACTION = "reject_no_action", "Reject with no downstream action"
    REQUEST_MORE_INFO = "request_more_info", "Request additional information"
    ESCALATE = "escalate", "Escalate to senior reviewer"


class ReviewQueue(models.Model):
    """A work-item in the human-review queue.

    Created when:
    - AI confidence < threshold (BR-DI-006)
    - Duplicate detected (BR-DI-005)
    - Low-quality OCR
    - Missing required fields
    """

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
        help_text="Why this item needs review (e.g. 'low_confidence', 'duplicate').",
    )

    assigned_to = models.UUIDField(null=True, blank=True, db_index=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.UUIDField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "document_intelligence"
        db_table = "review_queue"
        ordering = ["-priority", "created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def assign(self, reviewer_id: uuid.UUID) -> None:
        """Assign this review item to a reviewer."""
        self.assigned_to = reviewer_id
        self.assigned_at = timezone.now()
        self.status = ReviewStatus.ASSIGNED
        self.save(update_fields=["assigned_to", "assigned_at", "status"])

    def approve(self, reviewer_id: uuid.UUID) -> None:
        """Approve this review item."""
        self.status = ReviewStatus.APPROVED
        self.decided_by = reviewer_id
        self.decided_at = timezone.now()
        self.save(update_fields=["status", "decided_by", "decided_at"])

    def reject(self, reviewer_id: uuid.UUID) -> None:
        """Reject this review item."""
        self.status = ReviewStatus.REJECTED
        self.decided_by = reviewer_id
        self.decided_at = timezone.now()
        self.save(update_fields=["status", "decided_by", "decided_at"])

    def __str__(self) -> str:
        return f"Review {self.guid} ({self.status})"


class ReviewDecisionLog(models.Model):
    """Audit trail for review decisions.

    Every decision made on a review queue item is logged here for compliance
    and audit purposes. This is append-only — decisions are never modified.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    review_item = models.ForeignKey(
        "document_intelligence.ReviewQueue",
        on_delete=models.CASCADE,
        related_name="decision_log",
    )

    decision = models.CharField(
        max_length=32,
        choices=ReviewDecision.choices,
        help_text="The specific decision made.",
    )
    decision_note = models.TextField(
        blank=True,
        help_text="Optional note explaining the decision.",
    )
    correction_data = models.JSONField(
        null=True,
        blank=True,
        help_text="If decision is CORRECT_AND_APPROVE, the correction payload.",
    )

    decided_by = models.UUIDField(db_index=True)
    decided_at = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "document_intelligence"
        db_table = "review_decision_log"
        ordering = ["-decided_at"]
        indexes = [
            models.Index(fields=["tenant_id", "decided_at"]),
            models.Index(fields=["review_item", "decision"]),
        ]

    def __str__(self) -> str:
        return f"Decision {self.guid} ({self.decision}) by {self.decided_by}"
