"""
Acceptance tests for reconciliation invariants.

Implements tests for:
- BR-SPLIT-001: Split reconciliation states
- BR-SPLIT-004: Reconciled balance only includes reconciled splits
"""

import pytest
from decimal import Decimal
from django.test import TestCase

from accounting_engine.models import (
    Account,
    JournalEntry,
    JournalLine,
    JournalEntryStatus,
    ReconcileStatus,
)
from tests.factories import (
    AccountFactory,
    CommodityFactory,
    JournalEntryFactory,
    JournalLineFactory,
    TenantFactory,
    LegalEntityFactory,
)


@pytest.mark.acceptance
@pytest.mark.golden
class TestReconciliationStates(TestCase):
    """
    BR-SPLIT-001: Split reconciliation states

    Given: A Split in a Transaction
    When: the reconciled flag is examined
    Then: valid values are: 'n' (not reconciled), 'c' (cleared), 'y' (reconciled),
          'f' (frozen), 'v' (void)
    """

    @pytest.mark.acceptance
    def test_br_split_001_valid_reconciliation_states(self):
        """Test that valid reconciliation states are accepted."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
        )
        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
        )

        # BR-SPLIT-001: All valid states should be accepted
        valid_states = [
            "NOT_CLEARED",
            "CLEARED",
            "RECONCILED",
            "FROZEN",
            "VOID",
        ]

        for state in valid_states:
            line = JournalLineFactory(
                journal_entry=journal_entry,
                account=account,
                amount=Decimal("100.00"),
                value=Decimal("100.00"),
                reconcile_status=state,
            )
            assert line.reconcile_status == state

    @pytest.mark.acceptance
    def test_br_split_001_state_transitions(self):
        """Test that state transitions follow allowed transitions."""
        # BR-SPLIT-001: Explicit ALLOWED_TRANSITIONS matrix
        from accounting_engine.models import ReconcileStatus

        # Test allowed transitions
        allowed = ReconcileStatus.get_allowed_transitions("NOT_CLEARED")
        assert "CLEARED" in allowed
        assert "VOID" in allowed

        allowed = ReconcileStatus.get_allowed_transitions("CLEARED")
        assert "NOT_CLEARED" in allowed
        assert "RECONCILED" in allowed
        assert "VOID" in allowed

        allowed = ReconcileStatus.get_allowed_transitions("RECONCILED")
        assert "CLEARED" in allowed
        assert "FROZEN" in allowed
        assert "VOID" in allowed

        # FROZEN is final - no transitions allowed
        allowed = ReconcileStatus.get_allowed_transitions("FROZEN")
        assert len(allowed) == 0


@pytest.mark.acceptance
@pytest.mark.golden
class TestReconciledBalance(TestCase):
    """
    BR-SPLIT-004: Reconciled balance only includes reconciled splits

    Given: An Account with splits in various states
    When: reconciled balance is computed
    Then: only splits with reconciled state 'y' (RECONCILED) contribute to the balance;
          cleared ('c') and not-reconciled ('n') splits are excluded
    """

    @pytest.mark.acceptance
    def test_br_split_004_reconciled_balance_excludes_not_cleared(self):
        """Test that NOT_CLEARED splits are excluded from reconciled balance."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="BANK",
        )

        # Posted journal entry with NOT_CLEARED split
        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
            status=JournalEntryStatus.POSTED,
            is_posted=True,
        )

        JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("1000.00"),
            value=Decimal("1000.00"),
            reconcile_status="NOT_CLEARED",
        )

        # BR-SPLIT-004: Reconciled balance should be 0 (NOT_CLEARED excluded)
        reconciled_balance = account.get_reconciled_balance()
        assert reconciled_balance == Decimal("0.00")

    @pytest.mark.acceptance
    def test_br_split_004_reconciled_balance_excludes_cleared(self):
        """Test that CLEARED splits are excluded from reconciled balance."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="BANK",
        )

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
            status=JournalEntryStatus.POSTED,
            is_posted=True,
        )

        JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("1000.00"),
            value=Decimal("1000.00"),
            reconcile_status="CLEARED",
        )

        # BR-SPLIT-004: Reconciled balance should be 0 (CLEARED excluded)
        reconciled_balance = account.get_reconciled_balance()
        assert reconciled_balance == Decimal("0.00")

    @pytest.mark.acceptance
    def test_br_split_004_reconciled_balance_includes_reconciled(self):
        """Test that RECONCILED splits are included in reconciled balance."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="BANK",
        )

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
            status=JournalEntryStatus.POSTED,
            is_posted=True,
        )

        JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("1000.00"),
            value=Decimal("1000.00"),
            reconcile_status="RECONCILED",
        )

        # BR-SPLIT-004: Reconciled balance should include RECONCILED splits
        reconciled_balance = account.get_reconciled_balance()
        assert reconciled_balance == Decimal("1000.00")

    @pytest.mark.acceptance
    def test_br_split_004_cleared_balance_includes_both_cleared_and_reconciled(self):
        """Test that cleared balance includes both CLEARED and RECONCILED splits."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="BANK",
        )

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
            status=JournalEntryStatus.POSTED,
            is_posted=True,
        )

        # CLEARED split
        JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("500.00"),
            value=Decimal("500.00"),
            reconcile_status="CLEARED",
        )

        # RECONCILED split
        JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("300.00"),
            value=Decimal("300.00"),
            reconcile_status="RECONCILED",
        )

        # Cleared balance should include both
        cleared_balance = account.get_cleared_balance()
        assert cleared_balance == Decimal("800.00")
