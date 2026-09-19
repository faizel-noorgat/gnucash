"""
Audit event model.

Immutable audit trail for all financial actions.
"""

import uuid

from django.db import models
from django.utils import timezone


class AuditAction(models.TextChoices):
    """Types of auditable actions."""

    # Journal actions
    JOURNAL_CREATED = "JOURNAL_CREATED", "Journal Entry Created"
    JOURNAL_POSTED = "JOURNAL_POSTED", "Journal Entry Posted"
    JOURNAL_REVERSED = "JOURNAL_REVERSED", "Journal Entry Reversed"
    JOURNAL_CORRECTED = "JOURNAL_CORRECTED", "Journal Entry Corrected"
    JOURNAL_VOIDED = "JOURNAL_VOIDED", "Journal Entry Voided"

    # Account actions
    ACCOUNT_CREATED = "ACCOUNT_CREATED", "Account Created"
    ACCOUNT_MODIFIED = "ACCOUNT_MODIFIED", "Account Modified"
    ACCOUNT_DELETED = "ACCOUNT_DELETED", "Account Deleted"

    # Reconciliation actions
    RECONCILE_STATUS_CHANGED = "RECONCILE_STATUS_CHANGED", "Reconciliation Status Changed"
    RECONCILIATION_STARTED = "RECONCILIATION_STARTED", "Bank Reconciliation Started"
    RECONCILIATION_COMPLETED = "RECONCILIATION_COMPLETED", "Bank Reconciliation Completed"

    # Period actions
    PERIOD_CLOSED = "PERIOD_CLOSED", "Fiscal Period Closed"
    PERIOD_LOCKED = "PERIOD_LOCKED", "Fiscal Period Locked"
    PERIOD_REOPENED = "PERIOD_REOPENED", "Fiscal Period Reopened"

    # Intercompany actions
    INTERCOMPANY_PROPOSED = "INTERCOMPANY_PROPOSED", "Intercompany Event Proposed"
    INTERCOMPANY_ACCEPTED = "INTERCOMPANY_ACCEPTED", "Intercompany Event Accepted"
    INTERCOMPANY_REJECTED = "INTERCOMPANY_REJECTED", "Intercompany Event Rejected"

    # Document actions
    DOCUMENT_POSTED = "DOCUMENT_POSTED", "Document Posted"
    DOCUMENT_REVERSED = "DOCUMENT_REVERSED", "Document Reversed"


class AuditEvent(models.Model):
    """
    Immutable audit trail for all financial actions.

    Every financially significant event is recorded here.
    This table is append-only - no updates or deletes allowed.

    Attributes:
        guid: UUID primary key
        tenant: Multi-tenant isolation
        legal_entity: Legal entity context
        action: Type of action
        actor: User who performed the action
        entity_type: Type of entity affected
        entity_id: ID of the entity affected
        metadata: Additional context (JSON)
        timestamp: When the action occurred
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="audit_events",
        db_index=True,
    )
    legal_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="audit_events",
        db_index=True,
    )

    action = models.CharField(
        max_length=50,
        choices=AuditAction.choices,
        db_index=True,
    )
    actor = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )

    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.CharField(max_length=255, db_index=True)

    metadata = models.JSONField(default=dict)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        app_label = "accounting_engine"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["tenant", "timestamp"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.entity_type}:{self.entity_id} at {self.timestamp}"

    def save(self, *args, **kwargs):
        """Prevent updates to audit events."""
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValueError("Cannot update audit events - they are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of audit events."""
        raise ValueError("Cannot delete audit events - they are immutable.")

    @classmethod
    def log(
        cls,
        tenant,
        legal_entity,
        action: str,
        actor=None,
        entity_type: str = "",
        entity_id: str = "",
        metadata: dict = None,
        ip_address: str = None,
        user_agent: str = None,
    ) -> "AuditEvent":
        """Create an audit event."""
        return cls.objects.create(
            tenant=tenant,
            legal_entity=legal_entity,
            action=action,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent or "",
        )
