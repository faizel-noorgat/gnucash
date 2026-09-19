"""
Audit event model.

Immutable audit trail for all financial actions.

Accounting Semantics:
    The audit trail is a fundamental requirement for financial systems.
    Every financially significant action must be recorded in an immutable log.

    Audit events include:
    - Journal entry creation, posting, reversal, correction, voiding
    - Account creation, modification, deletion
    - Reconciliation status changes
    - Fiscal period closing, locking, reopening
    - Intercompany transaction proposals, acceptances, rejections
    - Document posting and reversal

    Immutability:
    Audit events are append-only. Once created, they cannot be modified or deleted.
    This ensures the integrity of the audit trail for compliance and forensics.

    Use Cases:
    - Regulatory compliance (SOX, GDPR, etc.)
    - Fraud detection and investigation
    - Troubleshooting and debugging
    - Historical analysis and reporting
"""

import uuid

from django.db import models
from django.utils import timezone


class AuditAction(models.TextChoices):
    """
    Types of auditable actions.

    Accounting Semantics:
        Each action represents a financially significant event that must be
        recorded in the audit trail for compliance and traceability.
    """

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

    Accounting Semantics:
        Every financially significant event is recorded here.
        This table is append-only - no updates or deletes allowed.

        The audit trail provides:
        - Who performed the action (actor)
        - What action was performed (action)
        - When it was performed (timestamp)
        - What entity was affected (entity_type, entity_id)
        - Additional context (metadata JSON)
        - Where it was performed from (ip_address, user_agent)

        Immutability:
        Once created, audit events cannot be modified or deleted.
        This is enforced at the application level (save/delete methods)
        and should also be enforced at the database level (triggers).

        Use Cases:
        - Regulatory compliance (SOX, GDPR, etc.)
        - Fraud detection and investigation
        - Troubleshooting and debugging
        - Historical analysis and reporting

    Attributes:
        guid: UUID primary key
        tenant: Multi-tenant isolation
        legal_entity: Legal entity context
        action: Type of action (AuditAction)
        actor: User who performed the action
        entity_type: Type of entity affected (e.g., "JournalEntry", "Account")
        entity_id: ID of the entity affected
        metadata: Additional context (JSON)
        timestamp: When the action occurred
        ip_address: IP address of the actor
        user_agent: User agent string of the actor's browser/client
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
        app_label = "accounting"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["tenant", "timestamp"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.entity_type}:{self.entity_id} at {self.timestamp}"

    def save(self, *args, **kwargs):
        """
        Prevent updates to audit events.

        Accounting Semantics:
            Audit events are immutable. Once created, they cannot be modified.
            This is enforced at the application level.
            Database-level triggers should also enforce this.

        Raises:
            ValueError: If attempting to update an existing audit event
        """
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValueError("Cannot update audit events - they are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Prevent deletion of audit events.

        Accounting Semantics:
            Audit events are immutable. They cannot be deleted.
            This is enforced at the application level.
            Database-level triggers should also enforce this.

        Raises:
            ValueError: Always raised when attempting to delete
        """
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
        """
        Create an audit event.

        Accounting Semantics:
            This is the primary method for creating audit events.
            It provides a convenient interface for logging financially
            significant actions.

        Args:
            tenant: Multi-tenant isolation
            legal_entity: Legal entity context
            action: Type of action (AuditAction)
            actor: User who performed the action (optional)
            entity_type: Type of entity affected (e.g., "JournalEntry")
            entity_id: ID of the entity affected
            metadata: Additional context (JSON dict)
            ip_address: IP address of the actor (optional)
            user_agent: User agent string (optional)

        Returns:
            Created AuditEvent instance
        """
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
