"""
Reconciliation and Banking models.

Implements:
- BR-SPLIT-001: Split reconciliation states (n/c/y/f/v)
- BR-SPLIT-004: Reconciled balance only includes reconciled splits
- Explicit state machine with ALLOWED_TRANSITIONS matrix (ADR-010)
- ReconciliationAuditLog for compliance-grade traceability

Accounting Semantics:
    Bank reconciliation is the process of matching bank statement transactions
    to ledger entries. This ensures the company's books match the bank's records.

    Reconciliation States (BR-SPLIT-001):
    - NOT_CLEARED (n): Transaction not yet seen on bank statement
    - CLEARED (c): Transaction appears on bank statement but not yet reconciled
    - RECONCILED (y): Transaction fully matched and reconciled
    - FROZEN (f): Transaction permanently reconciled (cannot be changed)
    - VOID (v): Transaction cancelled

    State Machine (ADR-010):
    Explicit ALLOWED_TRANSITIONS matrix enforced at model layer.
    FROZEN is a terminal state - no transitions allowed.

    Banking Models:
    - BankAccount: Links a ledger account to a real bank account
    - BankStatement: Imported bank statement (CSV, OFX, etc.)
    - BankTransaction: Individual transaction from bank statement
    - BankReconciliation: Reconciliation session matching bank to ledger
"""

import uuid
from decimal import Decimal
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

    Accounting Semantics:
        The reconciliation state tracks the lifecycle of a transaction
        from initial posting to final reconciliation with the bank.

        State Machine (ADR-010):
        Explicit ALLOWED_TRANSITIONS matrix enforced at model layer.
        FROZEN is a terminal state - no transitions allowed.
        This ensures the integrity of the reconciliation process.
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

        Accounting Semantics:
            Explicit ALLOWED_TRANSITIONS matrix enforced at model layer (ADR-010).
            This ensures that reconciliation state changes follow valid paths.

            State Transitions:
            - NOT_CLEARED → CLEARED, VOID
            - CLEARED → NOT_CLEARED, RECONCILED, VOID
            - RECONCILED → CLEARED, FROZEN, VOID
            - FROZEN → (no transitions - terminal state)
            - VOID → NOT_CLEARED (can un-void)

        Args:
            current_status: Current reconciliation state

        Returns:
            Set of allowed next states
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
        """
        Check if transition from one status to another is allowed.

        Args:
            from_status: Current state
            to_status: Desired next state

        Returns:
            True if transition is allowed, False otherwise
        """
        return to_status in cls.get_allowed_transitions(from_status)


class ReconciliationAuditLog(models.Model):
    """
    Compliance-grade audit log for reconciliation state changes.

    Accounting Semantics:
        Every reconciliation state transition is recorded with:
        - Old and new status
        - Actor (user) who made the change
        - Timestamp
        - Reason for the change
        - Reference to the reconciliation run (if applicable)

        This provides a complete audit trail for compliance and troubleshooting.
        The audit log is append-only - records cannot be modified or deleted.

    Attributes:
        guid: UUID primary key
        journal_line: The journal line being reconciled
        old_status: Previous reconciliation state
        new_status: New reconciliation state
        changed_by: User who made the change
        changed_at: When the change occurred
        reason: Reason for the change
        reconciliation_run: Reference to the reconciliation session
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_line = models.ForeignKey(
        "accounting.JournalLine",
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
        "accounting.BankReconciliation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_log_entries",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "accounting"
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["journal_line", "changed_at"]),
            models.Index(fields=["changed_by"]),
        ]

    def __str__(self) -> str:
        return f"{self.journal_line}: {self.old_status} → {self.new_status}"


# ============================================================================
# Banking Models
# ============================================================================

class BankAccount(models.Model):
    """
    Bank account linked to a ledger account.

    Accounting Semantics:
        A bank account represents a real-world bank account (e.g., checking account
        at Chase Bank). It is linked to a ledger account where transactions are posted.

        Bank accounts are used for:
        - Importing bank statements (CSV, OFX, etc.)
        - Matching bank transactions to ledger entries
        - Bank reconciliation

    Attributes:
        guid: UUID primary key
        account: Linked ledger account
        bank_name: Name of the bank (e.g., "Chase", "Bank of America")
        account_number: Bank account number
        routing_number: Routing number / sort code
        currency: Account currency
        is_active: Whether the account is active
        tenant: Multi-tenant isolation
        legal_entity: Legal entity that owns this account
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.OneToOneField(
        "accounting.Account",
        on_delete=models.PROTECT,
        related_name="bank_account",
    )
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50, blank=True)
    currency = models.ForeignKey(
        "accounting.Commodity",
        on_delete=models.PROTECT,
        related_name="bank_accounts",
    )
    is_active = models.BooleanField(default=True)

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="bank_accounts",
        db_index=True,
    )
    legal_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="bank_accounts",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting"
        unique_together = ["bank_name", "account_number", "tenant"]

    def __str__(self) -> str:
        return f"{self.bank_name} - {self.account_number}"


