"""
Account model - hierarchical chart of accounts.

Implements account type invariants from the behavior contract:
- BR-ACCT-006: Account fundamental types (ASSET, LIABILITY, INCOME, EXPENSE, EQUITY)
- BR-ACCT-007: AP/AR type detection
- BR-ACCT-010: Root account cannot have parent
"""

import uuid
from typing import Optional

from django.db import models

from .commodities import Commodity


class AccountType(models.TextChoices):
    """
    Detailed account types (mirrors GnuCash GNCAccountType).

    These are specialized types that map to fundamental types.
    """

    # Asset types
    BANK = "BANK", "Bank"
    CASH = "CASH", "Cash"
    CREDIT = "CREDIT", "Credit Card"
    ASSET = "ASSET", "Asset"
    RECEIVABLE = "RECEIVABLE", "Accounts Receivable"
    STOCK = "STOCK", "Stock"
    MUTUAL = "MUTUAL", "Mutual Fund"
    CURRENCY = "CURRENCY", "Currency"
    CHECKING = "CHECKING", "Checking"
    SAVINGS = "SAVINGS", "Savings"
    MONEYMRKT = "MONEYMRKT", "Money Market"

    # Liability types
    LIABILITY = "LIABILITY", "Liability"
    PAYABLE = "PAYABLE", "Accounts Payable"
    CREDITLINE = "CREDITLINE", "Credit Line"

    # Income/Expense/Equity
    INCOME = "INCOME", "Income"
    EXPENSE = "EXPENSE", "Expense"
    EQUITY = "EQUITY", "Equity"

    # Special types
    ROOT = "ROOT", "Root Account"
    TRADING = "TRADING", "Trading"  # System account for multi-currency


class FundamentalType(models.TextChoices):
    """
    Fundamental accounting equation types.

    These are the high-level categories used in financial statements.
    """

    ASSET = "ASSET", "Asset"
    LIABILITY = "LIABILITY", "Liability"
    INCOME = "INCOME", "Income"
    EXPENSE = "EXPENSE", "Expense"
    EQUITY = "EQUITY", "Equity"


