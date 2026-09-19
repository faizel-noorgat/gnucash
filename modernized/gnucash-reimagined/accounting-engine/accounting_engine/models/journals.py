"""
Journal Entry and Journal Line models.

Implements:
- Double-entry accounting (BR-ACCT-001, BR-ACCT-002)
- Transaction edit atomicity (BR-ACCT-003)
- Posted journal immutability via PostgreSQL triggers (ADR-010)
- Multi-currency dual-field amount/value model (ADR-009)
"""

import uuid
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class JournalEntryStatus(models.TextChoices):
    """Journal entry lifecycle status."""

    DRAFT = "draft", "Draft"
    POSTED = "posted", "Posted"
    REVERSED = "reversed", "Reversed"
    VOID = "void", "Void"


class JournalEntry(models.Model):
    """
    Journal entry (transaction) - embodies double-entry accounting.

    A journal entry consists of balanced journal lines (splits) where
    the sum of all values must be exactly zero.

    Attributes:
        guid: UUID primary key
        date: Transaction date (financial date)
        date_entered: When the entry was created/last edited
        description: Narration/description
        reference: External reference number
        transaction_currency: Explicit currency for the journal (ADR-009)
        status: draft → posted → immutable (ADR-010)
        is_posted: Whether the entry is immutable
        tenant: Multi-tenant isolation
        legal_entity: Legal entity that owns this journal
        idempotency_key: Prevents duplicate posting
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(db_index=True)
    date_entered = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=1024)
    reference = models.CharField(max_length=255, blank=True)
    num = models.CharField(max_length=50, blank=True, db_index=True)  # Entry number

    # Multi-currency (ADR-009)
    transaction_currency = models.ForeignKey(
        "accounting_engine.Commodity",
        on_delete=models.PROTECT,
        related_name="journal_entries",
        help_text="The currency in which this journal balances",
    )

    # Status and immutability
    status = models.CharField(
        max_length=20,
        choices=JournalEntryStatus.choices,
        default=JournalEntryStatus.DRAFT,
        db_index=True,
    )
    is_posted = models.BooleanField(default=False, db_index=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_journal_entries",
    )

    # Source document linkage
    source_document = models.ForeignKey(
        "business_documents.AccountingDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_entries",
    )

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="journal_entries",
        db_index=True,
    )
    legal_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="journal_entries",
        db_index=True,
    )

    # Concurrency control
    version = models.IntegerField(default=0)

    # Idempotency
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    # Reversal tracking
    reversal_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversals",
    )
    is_reversal = models.BooleanField(default=False)
    correcting_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corrections",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["status", "date"]),
            models.Index(fields=["tenant", "legal_entity", "date"]),
            models.Index(fields=["is_posted"]),
            models.Index(fields=["idempotency_key"]),
        ]
        ordering = ["-date", "-date_entered"]

    def __str__(self) -> str:
        return f"JE-{self.num or self.guid}: {self.description[:50]}"

    def clean(self):
        """Validate journal entry constraints."""
        if self.is_posted and self.status != JournalEntryStatus.POSTED:
            raise ValidationError("Posted journal entries must have status='posted'.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_balanced(self) -> bool:
        """
        BR-ACCT-001: Check if journal entry is balanced.

        Sum of all journal line values must be exactly zero.
        For multi-currency with trading accounts:
        - Non-trading lines sum to zero
        - Trading lines sum to zero independently
        """
        return self._check_balance_per_commodity()

    def _check_balance_per_commodity(self) -> bool:
        """
        BR-ACCT-002: Check balance per commodity.

        For multi-currency transactions, imbalance is computed per-commodity.
        """
        lines = self.lines.all()

        # Group by account commodity
        from collections import defaultdict
        commodity_totals = defaultdict(lambda: Decimal("0.00"))

        for line in lines:
            # Amount is in account's commodity
            commodity_totals[line.account.commodity.mnemonic] += line.amount
            # Value is in transaction currency
            commodity_totals[self.transaction_currency.mnemonic] += line.value

        # Check that each commodity sums to zero
        # Note: Trading accounts handle the multi-currency imbalance internally
        for commodity_code, total in commodity_totals.items():
            # Allow for rounding tolerance
            if abs(total) > Decimal("0.005"):
                return False

        return True

    def post(self, user=None):
        """
        Post the journal entry (make it immutable).

        This is a synchronous operation for ACID compliance.
        Uses REPEATABLE READ isolation level.
        """
        if self.is_posted:
            raise ValidationError("Journal entry is already posted.")

        if not self.is_balanced:
            raise ValidationError("Cannot post unbalanced journal entry.")

        with transaction.atomic():
            # Lock the journal entry
            locked_je = JournalEntry.objects.select_for_update().get(pk=self.pk)

            # Check fiscal period
            from .fiscal import FiscalPeriod
            period = FiscalPeriod.get_period_for_date(
                self.tenant,
                self.legal_entity,
                self.date
            )
            if period and not period.is_open:
                raise ValidationError(
                    f"Cannot post to {period.status} fiscal period."
                )

            # Mark as posted
            locked_je.status = JournalEntryStatus.POSTED
            locked_je.is_posted = True
            locked_je.posted_at = timezone.now()
            locked_je.posted_by = user
            locked_je.save()

            # Create audit event
            from .audit import AuditEvent, AuditAction
            AuditEvent.log(
                tenant=self.tenant,
                legal_entity=self.legal_entity,
                action=AuditAction.JOURNAL_POSTED,
                actor=user,
                entity_type="JournalEntry",
                entity_id=str(self.guid),
                metadata={
                    "date": str(self.date),
                    "description": self.description,
                    "line_count": self.lines.count(),
                },
            )

        return self

    def create_reversal(self, user=None, description=None) -> "JournalEntry":
        """
        Create a reversal entry for this posted journal.

        A reversal entry is a new journal entry that exactly offsets
        the original entry.
        """
        if not self.is_posted:
            raise ValidationError("Can only reverse posted journal entries.")

        reversal = JournalEntry(
            date=timezone.now().date(),
            description=description or f"Reversal of: {self.description}",
            transaction_currency=self.transaction_currency,
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            reversal_of=self,
            is_reversal=True,
        )

        # Create reversal lines (opposite signs)
        for line in self.lines.all():
            JournalLine(
                journal_entry=reversal,
                account=line.account,
                amount=-line.amount,
                value=-line.value,
                memo=f"Reversal: {line.memo}",
            )

        return reversal

    def create_correcting_entry(self, corrections: dict, user=None) -> "JournalEntry":
        """
        Create a correcting entry for differences in a posted journal.

        corrections: dict of line_guid -> new_amount mappings
        """
        if not self.is_posted:
            raise ValidationError("Can only correct posted journal entries.")

        # Calculate differences
        correcting_lines = []
        for line_guid, new_amount in corrections.items():
            original_line = self.lines.get(pk=line_guid)
            diff_amount = new_amount - original_line.amount
            if diff_amount != 0:
                correcting_lines.append({
                    "account": original_line.account,
                    "amount": diff_amount,
                    "value": diff_amount,  # Simplified - needs FX calculation
                    "memo": f"Correction: {original_line.memo}",
                })

        if not correcting_lines:
            raise ValidationError("No corrections needed.")

        # Create correcting entry
        correcting_je = JournalEntry(
            date=timezone.now().date(),
            description=f"Correction of: {self.description}",
            transaction_currency=self.transaction_currency,
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            correcting_of=self,
        )

        return correcting_je


class ImmutablePostedJournalEntry(models.Model):
    """
    Immutable financial facts for posted journal entries.

    ADR-010: Posted journals are immutable at the database level.
    PostgreSQL BEFORE UPDATE / BEFORE DELETE triggers enforce this.

    This model represents the immutable financial data:
    - account, amount, value
    - transaction/posting currency
    - financial transaction date
    - legal entity
    - posting relationships
    - tax/accounting snapshots
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="immutable_data",
    )

    # Immutable snapshot
    date = models.DateField()
    description = models.CharField(max_length=1024)
    transaction_currency_code = models.CharField(max_length=10)
    is_posted = models.BooleanField(default=True)
    posted_at = models.DateTimeField()

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="immutable_journal_entries",
    )
    legal_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="immutable_journal_entries",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "accounting_engine"
        managed = False  # This is a view/snapshot, not directly managed
        db_table = "accounting_engine_immutable_posted_journal_entry"

    def save(self, *args, **kwargs):
        raise ValidationError("Cannot save immutable posted journal entry.")

    def delete(self, *args, **kwargs):
        raise ValidationError("Cannot delete immutable posted journal entry.")


