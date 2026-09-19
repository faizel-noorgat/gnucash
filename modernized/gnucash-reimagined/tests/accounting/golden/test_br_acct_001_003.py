"""
Acceptance tests for transaction balance invariants.

Implements tests for:
- BR-ACCT-001: Transaction balance invariant (double-entry)
- BR-ACCT-002: Multi-currency transaction balance per commodity
- BR-ACCT-003: Transaction edit atomicity
"""

import pytest
from decimal import Decimal
from django.test import TestCase

from apps.accounting.models import (
    Account,
    Commodity,
    JournalEntry,
    JournalLine,
    JournalEntryStatus,
)
from tests.accounting.golden.factories import (
    AccountFactory,
    CommodityFactory,
    JournalEntryFactory,
    JournalLineFactory,
    TenantFactory,
    LegalEntityFactory,
)


@pytest.mark.acceptance
@pytest.mark.golden
class TestTransactionBalanceInvariants(TestCase):
    """
    BR-ACCT-001: Transaction balance invariant (double-entry)

    Given: A Transaction with one or more Splits
    When: the transaction is evaluated for balance
    Then: the sum of all Split values must be exactly zero;
          if trading accounts are in use, the non-trading splits must sum to zero
          AND the trading splits must sum to zero independently
    """

    @pytest.mark.acceptance
    def test_br_acct_001_simple_balanced_transaction(self):
        """Test that a simple balanced transaction passes validation."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        # Create accounts
        cash_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="BANK",
            name="Cash",
        )
        revenue_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="INCOME",
            name="Revenue",
        )

        # Create balanced journal entry
        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
        )

        # Debit cash
        JournalLineFactory(
            journal_entry=journal_entry,
            account=cash_account,
            amount=Decimal("1000.00"),
            value=Decimal("1000.00"),
        )

        # Credit revenue
        JournalLineFactory(
            journal_entry=journal_entry,
            account=revenue_account,
            amount=Decimal("-1000.00"),
            value=Decimal("-1000.00"),
        )

        # BR-ACCT-001: Transaction must be balanced
        assert journal_entry.is_balanced is True

    @pytest.mark.acceptance
    def test_br_acct_001_unbalanced_transaction_fails(self):
        """Test that an unbalanced transaction fails validation."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        cash_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="BANK",
        )
        revenue_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="INCOME",
        )

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
        )

        # Debit cash
        JournalLineFactory(
            journal_entry=journal_entry,
            account=cash_account,
            amount=Decimal("1000.00"),
            value=Decimal("1000.00"),
        )

        # Credit revenue (but not enough)
        JournalLineFactory(
            journal_entry=journal_entry,
            account=revenue_account,
            amount=Decimal("-900.00"),
            value=Decimal("-900.00"),
        )

        # BR-ACCT-001: Transaction must NOT be balanced
        assert journal_entry.is_balanced is False

    @pytest.mark.acceptance
    def test_br_acct_002_multi_currency_balance_per_commodity(self):
        """
        BR-ACCT-002: Multi-currency transaction balance per commodity

        Given: A Transaction using trading accounts with splits in multiple commodities
        When: imbalance is computed
        Then: imbalance is computed per-commodity (not aggregated);
              the transaction is balanced only if there is zero imbalance in every commodity
        """
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)

        # Create two currencies
        usd = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)
        sgd = CommodityFactory(tenant=tenant, mnemonic="SGD", fraction=100)

        # Create accounts in different currencies. Cross-commodity movements are
        # carried by trading accounts (ADR-009), which are system accounts:
        # hidden from users and used to balance each commodity independently.
        usd_bank = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=usd,
            account_type="BANK",
            name="USD Bank",
        )
        usd_trading = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=usd,
            account_type="TRADING",
            is_system_account=True,
            name="Trading USD",
        )
        sgd_bank = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=sgd,
            account_type="BANK",
            name="SGD Bank",
        )
        sgd_trading = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=sgd,
            account_type="TRADING",
            is_system_account=True,
            name="Trading SGD",
        )

        # Create journal entry in SGD (base currency)
        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=sgd,
        )

        # Exchange of USD 1000 for SGD 1340 (rate 1.34), booked with trading
        # accounts so that every commodity nets to zero on its own.
        JournalLineFactory(
            journal_entry=journal_entry,
            account=usd_bank,
            amount=Decimal("1000.00"),   # USD
            value=Decimal("1340.00"),    # SGD
        )
        JournalLineFactory(
            journal_entry=journal_entry,
            account=usd_trading,
            amount=Decimal("-1000.00"),  # USD
            value=Decimal("-1340.00"),   # SGD
        )
        JournalLineFactory(
            journal_entry=journal_entry,
            account=sgd_bank,
            amount=Decimal("-1340.00"),  # SGD
            value=Decimal("-1340.00"),   # SGD
        )
        JournalLineFactory(
            journal_entry=journal_entry,
            account=sgd_trading,
            amount=Decimal("1340.00"),   # SGD
            value=Decimal("1340.00"),    # SGD
        )

        # BR-ACCT-002: USD nets to zero AND SGD nets to zero, so the entry balances
        assert journal_entry.is_balanced is True

        # Control: the same cross-commodity exchange WITHOUT trading accounts
        # nets to zero when aggregated, but not per commodity - so it must NOT
        # be considered balanced. This is what makes the check per-commodity
        # rather than a single aggregated sum.
        untraded_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=sgd,
        )
        JournalLineFactory(
            journal_entry=untraded_entry,
            account=usd_bank,
            amount=Decimal("1000.00"),   # USD - never offset in USD
            value=Decimal("1340.00"),    # SGD
        )
        JournalLineFactory(
            journal_entry=untraded_entry,
            account=sgd_bank,
            amount=Decimal("-1340.00"),  # SGD
            value=Decimal("-1340.00"),   # SGD
        )

        # Values sum to zero, yet USD is left at +1000 and SGD at -1340
        assert sum(line.value for line in untraded_entry.lines.all()) == Decimal("0.00")
        assert untraded_entry.is_balanced is False

    @pytest.mark.acceptance
    def test_br_acct_002_amount_and_value_are_checked_separately(self):
        """Regression: amount and value must not share one accumulator.

        A line whose account commodity equals the transaction currency used to
        contribute its `amount` and its `value` to the SAME bucket, so two
        errors cancelled: a single line with amount +100 and value -100, with
        no offsetting line anywhere, summed to zero and was reported balanced.

        `is_balanced` gates JournalEntry.post() and
        PostingService.post_journal_entry(), so this permitted unbalanced
        entries to be posted - a BR-ACCT-001/002 violation.
        """
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
        )
        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
        )
        # One line only. Nothing offsets it, so this entry cannot be balanced.
        JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("100.00"),
            value=Decimal("-100.00"),
        )

        assert journal_entry.lines.count() == 1
        assert journal_entry.is_balanced is False


