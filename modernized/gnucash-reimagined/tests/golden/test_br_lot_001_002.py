"""
Acceptance tests for lot invariants.

Implements tests for:
- BR-LOT-001: Lot closure criterion
- BR-LOT-002: Lot balance cached closure flag
"""

import pytest
from decimal import Decimal
from django.test import TestCase

from accounting_engine.models import Lot
from tests.factories import (
    AccountFactory,
    CommodityFactory,
    JournalEntryFactory,
    JournalLineFactory,
    LotFactory,
    TenantFactory,
    LegalEntityFactory,
)

# Note: LotFactory is in tests/factories.py


@pytest.mark.acceptance
@pytest.mark.golden
class TestLotInvariants(TestCase):
    """
    BR-LOT-001: Lot closure criterion

    Given: A Lot with one or more splits
    When: lot balance is computed
    Then: the lot is marked closed if and only if the sum of adjusted
          split amounts equals exactly zero
    """

    @pytest.mark.acceptance
    def test_br_lot_001_lot_with_zero_balance_is_closed(self):
        """Test that a lot with zero balance is marked as closed."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
        )

        lot = Lot.objects.create(
            title="Test Lot",
            account=account,
            tenant=tenant,
            legal_entity=legal_entity,
        )

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
        )

        # Add splits that balance to zero
        line1 = JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("100.00"),
            value=Decimal("100.00"),
        )
        line2 = JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("-100.00"),
            value=Decimal("-100.00"),
        )

        lot.add_line(line1)
        lot.add_line(line2)

        # BR-LOT-001: Lot with zero balance should be closed
        lot.refresh_from_db()
        assert lot.balance == Decimal("0.00")
        assert lot.is_closed is True

    @pytest.mark.acceptance
    def test_br_lot_001_lot_with_nonzero_balance_is_open(self):
        """Test that a lot with non-zero balance is not closed."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
        )

        lot = Lot.objects.create(
            title="Test Lot",
            account=account,
            tenant=tenant,
            legal_entity=legal_entity,
        )

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
        )

        # Add split with non-zero balance
        line = JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("100.00"),
            value=Decimal("100.00"),
        )

        lot.add_line(line)

        # BR-LOT-001: Lot with non-zero balance should not be closed
        lot.refresh_from_db()
        assert lot.balance == Decimal("100.00")
        assert lot.is_closed is False


@pytest.mark.acceptance
@pytest.mark.golden
class TestLotBalanceCache(TestCase):
    """
    BR-LOT-002: Lot balance cached closure flag

    Given: A Lot whose closure status is unknown
    When: closure status is requested
    Then: if status is unknown, balance is computed first to determine
          and cache the closure status
    """

    @pytest.mark.acceptance
    def test_br_lot_002_check_closure_computes_and_caches(self):
        """Test that check_closure computes and caches the closure status."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
        )

        lot = Lot.objects.create(
            title="Test Lot",
            account=account,
            tenant=tenant,
            legal_entity=legal_entity,
            is_closed=False,  # Unknown status
        )

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
        )

        # Add balancing splits
        line1 = JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("100.00"),
            value=Decimal("100.00"),
        )
        line2 = JournalLineFactory(
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("-100.00"),
            value=Decimal("-100.00"),
        )

        lot.add_line(line1)
        lot.add_line(line2)

        # BR-LOT-002: check_closure should compute and cache
        is_closed = lot.check_closure()

        lot.refresh_from_db()
        assert is_closed is True
        assert lot.is_closed is True  # Cached