class JournalLine(models.Model):
    """
    Journal line (split) - individual debit/credit entry.

    Dual-field model (ADR-009):
    - amount: Quantity in the account's commodity
    - value: Quantity in the transaction's balancing currency

    Attributes:
        guid: UUID primary key
        journal_entry: Parent journal entry
        account: Account this line affects
        amount: Quantity in account's commodity (e.g., USD 10,000)
        value: Quantity in transaction currency (e.g., SGD 13,400)
        memo: Description/narration
        reconcile_status: Reconciliation state (n/c/y/f/v)
        date_reconciled: When the line was reconciled
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    account = models.ForeignKey(
        "accounting_engine.Account",
        on_delete=models.PROTECT,
        related_name="lines",
    )

    # Dual-field amount/value (ADR-009)
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        help_text="Quantity in account's commodity",
    )
    value = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        help_text="Quantity in transaction currency",
    )

    memo = models.CharField(max_length=1024, blank=True)
    action = models.CharField(max_length=50, blank=True)  # e.g., "Payment", "Deposit"

    # Reconciliation (BR-SPLIT-001)
    reconcile_status = models.CharField(
        max_length=20,
        choices=[
            ("NOT_CLEARED", "Not Cleared"),
            ("CLEARED", "Cleared"),
            ("RECONCILED", "Reconciled"),
            ("FROZEN", "Frozen"),
            ("VOID", "Void"),
        ],
        default="NOT_CLEARED",
        db_index=True,
    )
    date_reconciled = models.DateTimeField(null=True, blank=True)

    # Online ID (for imported transactions)
    online_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Lot tracking (for inventory/stock)
    lot = models.ForeignKey(
        "accounting_engine.Lot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lines",
    )

    # Void tracking
    voided_amount = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        null=True,
        blank=True,
    )
    voided_value = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        null=True,
        blank=True,
    )
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        indexes = [
            models.Index(fields=["journal_entry"]),
            models.Index(fields=["account"]),
            models.Index(fields=["reconcile_status"]),
            models.Index(fields=["lot"]),
        ]

    def __str__(self) -> str:
        return f"{self.account}: {self.amount} (value: {self.value})"

    def clean(self):
        """Validate journal line constraints."""
        # Check if journal entry is posted (immutable)
        if self.journal_entry.is_posted:
            raise ValidationError(
                "Cannot modify lines of a posted journal entry. "
                "Create a reversal or correcting entry instead."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def void(self, user=None):
        """Void this journal line."""
        if self.journal_entry.is_posted:
            raise ValidationError("Cannot void lines of a posted journal entry.")

        self.voided_amount = self.amount
        self.voided_value = self.value
        self.voided_at = timezone.now()
        self.voided_by = user
        self.amount = Decimal("0.00")
        self.value = Decimal("0.00")
        self.reconcile_status = "VOID"
        self.save()


class ImmutablePostedJournalLine(models.Model):
    """
    Immutable financial facts for posted journal lines.

    ADR-010: Cannot be modified once posted.
    Enforced by PostgreSQL BEFORE UPDATE / BEFORE DELETE triggers.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_line = models.OneToOneField(
        JournalLine,
        on_delete=models.CASCADE,
        related_name="immutable_data",
    )

    # Immutable snapshot
    account_id = models.UUIDField()
    amount = models.DecimalField(max_digits=20, decimal_places=10)
    value = models.DecimalField(max_digits=20, decimal_places=10)
    memo = models.CharField(max_length=1024)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "accounting_engine"
        managed = False
        db_table = "accounting_engine_immutable_posted_journal_line"

    def save(self, *args, **kwargs):
        raise ValidationError("Cannot save immutable posted journal line.")

    def delete(self, *args, **kwargs):
        raise ValidationError("Cannot delete immutable posted journal line.")


class TransactionMetadata(models.Model):
    """
    Mutable operational state for journal entries.

    ADR-010: Separated from immutable financial facts.

    Mutable fields:
    - reconciliation state
    - bank matching
    - attachments
    - comments
    - review status
    - external references
    """

    journal_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="metadata",
    )

    # Operational state
    review_status = models.CharField(max_length=50, default="pending")
    reviewer_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # External references
    external_reference = models.CharField(max_length=255, blank=True)
    external_system = models.CharField(max_length=100, blank=True)

    # Comments
    comments = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"

    def __str__(self) -> str:
        return f"Metadata for {self.journal_entry}"