class Account(models.Model):
    """
    Hierarchical chart of accounts.

    Each account belongs to a legal entity and has a commodity (currency or security).
    Accounts form a tree structure with parent-child relationships.

    Attributes:
        guid: UUID primary key
        name: Account name (cannot contain account separator)
        code: Account code for sorting/display
        description: Optional description
        account_type: Detailed account type (AccountType)
        fundamental_type: Derived fundamental type (ASSET/LIABILITY/INCOME/EXPENSE/EQUITY)
        commodity: Currency or security for this account
        parent: Parent account (null for root/top-level)
        is_placeholder: Placeholder account (cannot have transactions)
        is_system: System account (hidden from users, e.g., trading accounts)
        tenant: Multi-tenant isolation
        legal_entity: Legal entity that owns this account's ledger
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, db_index=True)
    description = models.TextField(blank=True)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    commodity = models.ForeignKey(
        Commodity,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    is_placeholder = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)  # Hidden trading accounts
    path = models.CharField(max_length=1000, blank=True)  # Full path: "Assets:Current Assets:Cash"
    level = models.IntegerField(default=0)  # Depth in hierarchy

    # Multi-tenancy
    tenant = models.ForeignKey(
        "identity.Tenant",
        on_delete=models.CASCADE,
        related_name="accounts",
        db_index=True,
    )
    legal_entity = models.ForeignKey(
        "identity.LegalEntity",
        on_delete=models.CASCADE,
        related_name="accounts",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounting_engine"
        unique_together = ["name", "parent", "legal_entity"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["account_type"]),
            models.Index(fields=["path"]),
            models.Index(fields=["tenant", "legal_entity"]),
        ]
        ordering = ["path"]

    def __str__(self) -> str:
        return f"{self.code}: {self.name}" if self.code else self.name

    def clean(self):
        """Validate account constraints."""
        from django.core.exceptions import ValidationError

        # BR-ACCT-010: Root account cannot have parent
        if self.account_type == AccountType.ROOT and self.parent is not None:
            raise ValidationError("Root account cannot have a parent account.")

        # Check for account separator in name
        if ":" in self.name:
            raise ValidationError("Account name cannot contain ':' (account separator).")

    def save(self, *args, **kwargs):
        """Save account with path computation."""
        self.full_clean()

        # Compute path and level
        if self.parent:
            self.path = f"{self.parent.path}:{self.name}"
            self.level = self.parent.level + 1
        else:
            self.path = self.name
            self.level = 0

        super().save(*args, **kwargs)

    @property
    def fundamental_type(self) -> FundamentalType:
        """
        BR-ACCT-006: Determine fundamental type from detailed account type.

        Mapping:
        - BANK/STOCK/MONEYMRKT/CHECKING/SAVINGS/MUTUAL/CURRENCY/CASH/ASSET/RECEIVABLE → ASSET
        - CREDIT/LIABILITY/PAYABLE/CREDITLINE → LIABILITY
        - INCOME → INCOME
        - EXPENSE → EXPENSE
        - EQUITY → EQUITY
        - ROOT/TRADING → Special handling
        """
        asset_types = {
            AccountType.BANK,
            AccountType.CASH,
            AccountType.ASSET,
            AccountType.RECEIVABLE,
            AccountType.STOCK,
            AccountType.MUTUAL,
            AccountType.CURRENCY,
            AccountType.CHECKING,
            AccountType.SAVINGS,
            AccountType.MONEYMRKT,
        }

        liability_types = {
            AccountType.CREDIT,
            AccountType.LIABILITY,
            AccountType.PAYABLE,
            AccountType.CREDITLINE,
        }

        if self.account_type in asset_types:
            return FundamentalType.ASSET
        elif self.account_type in liability_types:
            return FundamentalType.LIABILITY
        elif self.account_type == AccountType.INCOME:
            return FundamentalType.INCOME
        elif self.account_type == AccountType.EXPENSE:
            return FundamentalType.EXPENSE
        elif self.account_type == AccountType.EQUITY:
            return FundamentalType.EQUITY
        else:
            # ROOT and TRADING don't have fundamental types
            raise ValueError(f"Account type {self.account_type} has no fundamental type")

    @property
    def is_ap_ar(self) -> bool:
        """
        BR-ACCT-007: Detect AP/AR accounts.

        Returns TRUE only for RECEIVABLE or PAYABLE types.
        """
        return self.account_type in {AccountType.RECEIVABLE, AccountType.PAYABLE}

    @property
    def is_trading_account(self) -> bool:
        """Check if this is a hidden trading account for multi-currency."""
        return self.account_type == AccountType.TRADING or self.is_system

    def get_balance(self, as_of_date=None) -> "Decimal":
        """
        Calculate account balance.

        For asset/expense accounts: debits increase, credits decrease
        For liability/income/equity accounts: credits increase, debits decrease
        """
        from decimal import Decimal
        from django.db.models import Sum, F, Value
        from django.db.models.functions import Coalesce

        # Sum all journal lines for this account
        lines = self.lines.filter(journal_entry__status="posted")

        if as_of_date:
            lines = lines.filter(journal_entry__date__lte=as_of_date)

        total_amount = lines.aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00"))
        )["total"]

        return total_amount

    def get_reconciled_balance(self, as_of_date=None) -> "Decimal":
        """
        BR-SPLIT-004: Calculate reconciled balance.

        Only splits with reconciled state 'y' (RECONCILED) contribute to the balance.
        """
        from decimal import Decimal
        from django.db.models import Sum
        from django.db.models.functions import Coalesce

        lines = self.lines.filter(
            reconcile_status="RECONCILED",
            journal_entry__status="posted",
        )

        if as_of_date:
            lines = lines.filter(journal_entry__date__lte=as_of_date)

        total = lines.aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00"))
        )["total"]

        return total

    def get_cleared_balance(self, as_of_date=None) -> "Decimal":
        """Calculate cleared balance (includes both 'c' and 'y' status)."""
        from decimal import Decimal
        from django.db.models import Sum
        from django.db.models.functions import Coalesce

        lines = self.lines.filter(
            reconcile_status__in=["CLEARED", "RECONCILED"],
            journal_entry__status="posted",
        )

        if as_of_date:
            lines = lines.filter(journal_entry__date__lte=as_of_date)

        total = lines.aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00"))
        )["total"]

        return total
