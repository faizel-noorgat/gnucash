"""
Reconciliation models.

Implements:
- BR-SPLIT-001: Split reconciliation states (n/c/y/f/v)
- BR-SPLIT-004: Reconciled balance only includes reconciled splits
- Explicit state machine with ALLOWED_TRANSITIONS matrix (ADR-010)
- ReconciliationAuditLog for compliance-grade traceability
"""

import uuid
from typing import Optional

from django.db import models
from django.utils import timezone


class ReconcileStatus(models.TextChoices):
    """
    Reconciliation status states.

    BR-SPLIT-001: Valid reconciliation states
    - NOT_CLEARED (n): Not yet cleared
    - CLEARED (c): Cleared but not reconciled
    - RECONCILED (y): Fully reconciled
    - FROZEN (f): Frozen (permanent)
    - VOID (v): Voided

    Explicit state machine with allowed transitions.
    """

    NOT_CLEARED = "NOT_CLEARED", "Not Cleared"
    CLEARED = "CLEARED", "Cleared"
    RECONCILED = "RECONCILED", "Reconciled"
    FROZEN = "FROZEN", "Frozen"
    VOID = "VOID", "Void"

    @classmethod
    def get_allowed_transitions(cls, current_status: str) -> set[str]:
        """
        Get allowed next states for a given status.

        Explicit ALLOWED_TRANSITIONS matrix enforced at model layer (ADR-010).
        """
        transitions = {
            cls.NOT_CLEARED: {cls.CLEARED, cls.VOID},
            cls.CLEARED: {cls.NOT_CLEARED, cls.RECONCILED, cls.VOID},
            cls.RECONCILED: {cls.CLEARED, cls.FROZEN, cls.VOID},
            cls.FROZEN: set(),  # Frozen is final - no transitions allowed
            cls.VOID: {cls.NOT_CLEARED},  # Can un-void
        }
        return transitions.get(current_status, set())

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if transition from one status to another is allowed."""
        return to_status in cls.get_allowed_transitions(from_status)


class ReconciliationAuditLog(models.Model):
    """
    Compliance-grade audit log for reconciliation state changes.

    Every state transition is recorded with actor, timestamp, and reason.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_line = models.ForeignKey(
        "accounting_engine.JournalLine",
        on_delete=models.CASCADE,
        related_name="reconciliation_audit_log",
    )

    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    changed_at = models.DateTimeField(default=timezone.now)
    reason = models.TextField(blank=True)

    # Reconciliation run reference
    reconciliation_run = models.ForeignKey(
        "accounting_engine.BankReconciliation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_log_entries",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "accounting_engine"
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["journal_line", "changed_at"]),
            models.Index(fields=["changed_by"]),
        ]

    def __str__(self) -> str:
        return f"{self.journal_line}: {self.old_status} → {self.new_status}"
