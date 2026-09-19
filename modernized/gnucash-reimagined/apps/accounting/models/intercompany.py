"""
Intercompany models.

Minimal intercompany functionality per ADR-004.
Links two LegalEntities for inter-entity transactions.

Accounting Semantics:
    Intercompany transactions occur when two legal entities within the same
    organization transact with each other. For example:
    - Parent company provides services to subsidiary
    - Sister companies share expenses
    - One entity lends money to another

    Intercompany accounting requires:
    1. Recording the transaction in both entities' books
    2. Ensuring amounts match (elimination during consolidation)
    3. Tracking outstanding balances between entities

    Coordination Model:
    - IntercompanyRelationship: Links two entities for intercompany transactions
    - InterEntityEvent: Coordination object above entity journals
    - CounterpartPosting: Proposed posting in counterparty entity

    Mismatch Detection:
    When one entity records a transaction, the counterparty must record
    a matching transaction. Mismatches can occur in:
    - Amount (different values recorded)
    - Currency (different currencies used)
    - Classification (different account categories)
    - Date (different transaction dates)
"""

import uuid
from decimal import Decimal

from django.db import models


class IntercompanyRelationship(models.Model):
    """
    Links two legal entities for intercompany transactions.

    Accounting Semantics:
        An intercompany relationship defines which entities can transact
        with each other. This is used for:
        - Validating intercompany transactions
        - Generating intercompany reports
        - Consolidation elimination entries

        Relationship Types:
        - PARENT_SUBSIDIARY: Parent company and its subsidiary
        - SISTER_COMPANIES: Two entities with common parent
        - AFFILIATED: Entities with ownership interest but not control

    Attributes:
        guid: UUID primary key
        entity_a: First legal entity
        entity_b: Second legal entity
        relationship_type: Type of relationship
        is_active: Whether the relationship is active
        effective_from: When the relationship started
        effective_to: When the relationship ended (null = ongoing)
        tenant: Multi-tenant isolation
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
        app_label = "accounting"
        unique_together = ["entity_a", "entity_b", "tenant"]

    def __str__(self) -> str:
        return f"{self.entity_a} ↔ {self.entity_b}"

    def clean(self):
        """Validate that entity_a and entity_b are different."""
        from django.core.exceptions import ValidationError
        if self.entity_a == self.entity_b:
            raise ValidationError("Cannot create intercompany relationship with same entity.")


class InterEntityEvent(models.Model):
    """
    Coordination object above entity journals.

    Accounting Semantics:
        An inter-entity event links journal entries across legal entities
        for intercompany transactions. When one entity records a transaction,
        an InterEntityEvent is created to coordinate with the counterparty.

        Workflow:
        1. Source entity records transaction
        2. InterEntityEvent created with status=PROPOSED
        3. Counterparty entity reviews and accepts/rejects
        4. Counterparty records matching transaction
        5. Event status updated to ACCEPTED
        6. Mismatch detection ensures amounts match

        Status:
        - PROPOSED: Transaction proposed by source entity
        - ACCEPTED: Counterparty accepted and recorded matching entry
        - MODIFIED: Counterparty modified the amounts (requires reconciliation)
        - REJECTED: Counterparty rejected the transaction

        Mismatch Status:
        - MATCHED: Amounts match perfectly
        - AMOUNT_MISMATCH: Different amounts recorded
        - CURRENCY_MISMATCH: Different currencies used
        - CLASSIFICATION_MISMATCH: Different account categories
        - DATE_MISMATCH: Different transaction dates

    Attributes:
        guid: UUID primary key
        source_entity: Entity initiating the transaction
        counterparty_entity: Counterparty entity
        source_journal_entry: Journal entry in source entity
        counterpart_journal_entry: Journal entry in counterparty entity
        status: Event status (PROPOSED, ACCEPTED, MODIFIED, REJECTED)
        mismatch_status: Whether entries match
        source_amount: Amount recorded by source entity
        counterpart_amount: Amount recorded by counterparty entity
        currency: Transaction currency
        proposed_by: User who proposed the transaction
        accepted_by: User who accepted the transaction
        tenant: Multi-tenant isolation
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
        "accounting.JournalEntry",
        on_delete=models.CASCADE,
        related_name="source_events",
    )
    counterpart_journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
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
        "accounting.Commodity",
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
        app_label = "accounting"
        ordering = ["-proposed_at"]

    def __str__(self) -> str:
        return f"Intercompany Event: {self.source_entity} → {self.counterparty_entity}"

    def accept(self, user, counterpart_journal_entry=None):
        """
        Accept the intercompany event.

        Accounting Semantics:
            The counterparty entity accepts the proposed transaction
            and records a matching journal entry.

        Args:
            user: User accepting the event
            counterpart_journal_entry: Journal entry recorded by counterparty
        """
        self.status = "ACCEPTED"
        self.accepted_by = user
        from django.utils import timezone
        self.accepted_at = timezone.now()
        if counterpart_journal_entry:
            self.counterpart_journal_entry = counterpart_journal_entry
        self.save()

    def reject(self, user, reason=""):
        """
        Reject the intercompany event.

        Accounting Semantics:
            The counterparty entity rejects the proposed transaction.
            This may require the source entity to reverse their entry.

        Args:
            user: User rejecting the event
            reason: Reason for rejection
        """
        self.status = "REJECTED"
        self.accepted_by = user
        from django.utils import timezone
        self.accepted_at = timezone.now()
        self.save()

    def detect_mismatch(self):
        """
        Detect and record any mismatches between source and counterpart.

        Accounting Semantics:
            Compares the amounts recorded by source and counterparty entities.
            Mismatches must be resolved before consolidation.

            Mismatch Types:
            - AMOUNT_MISMATCH: Different amounts recorded
            - CURRENCY_MISMATCH: Different currencies used
            - CLASSIFICATION_MISMATCH: Different account categories
            - DATE_MISMATCH: Different transaction dates
        """
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

    Accounting Semantics:
        A counterpart posting represents the expected journal entry in the
        counterparty entity. This is used for:
        - Proposing transactions to counterparty
        - Tracking acceptance/rejection
        - Coordinating intercompany workflows

    Attributes:
        guid: UUID primary key
        inter_entity_event: Parent inter-entity event
        proposed_journal_entry: Proposed journal entry for counterparty
        accepted_by: User who accepted the posting
        accepted_at: When the posting was accepted
        status: PENDING, ACCEPTED, or REJECTED
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inter_entity_event = models.ForeignKey(
        InterEntityEvent,
        on_delete=models.CASCADE,
        related_name="counterpart_postings",
    )
    proposed_journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
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
        app_label = "accounting"

    def __str__(self) -> str:
        return f"Counterpart Posting for {self.inter_entity_event}"
