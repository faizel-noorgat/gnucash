"""
Journal Entry and Journal Line models.

Implements:
- Double-entry accounting (BR-ACCT-001, BR-ACCT-002)
- Transaction edit atomicity (BR-ACCT-003)
- Posted journal immutability via PostgreSQL triggers (ADR-010)
- Multi-currency dual-field amount/value model (ADR-009)

Accounting Semantics:
    The journal is the primary record of financial transactions.
    Every transaction must be balanced: sum of debits = sum of credits.

    Dual-Field Model (ADR-009):
    - amount: Quantity in the account's commodity (e.g., 10,000 USD)
    - value: Quantity in the transaction currency (e.g., 13,400 SGD)

    For example, if a USD-denominated account buys EUR stock:
    - Account commodity: USD
    - Transaction currency: EUR
    - amount: 10,000 (USD)
    - value: 8,500 (EUR equivalent)

    Immutability (ADR-010):
    Once a journal entry is posted, it becomes immutable financial fact.
    PostgreSQL BEFORE UPDATE / BEFORE DELETE triggers enforce this at the database level.
    To "correct" a posted entry, create a reversal or correcting entry instead.

    Posting Flow:
    1. Draft: Entry can be edited freely
    2. Posted: Entry becomes immutable (ADR-010)
    3. Reversed: A reversal entry offsets the original
    4. Void: Entry is effectively cancelled (via reversal)
"""

import uuid
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class JournalEntryStatus(models.TextChoices):
    """
    Journal entry lifecycle status.

    Accounting Semantics:
        DRAFT: Entry can be edited, not yet posted
        POSTED: Entry is immutable (ADR-010), cannot be modified
        REVERSED: Entry has been offset by a reversal entry
        VOID: Entry has been cancelled (via reversal)
    """

    DRAFT = "draft", "Draft"
    POSTED = "posted", "Posted"
    REVERSED = "reversed", "Reversed"
    VOID = "void", "Void"