@pytest.mark.acceptance
@pytest.mark.golden
class TestTransactionEditAtomicity(TestCase):
    """
    BR-ACCT-003: Transaction edit atomicity

    Given: A Transaction being modified
    When: BeginEdit is called before the edit
    Then: a clone of the transaction is preserved;
          if CommitEdit is called the changes persist;
          if RollbackEdit is called the transaction is restored to the clone
    """

    @pytest.mark.acceptance
    def test_br_acct_003_draft_transaction_can_be_modified(self):
        """Test that draft transactions can be modified."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
            status=JournalEntryStatus.DRAFT,
            is_posted=False,
        )

        # Add a line
        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
        )
        line = JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("100.00"),
            value=Decimal("100.00"),
        )

        # Modify the line
        line.amount = Decimal("200.00")
        line.save()

        # BR-ACCT-003: Draft transactions can be modified
        line.refresh_from_db()
        assert line.amount == Decimal("200.00")

    @pytest.mark.acceptance
    def test_br_acct_003_posted_transaction_cannot_be_modified(self):
        """Test that posted transactions cannot be modified."""
        from django.core.exceptions import ValidationError

        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        # Lifecycle: draft -> lines -> post. A posted entry cannot be built
        # directly, because posting is what makes it immutable.
        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
            status=JournalEntryStatus.DRAFT,
            is_posted=False,
        )

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
        )
        balancing_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="INCOME",
        )
        line = JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("100.00"),
            value=Decimal("100.00"),
        )
        JournalLineFactory(
            journal_entry=journal_entry,
            account=balancing_account,
            amount=Decimal("-100.00"),
            value=Decimal("-100.00"),
        )

        journal_entry.post()
        journal_entry.refresh_from_db()
        assert journal_entry.is_posted is True

        # BR-ACCT-003: Posted transactions cannot be modified
        line.amount = Decimal("200.00")
        with pytest.raises(ValidationError, match="Cannot modify lines of a posted journal entry"):
            line.save()

        # The posted line is untouched
        line.refresh_from_db()
        assert line.amount == Decimal("100.00")
