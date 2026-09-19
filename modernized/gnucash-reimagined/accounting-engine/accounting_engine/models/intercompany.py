"""
Intercompany models.

Minimal intercompany functionality per ADR-004.
Links two LegalEntities for inter-entity transactions.
"""

import uuid
from decimal import Decimal

from django.db import models


class IntercompanyRelationship(models.Model):
    """
    Links two legal entities for intercompany transactions.

    Attributes:
        guid: UUID primary key
        entity_a: First legal entity
        entity_b: Second legal entity
        relationship_type: Type of relationship
        is_active: Whether the relationship is active
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_a = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="intercompany_relationships_a",
    )
    entity_b = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="intercompany_relationships_b",
    )
    relationship_type = models.CharField(
        max_length=50,
        choices=[
            ("PARENT_SUBSIDIARY", "Parent-Subsidiary"),
            ("SISTER_COMPANIES", "Sister Companies"),
            ("AFFILIATED", "Affiliated"),
        ],
    )
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="intercompany_relationships",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        unique_together = ["entity_a", "entity_b", "tenant"]

    def __str__(self) -> str:
        return f"{self.entity_a} ↔ {self.entity_b}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.entity_a == self.entity_b:
            raise ValidationError("Cannot create intercompany relationship with same entity.")


class InterEntityEvent(models.Model):
    """
    Coordination object above entity journals.

    Links journal entries across legal entities for intercompany transactions.

    Attributes:
        guid: UUID primary key
        source_entity: Entity initiating the transaction
        counterparty_entity: Counterparty entity
        source_journal_entry: Journal entry in source entity
        counterpart_journal_entry: Journal entry in counterparty entity
        status: Event status (proposed, accepted, modified, rejected)
        mismatch_status: Whether entries match
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="source_events",
    )
    counterparty_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="counterparty_events",
    )
    source_journal_entry = models.ForeignKey(
        "accounting_engine.JournalEntry",
        on_delete=models.CASCADE,
        related_name="source_events",
    )
    counterpart_journal_entry = models.ForeignKey(
        "accounting_engine.JournalEntry",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="counterpart_events",
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("PROPOSED", "Proposed"),
            ("ACCEPTED", "Accepted"),
            ("MODIFIED", "Modified"),
            ("REJECTED", "Rejected"),
        ],
        default="PROPOSED",
        db_index=True,
    )
    mismatch_status = models.CharField(
        max_length=30,
        choices=[
            ("MATCHED", "Matched"),
            ("AMOUNT_MISMATCH", "Amount Mismatch"),
            ("CURRENCY_MISMATCH", "Currency Mismatch"),
            ("CLASSIFICATION_MISMATCH", "Classification Mismatch"),
            ("DATE_MISMATCH", "Date Mismatch"),
        ],
        default="MATCHED",
    )

    # Amounts for comparison
    source_amount = models.DecimalField(max_digits=20, decimal_places=10)
    counterpart_amount = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        null=True,
        blank=True,
    )
    currency = models.ForeignKey(
        "accounting_engine.Commodity",
        on_delete=models.PROTECT,
        related_name="intercompany_events",
    )

    # Approval
    proposed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposed_intercompany_events",
    )
    accepted_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_intercompany_events",
    )
    proposed_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="intercompany_events",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        ordering = ["-proposed_at"]

    def __str__(self) -> str:
        return f"Intercompany Event: {self.source_entity} → {self.counterparty_entity}"

    def accept(self, user, counterpart_journal_entry=None):
        """Accept the intercompany event."""
        self.status = "ACCEPTED"
        self.accepted_by = user
        from django.utils import timezone
        self.accepted_at = timezone.now()
        if counterpart_journal_entry:
            self.counterpart_journal_entry = counterpart_journal_entry
        self.save()

    def reject(self, user, reason=""):
        """Reject the intercompany event."""
        self.status = "REJECTED"
        self.accepted_by = user
        from django.utils import timezone
        self.accepted_at = timezone.now()
        self.save()

    def detect_mismatch(self):
        """Detect and record any mismatches between source and counterpart."""
        if not self.counterpart_journal_entry:
            return

        # Compare amounts
        counterpart_total = sum(
            abs(line.amount) for line in self.counterpart_journal_entry.lines.all()
        )

        if self.source_amount != counterpart_total:
            self.mismatch_status = "AMOUNT_MISMATCH"
        else:
            self.mismatch_status = "MATCHED"

        self.save()


class CounterpartPosting(models.Model):
    """
    Proposed posting in counterparty entity.

    Represents the expected journal entry in the counterparty entity.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inter_entity_event = models.ForeignKey(
        InterEntityEvent,
        on_delete=models.CASCADE,
        related_name="counterpart_postings",
    )
    proposed_journal_entry = models.ForeignKey(
        "accounting_engine.JournalEntry",
        on_delete=models.CASCADE,
        related_name="counterpart_postings",
    )
    accepted_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("ACCEPTED", "Accepted"),
            ("REJECTED", "Rejected"),
        ],
        default="PENDING",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "accounting_engine"

    def __str__(self) -> str:
        return f"Counterpart Posting for {self.inter_entity_event}"
