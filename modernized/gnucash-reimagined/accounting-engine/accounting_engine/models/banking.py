"""
Banking and reconciliation models.

Merged into Accounting Engine per ADR-003.
"""

import uuid
from decimal import Decimal

from django.db import models


class BankAccount(models.Model):
    """
    Bank account linked to a ledger account.

    Attributes:
        guid: UUID primary key
        account: Linked ledger account
        bank_name: Name of the bank
        account_number: Bank account number
        routing_number: Routing number / sort code
        currency: Account currency
        is_active: Whether the account is active
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.OneToOneField(
        "accounting_engine.Account",
        on_delete=models.PROTECT,
        related_name="bank_account",
    )
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50, blank=True)
    currency = models.ForeignKey(
        "accounting_engine.Commodity",
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
        app_label = "accounting_engine"
        unique_together = ["bank_name", "account_number", "tenant"]

    def __str__(self) -> str:
        return f"{self.bank_name} - {self.account_number}"


class BankStatement(models.Model):
    """
    Imported bank statement.

    Attributes:
        guid: UUID primary key
        bank_account: The bank account this statement belongs to
        statement_date: Statement date
        opening_balance: Opening balance
        closing_balance: Closing balance
        start_date: Statement period start
        end_date: Statement period end
        source: Source format (CSV, OFX, etc.)
        raw_file_key: Object storage key for raw file
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
        app_label = "accounting_engine"
        ordering = ["-statement_date"]

    def __str__(self) -> str:
        return f"Statement {self.statement_date} for {self.bank_account}"


class BankTransaction(models.Model):
    """
    Individual transaction from bank statement.

    Attributes:
        guid: UUID primary key
        statement: Parent statement
        transaction_date: Transaction date
        amount: Transaction amount
        description: Bank description
        reference: Bank reference number
        online_id: Unique ID from bank (OFX/HBCI)
        matched_journal_line: Matched ledger entry (if any)
        match_status: Match status
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
        "accounting_engine.JournalLine",
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
        app_label = "accounting_engine"
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

    Matches bank transactions to ledger entries.
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
        app_label = "accounting_engine"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Reconciliation for {self.bank_account} on {self.statement.statement_date}"