class JournalEntry(models.Model):
    """
    Journal entry (transaction) - embodies double-entry accounting.

    Accounting Semantics:
        A journal entry consists of balanced journal lines (splits) where
        the sum of all values must be exactly zero.

        Multi-Currency (ADR-009):
        - transaction_currency: The currency in which the journal balances
        - Each line has amount (account commodity) and value (transaction currency)
        - Trading accounts handle cross-commodity imbalances

        Immutability (ADR-010):
        - Once posted, the entry cannot be modified
        - PostgreSQL BEFORE UPDATE / BEFORE DELETE triggers enforce this
        - To correct, create a reversal or correcting entry

    Attributes:
        guid: UUID primary key
        date: Transaction date (financial date)
        date_entered: When the entry was created/last edited
        description: Narration/description
        reference: External reference number
        num: Entry number (for display)
        transaction_currency: Explicit currency for the journal (ADR-009)
        status: draft → posted → immutable (ADR-010)
        is_posted: Whether the entry is immutable
        tenant: Multi-tenant isolation
        legal_entity: Legal entity that owns this journal
        idempotency_key: Prevents duplicate posting
        source_document: Linked business document (invoice, receipt, etc.)
        reversal_of: Original entry this reverses
        correcting_of: Original entry this corrects
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(db_index=True)
    date_entered = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=1024)
    reference = models.CharField(max_length=255, blank=True)
    num = models.CharField(max_length=50, blank=True, db_index=True)  # Entry number

    # Multi-currency (ADR-009)
    transaction_currency = models.ForeignKey(
        "accounting.Commodity",
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
        app_label = "accounting"
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
        """
        Validate journal entry constraints.

        BR-BUS-001: Posting is one-way. An entry that is already posted cannot
        be moved back to draft/unposted; correct it with a reversal or
        correcting entry instead.
        """
        if self.is_posted and self.status != JournalEntryStatus.POSTED:
            raise ValidationError("Posted journal entries must have status='posted'.")

        # BR-BUS-001: Posting is one-way. Detect the posted -> unposted/draft
        # transition by comparing against the persisted row. `_state.adding` is
        # used rather than `pk` because `guid` carries a default, so `pk` is
        # populated even for instances that were never saved.
        if not self._state.adding:
            was_posted = (
                JournalEntry.objects.filter(pk=self.pk)
                .values_list("is_posted", flat=True)
                .first()
            )
            if was_posted and (
                not self.is_posted or self.status == JournalEntryStatus.DRAFT
            ):
                raise ValidationError(
                    "Cannot un-post a posted journal entry. "
                    "Create a reversal or correcting entry instead."
                )

    def save(self, *args, **kwargs):
        """Save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_balanced(self) -> bool:
        """
        BR-ACCT-001: Check if journal entry is balanced.

        Accounting Semantics:
            Sum of all journal line values must be exactly zero.
            For multi-currency with trading accounts:
            - Non-trading lines sum to zero
            - Trading lines sum to zero independently

        Returns:
            True if balanced, False otherwise
        """
        return self._check_balance_per_commodity()

    def _check_balance_per_commodity(self) -> bool:
        """
        BR-ACCT-002: Check balance per commodity.

        Accounting Semantics:
            For multi-currency transactions, imbalance is computed per-commodity.
            Each commodity must sum to zero independently. Separately, the sum of
            all line `value` figures (which are always expressed in the
            transaction currency) must be zero.

        Returns:
            True if balanced per commodity, False otherwise

        Note:
            The two checks MUST use separate accumulators. An earlier version
            folded `amount` and `value` into one dict keyed by commodity, so a
            line whose account commodity equalled the transaction currency
            contributed twice to the same bucket. Two wrongs then cancelled:
            a single line with amount +100 and value -100, with no offsetting
            line at all, summed to zero and was reported balanced. Because
            `is_balanced` gates JournalEntry.post() and
            PostingService.post_journal_entry(), that allowed unbalanced
            entries to be posted.
        """
        from collections import defaultdict

        commodity_totals = defaultdict(lambda: Decimal("0.00"))
        value_total = Decimal("0.00")

        for line in self.lines.all():
            # `amount` is denominated in the line's OWN account commodity, so it
            # is bucketed per commodity.
            commodity_totals[line.account.commodity.mnemonic] += line.amount
            # `value` is denominated in the transaction currency, which every
            # line of this entry shares - so it is a single running total, not
            # a per-commodity bucket.
            value_total += line.value

        # Each commodity must net to zero on its own.
        for total in commodity_totals.values():
            # Allow for rounding tolerance (0.5 cents)
            if abs(total) > Decimal("0.005"):
                return False

        # ...and the transaction-currency values must net to zero.
        return abs(value_total) <= Decimal("0.005")

    def post(self, user=None):
        """
        Post the journal entry (make it immutable).

        ADR-010: Once posted, the entry cannot be modified.

        This is a synchronous operation for ACID compliance.
        Uses REPEATABLE READ isolation level.

        Steps:
        1. Lock the journal entry (pessimistic locking)
        2. Check fiscal period (must be open)
        3. Mark as posted
        4. Create audit event

        Args:
            user: User performing the post action

        Returns:
            self (the posted journal entry)

        Raises:
            ValidationError: If already posted, unbalanced, or fiscal period is closed
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

        Accounting Semantics:
            A reversal entry is a new journal entry that exactly offsets
            the original entry. All amounts are negated.

            Example:
            Original: Debit Cash $100, Credit Revenue $100
            Reversal: Debit Revenue $100, Credit Cash $100

        Args:
            user: User creating the reversal
            description: Optional description (defaults to "Reversal of: <original>")

        Returns:
            New JournalEntry (not yet posted)

        Raises:
            ValidationError: If original entry is not posted
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

        Accounting Semantics:
            A correcting entry adjusts specific lines in a posted journal
            without modifying the original. The difference is calculated
            and a new entry is created to correct it.

        Args:
            corrections: dict of line_guid -> new_amount mappings
            user: User creating the correction

        Returns:
            New JournalEntry (not yet posted)

        Raises:
            ValidationError: If original entry is not posted or no corrections needed
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

    Accounting Semantics:
        This model represents the immutable financial data:
        - account, amount, value
        - transaction/posting currency
        - financial transaction date
        - legal entity
        - posting relationships
        - tax/accounting snapshots

        Once created, these records cannot be modified or deleted.
        This ensures the integrity of the audit trail.

    Database Implementation:
        This is a view/snapshot (managed=False), not directly managed by Django.
        PostgreSQL triggers prevent any UPDATE or DELETE operations.
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
        app_label = "accounting"
        managed = False  # This is a view/snapshot, not directly managed
        db_table = "accounting_immutable_posted_journal_entry"

    def save(self, *args, **kwargs):
        """Prevent saving - this model is immutable."""
        raise ValidationError("Cannot save immutable posted journal entry.")

    def delete(self, *args, **kwargs):
        """Prevent deletion - this model is immutable."""
        raise ValidationError("Cannot delete immutable posted journal entry.")


class JournalLine(models.Model):
    """
    Journal line (split) - individual debit/credit entry.

    Dual-field model (ADR-009):
    - amount: Quantity in the account's commodity
    - value: Quantity in the transaction's balancing currency

    Accounting Semantics:
        Each journal line represents one side of a double-entry transaction.
        The `amount` field is in the account's commodity (e.g., USD 10,000).
        The `value` field is in the transaction currency (e.g., SGD 13,400).

        For single-currency transactions: amount == value
        For multi-currency transactions: amount != value (exchange rate applied)

        Reconciliation States (BR-SPLIT-001):
        - NOT_CLEARED (n): Not yet cleared by bank
        - CLEARED (c): Cleared by bank but not reconciled
        - RECONCILED (y): Fully reconciled with bank statement
        - FROZEN (f): Frozen (permanent, cannot be changed)
        - VOID (v): Voided (effectively cancelled)

        Lot Tracking:
        For inventory/securities, lines can be linked to a Lot for tracking
        specific batches of goods or securities.

    Attributes:
        guid: UUID primary key
        journal_entry: Parent journal entry
        account: Account this line affects
        amount: Quantity in account's commodity (e.g., USD 10,000)
        value: Quantity in transaction currency (e.g., SGD 13,400)
        memo: Description/narration
        reconcile_status: Reconciliation state (n/c/y/f/v)
        date_reconciled: When the line was reconciled
        lot: Lot tracking for inventory/securities
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    account = models.ForeignKey(
        "accounting.Account",
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
        "accounting.Lot",
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
        app_label = "accounting"
        indexes = [
            models.Index(fields=["journal_entry"]),
            models.Index(fields=["account"]),
            models.Index(fields=["reconcile_status"]),
            models.Index(fields=["lot"]),
        ]

    def __str__(self) -> str:
        return f"{self.account}: {self.amount} (value: {self.value})"

    def clean(self):
        """
        Validate journal line constraints.

        ADR-010: Cannot modify lines of a posted journal entry.
        To correct, create a reversal or correcting entry instead.
        """
        # Check if journal entry is posted (immutable)
        if self.journal_entry.is_posted:
            raise ValidationError(
                "Cannot modify lines of a posted journal entry. "
                "Create a reversal or correcting entry instead."
            )

    def save(self, *args, **kwargs):
        """Save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def void(self, user=None):
        """
        Void this journal line.

        Accounting Semantics:
            Voiding sets the amount and value to zero while preserving
            the original values for audit purposes. This is different
            from deletion - the voided line remains in the audit trail.

        Args:
            user: User performing the void action

        Raises:
            ValidationError: If journal entry is already posted
        """
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

    Accounting Semantics:
        This model stores the immutable snapshot of journal line data:
        - account, amount, value
        - memo
        - posting timestamp

        Once created, these records cannot be modified or deleted.
        This ensures the integrity of the audit trail.

    Database Implementation:
        This is a view/snapshot (managed=False), not directly managed by Django.
        PostgreSQL triggers prevent any UPDATE or DELETE operations.
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
        app_label = "accounting"
        managed = False
        db_table = "accounting_immutable_posted_journal_line"

    def save(self, *args, **kwargs):
        """Prevent saving - this model is immutable."""
        raise ValidationError("Cannot save immutable posted journal line.")

    def delete(self, *args, **kwargs):
        """Prevent deletion - this model is immutable."""
        raise ValidationError("Cannot delete immutable posted journal line.")


class TransactionMetadata(models.Model):
    """
    Mutable operational state for journal entries.

    ADR-010: Separated from immutable financial facts.

    Accounting Semantics:
        This model stores mutable operational data that is separate from
        the immutable financial facts:
        - reconciliation state (can change as reconciliation progresses)
        - bank matching (can be updated as matches are found)
        - attachments (can be added/removed)
        - comments (can be updated)
        - review status (can change during approval workflow)
        - external references (can be updated as external systems change)

        This separation allows operational workflows to proceed without
        violating the immutability of the financial facts.
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
        app_label = "accounting"

    def __str__(self) -> str:
        return f"Metadata for {self.journal_entry}"
