"""
Domain models package for accounting app.

This package contains all the domain models for the accounting bounded context:

Commodities & Currency:
    - Commodity: Anything tradable (currencies, securities, cryptocurrencies)
    - Currency: Proxy model for currency-specific operations
    - ExchangeRate: Historical exchange rates between commodities

Accounts:
    - Account: Hierarchical chart of accounts
    - AccountType: Detailed account types (BANK, CASH, RECEIVABLE, etc.)
    - FundamentalType: High-level categories (ASSET, LIABILITY, INCOME, EXPENSE, EQUITY)

Journals:
    - JournalEntry: Double-entry transaction (immutable once posted - ADR-010)
    - JournalLine: Individual debit/credit entry with dual-field amount/value (ADR-009)
    - ImmutablePostedJournalEntry: Immutable snapshot of posted entries
    - ImmutablePostedJournalLine: Immutable snapshot of posted lines
    - TransactionMetadata: Mutable operational state for journal entries

Lots:
    - Lot: Groups splits for inventory/stock tracking

Fiscal:
    - FiscalPeriod: Period for period-end controls
    - TaxRule: Versioned tax rules with effective dates
    - PaymentTerm: Payment terms with due dates and discounts

Reconciliation & Banking:
    - BankAccount: Links ledger account to real bank account
    - BankStatement: Imported bank statement
    - BankTransaction: Individual transaction from bank statement
    - BankReconciliation: Reconciliation session
    - ReconcileStatus: Reconciliation state machine
    - ReconciliationAuditLog: Audit trail for reconciliation changes

Intercompany:
    - IntercompanyRelationship: Links two legal entities
    - InterEntityEvent: Coordination object for inter-entity transactions
    - CounterpartPosting: Proposed posting in counterparty entity

Audit:
    - AuditEvent: Immutable audit trail for all financial actions

Accounting Semantics:
    These models implement the core accounting functionality:
    - Double-entry bookkeeping (every transaction has equal debits and credits)
    - Multi-currency support (dual-field amount/value model)
    - Period-end controls (fiscal period locking)
    - Audit trail (immutable audit events)
    - Bank reconciliation (matching bank transactions to ledger entries)
    - Intercompany transactions (coordinating entries across legal entities)

    Key Business Rules:
    - BR-ACCT-001: Journal entries must balance (debits = credits)
    - BR-ACCT-002: Balance checked per commodity for multi-currency
    - BR-ACCT-006: Account fundamental types determine normal balance
    - BR-ACCT-007: AP/AR detection for invoice processing
    - BR-ACCT-010: Root account cannot have parent
    - BR-SPLIT-001: Reconciliation state machine
    - BR-SPLIT-004: Reconciled balance only includes reconciled splits
    - BR-FX-001: Price lookup nearest-in-time
    - BR-LOT-001: Lot closure criterion (balance = 0)
    - BR-LOT-002: Lot balance cached closure flag
    - BR-TAX-001: Tax table entry types (VALUE, PERCENT)
    - BR-TAX-002: Tax-included price back-computation
    - BR-TAX-003: Discount ordering modes (PRETAX, SAMETIME, POSTTAX)

    Key ADRs:
    - ADR-004: Minimal intercompany functionality
    - ADR-009: Dual-field multi-currency model
    - ADR-010: Posted journal immutability
"""

from .accounts import Account, AccountType, FundamentalType
from .audit import AuditAction, AuditEvent
from .commodities import Commodity, CommodityNamespace, Currency, ExchangeRate
from .fiscal import (
    DiscountOrderingMode,
    FiscalPeriod,
    FiscalPeriodStatus,
    PaymentTerm,
    TaxRule,
    TaxRuleType,
)
from .intercompany import (
    CounterpartPosting,
    InterEntityEvent,
    IntercompanyRelationship,
)
from .journals import (
    ImmutablePostedJournalEntry,
    ImmutablePostedJournalLine,
    JournalEntry,
    JournalEntryStatus,
    JournalLine,
    TransactionMetadata,
)
from .lots import Lot
from .reconciliation import (
    BankAccount,
    BankReconciliation,
    BankStatement,
    BankTransaction,
    ReconcileStatus,
    ReconciliationAuditLog,
)

__all__ = [
    # Commodities
    "Commodity",
    "CommodityNamespace",
    "Currency",
    "ExchangeRate",
    # Accounts
    "Account",
    "AccountType",
    "FundamentalType",
    # Journals
    "JournalEntry",
    "JournalLine",
    "JournalEntryStatus",
    "ImmutablePostedJournalEntry",
    "ImmutablePostedJournalLine",
    "TransactionMetadata",
    # Lots
    "Lot",
    # Fiscal
    "FiscalPeriod",
    "FiscalPeriodStatus",
    "TaxRule",
    "TaxRuleType",
    "PaymentTerm",
    "DiscountOrderingMode",
    # Reconciliation
    "ReconcileStatus",
    "ReconciliationAuditLog",
    # Banking
    "BankAccount",
    "BankStatement",
    "BankTransaction",
    "BankReconciliation",
    # Intercompany
    "IntercompanyRelationship",
    "InterEntityEvent",
    "CounterpartPosting",
    # Audit
    "AuditEvent",
    "AuditAction",
]
