"""
Account model - hierarchical chart of accounts.

Implements account type invariants from the behavior contract:
- BR-ACCT-006: Account fundamental types (ASSET, LIABILITY, INCOME, EXPENSE, EQUITY)
- BR-ACCT-007: AP/AR type detection
- BR-ACCT-010: Root account cannot have parent

Accounting Semantics:
    The chart of accounts is the backbone of any accounting system.
    Accounts are organized hierarchically (e.g., Assets:Current Assets:Cash).
    Each account has a type that determines its normal balance (debit or credit).

    Fundamental types map to the accounting equation:
    Assets = Liabilities + Equity + Income - Expenses

    Trading accounts are special system accounts used for multi-currency
    transactions. They are marked with is_system_account=True and are
    hidden from user-facing reports.
"""

import uuid
from typing import Optional

from django.db import models

from .commodities import Commodity


class AccountType(models.TextChoices):
    """
    Detailed account types (mirrors GnuCash GNCAccountType).

    These are specialized types that map to fundamental types.
    The mapping is defined in Account.fundamental_type property.
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
    The fundamental type is derived from the detailed account_type.

    Accounting Equation:
        Assets = Liabilities + Equity + Income - Expenses
    """

    ASSET = "ASSET", "Asset"
    LIABILITY = "LIABILITY", "Liability"
    INCOME = "INCOME", "Income"
    EXPENSE = "EXPENSE", "Expense"
    EQUITY = "EQUITY", "Equity"


class Account(models.Model):
    """
    Hierarchical chart of accounts.

    Accounting Semantics:
        Each account belongs to a legal entity and has a commodity (currency or security).
        Accounts form a tree structure with parent-child relationships.
        The `path` field stores the full hierarchical path (e.g., "Assets:Current Assets:Cash").

        Key constraints:
        - BR-ACCT-010: Root account cannot have a parent
        - Account name cannot contain the account separator (':')
        - Placeholder accounts cannot have transactions

        System accounts (is_system_account=True):
        - Trading accounts for multi-currency transactions
        - Hidden from user-facing reports
        - Used internally to balance cross-commodity transactions

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
        is_system_account: System account (hidden from users, e.g., trading accounts)
        path: Full hierarchical path (e.g., "Assets:Current Assets:Cash")
        level: Depth in hierarchy (0 for root)
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
    is_system_account = models.BooleanField(
        default=False,
        help_text="System account (hidden from users, e.g., trading accounts for multi-currency)"
    )
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
        app_label = "accounting"
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
        """
        Validate account constraints.

        BR-ACCT-010: Root account cannot have parent
        Account name cannot contain the account separator (':')
        """
        from django.core.exceptions import ValidationError

        # BR-ACCT-010: Root account cannot have parent
        if self.account_type == AccountType.ROOT and self.parent is not None:
            raise ValidationError("Root account cannot have a parent account.")

        # Check for account separator in name
        if ":" in self.name:
            raise ValidationError("Account name cannot contain ':' (account separator).")

    def save(self, *args, **kwargs):
        """
        Save account with path computation.

        Automatically computes the hierarchical path and level based on parent.
        Calls full_clean() to enforce validation constraints.
        """
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

        Accounting Semantics:
            The fundamental type determines the normal balance direction:
            - ASSET, EXPENSE: Debit increases, Credit decreases
            - LIABILITY, INCOME, EQUITY: Credit increases, Debit decreases

        Mapping:
        - BANK/STOCK/MONEYMRKT/CHECKING/SAVINGS/MUTUAL/CURRENCY/CASH/ASSET/RECEIVABLE → ASSET
        - CREDIT/LIABILITY/PAYABLE/CREDITLINE → LIABILITY
        - INCOME → INCOME
        - EXPENSE → EXPENSE
        - EQUITY → EQUITY
        - ROOT/TRADING → Special handling (no fundamental type)
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

        Accounting Semantics:
            Accounts Receivable (AR) and Accounts Payable (AP) are special
            asset/liability accounts that track amounts owed to/from customers/vendors.
            They are used in invoice processing and payment workflows.

        Returns TRUE only for RECEIVABLE or PAYABLE types.
        """
        return self.account_type in {AccountType.RECEIVABLE, AccountType.PAYABLE}

    @property
    def is_trading_account(self) -> bool:
        """
        Check if this is a hidden trading account for multi-currency.

        Accounting Semantics:
            Trading accounts are system accounts used to balance multi-currency
            transactions. For example, when buying EUR with USD:
            - Debit EUR Bank Account (amount in EUR)
            - Credit USD Bank Account (amount in USD)
            - Debit/Credit Trading Account (balances the commodity mismatch)

            Trading accounts are marked with is_system_account=True and
            are hidden from user-facing reports.
        """
        return self.account_type == AccountType.TRADING or self.is_system_account

    def get_balance(self, as_of_date=None) -> "Decimal":
        """
        Calculate account balance.

        Accounting Semantics:
            For asset/expense accounts: debits increase, credits decrease
            For liability/income/equity accounts: credits increase, debits decrease

            Only posted journal entries contribute to the balance.
            Draft entries are excluded.

        Args:
            as_of_date: Calculate balance as of this date (optional)

        Returns:
            Decimal balance in the account's commodity
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

        Accounting Semantics:
            Only splits with reconciled state 'y' (RECONCILED) contribute to the balance.
            This is used in bank reconciliation to compare against the bank statement.

        Args:
            as_of_date: Calculate balance as of this date (optional)

        Returns:
            Decimal reconciled balance in the account's commodity
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
        """
        Calculate cleared balance (includes both 'c' and 'y' status).

        Accounting Semantics:
            Cleared balance includes both CLEARED and RECONCILED splits.
            This represents transactions that have been processed by the bank
            but may not yet be fully reconciled.

        Args:
            as_of_date: Calculate balance as of this date (optional)

        Returns:
            Decimal cleared balance in the account's commodity
        """
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