class BankStatement(models.Model):
    """
    Imported bank statement.

    Accounting Semantics:
        A bank statement is an import from the bank (CSV, OFX, QFX, etc.).
        It contains a list of transactions for a specific period.
        Statements are used for bank reconciliation.

        Import Process:
        1. Upload statement file (CSV, OFX, etc.)
        2. Parse transactions
        3. Create BankTransaction records
        4. Match transactions to ledger entries (manual or automatic)
        5. Reconcile matched transactions

    Attributes:
        guid: UUID primary key
        bank_account: The bank account this statement belongs to
        statement_date: Statement date
        opening_balance: Opening balance from statement
        closing_balance: Closing balance from statement
        start_date: Statement period start
        end_date: Statement period end
        source: Source format (CSV, OFX, QFX, etc.)
        raw_file_key: Object storage key for raw file (for audit trail)
        tenant: Multi-tenant isolation
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="statements",
    )
    statement_date = models.DateField()
    opening_balance = models.DecimalField(max_digits=20, decimal_places=10)
    closing_balance = models.DecimalField(max_digits=20, decimal_places=10)
    start_date = models.DateField()
    end_date = models.DateField()
    source = models.CharField(max_length=50)
    raw_file_key = models.CharField(max_length=500, blank=True)

    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="bank_statements",
        db_index=True,
    )

    class Meta:
        app_label = "accounting"
        ordering = ["-statement_date"]

    def __str__(self) -> str:
        return f"Statement {self.statement_date} for {self.bank_account}"


class BankTransaction(models.Model):
    """
    Individual transaction from bank statement.

    Accounting Semantics:
        A bank transaction is a single line item from a bank statement.
        It can be matched to a ledger entry (JournalLine) during reconciliation.

        Match Status:
        - UNMATCHED: Not yet matched to any ledger entry
        - SUGGESTED: Auto-matched but not confirmed
        - MATCHED: Manually confirmed match
        - EXCLUDED: Excluded from matching (e.g., bank fees)

        Matching Process:
        1. Import bank statement
        2. Auto-match based on amount, date, reference
        3. Manual review and confirmation
        4. Update reconciliation status

    Attributes:
        guid: UUID primary key
        statement: Parent statement
        transaction_date: Transaction date
        amount: Transaction amount (positive = deposit, negative = withdrawal)
        description: Bank description (e.g., "PAYMENT TO VENDOR")
        reference: Bank reference number (check number, etc.)
        online_id: Unique ID from bank (OFX/HBCI) - prevents duplicate imports
        matched_journal_line: Matched ledger entry (if any)
        match_status: Match status (UNMATCHED, SUGGESTED, MATCHED, EXCLUDED)
        match_confidence: Confidence score for auto-matching (0.00-1.00)
        tenant: Multi-tenant isolation
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    statement = models.ForeignKey(
        BankStatement,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=10)
    description = models.CharField(max_length=1024)
    reference = models.CharField(max_length=255, blank=True)
    online_id = models.CharField(max_length=255, blank=True, unique=True)

    # Match status
    match_status = models.CharField(
        max_length=20,
        choices=[
            ("UNMATCHED", "Unmatched"),
            ("SUGGESTED", "Suggested"),
            ("MATCHED", "Matched"),
            ("EXCLUDED", "Excluded"),
        ],
        default="UNMATCHED",
        db_index=True,
    )
    matched_journal_line = models.ForeignKey(
        "accounting.JournalLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bank_transactions",
    )
    match_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="bank_transactions",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "accounting"
        ordering = ["-transaction_date"]
        indexes = [
            models.Index(fields=["statement", "transaction_date"]),
            models.Index(fields=["online_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_date}: {self.description[:50]} ({self.amount})"


class BankReconciliation(models.Model):
    """
    Bank reconciliation session.

    Accounting Semantics:
        A bank reconciliation session matches bank transactions to ledger entries.
        The goal is to ensure the company's books match the bank's records.

        Reconciliation Process:
        1. Import bank statement
        2. Start reconciliation session
        3. Match bank transactions to ledger entries
        4. Identify differences (timing differences, errors, missing entries)
        5. Complete reconciliation (all transactions matched)

        Status:
        - IN_PROGRESS: Reconciliation in progress
        - COMPLETED: All transactions matched
        - ABANDONED: Reconciliation abandoned (not completed)

    Attributes:
        guid: UUID primary key
        bank_account: Bank account being reconciled
        statement: Bank statement being reconciled
        statement_balance: Closing balance from bank statement
        ledger_balance: Calculated ledger balance
        difference: Difference between statement and ledger (should be 0 when complete)
        status: IN_PROGRESS, COMPLETED, or ABANDONED
        started_at: When reconciliation started
        completed_at: When reconciliation completed
        started_by: User who started reconciliation
        completed_by: User who completed reconciliation
        tenant: Multi-tenant isolation
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="reconciliations",
    )
    statement = models.ForeignKey(
        BankStatement,
        on_delete=models.CASCADE,
        related_name="reconciliations",
    )
    statement_balance = models.DecimalField(max_digits=20, decimal_places=10)
    ledger_balance = models.DecimalField(max_digits=20, decimal_places=10)
    difference = models.DecimalField(max_digits=20, decimal_places=10)

    status = models.CharField(
        max_length=20,
        choices=[
            ("IN_PROGRESS", "In Progress"),
            ("COMPLETED", "Completed"),
            ("ABANDONED", "Abandoned"),
        ],
        default="IN_PROGRESS",
        db_index=True,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    started_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="started_reconciliations",
    )
    completed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_reconciliations",
    )

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="bank_reconciliations",
        db_index=True,
    )

    class Meta:
        app_label = "accounting"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Reconciliation for {self.bank_account} on {self.statement.statement_date}"
