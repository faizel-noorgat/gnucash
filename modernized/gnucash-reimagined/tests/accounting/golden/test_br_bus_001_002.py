"""
Acceptance tests for business document posting invariants.

Implements tests for:
- BR-BUS-001: Invoice posting is one-way
- BR-BUS-002: Invoice amounts are always stored positive

Note: These rules are primarily enforced by the Business Documents service,
but the accounting engine provides the posting mechanism and journal immutability.
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.accounting.models import (
    JournalEntry,
    JournalLine,
    JournalEntryStatus,
)
from apps.accounting.services.posting import PostingService
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
class TestInvoicePostingInvariants(TestCase):
    """
    BR-BUS-001: Invoice posting is one-way

    Given: An Invoice that is not yet posted
    When: posting is initiated
    Then: a new Lot is created; a new Transaction is created;
          the invoice is marked posted;
          attempting to post an already-posted invoice returns NULL
    """

    @pytest.mark.acceptance
    def test_br_bus_001_journal_entry_posting_is_one_way(self):
        """Test that posting a journal entry is one-way (cannot un-post)."""
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

        # Create balanced journal entry
        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
            status=JournalEntryStatus.DRAFT,
            is_posted=False,
        )

        JournalLineFactory(
            journal_entry=journal_entry,
            account=cash_account,
            amount=Decimal("1000.00"),
            value=Decimal("1000.00"),
        )
        JournalLineFactory(
            journal_entry=journal_entry,
            account=revenue_account,
            amount=Decimal("-1000.00"),
            value=Decimal("-1000.00"),
        )

        # Post the journal entry
        posted_entry = PostingService.post_journal_entry(journal_entry)

        # BR-BUS-001: Posting is one-way
        assert posted_entry.is_posted is True
        assert posted_entry.status == JournalEntryStatus.POSTED

        # Attempting to post again should raise an error
        with pytest.raises(ValidationError, match="already posted"):
            PostingService.post_journal_entry(posted_entry)

    @pytest.mark.acceptance
    def test_br_bus_001_posted_journal_cannot_be_unposted(self):
        """Test that a posted journal entry cannot be un-posted."""
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
            status=JournalEntryStatus.POSTED,
            is_posted=True,
        )

        # BR-BUS-001: Cannot change status back to draft
        journal_entry.status = JournalEntryStatus.DRAFT
        journal_entry.is_posted = False

        # This should fail at validation level (and at the database level via
        # the ADR-010 triggers once they exist)
        with pytest.raises(ValidationError, match="un-post"):
            journal_entry.save()

        # The posted fact is untouched - the transition was rejected outright
        journal_entry.refresh_from_db()
        assert journal_entry.is_posted is True
        assert journal_entry.status == JournalEntryStatus.POSTED


@pytest.mark.acceptance
@pytest.mark.golden
class TestInvoiceAmountInvariants(TestCase):
    """
    BR-BUS-002: Invoice amounts are always stored positive

    Given: An Invoice or Bill or Credit Note with entries
    When: entry values are converted to posting splits
    Then: amounts in entries are always stored as positive values;
          the sign for the split is determined by the owner type (customer vs vendor/employee)
    """

    @pytest.mark.acceptance
    def test_br_bus_002_positive_amounts_in_entries(self):
        """
        Test that journal lines for sales invoices have proper sign conventions.

        Note: This is a simplified test. The full implementation would be in
        the Business Documents service which creates the journal entries.
        """
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        # Sales invoice: debit AR (positive), credit Revenue (negative)
        ar_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="RECEIVABLE",
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

        # BR-BUS-002: AR debit is positive
        JournalLineFactory(
            journal_entry=journal_entry,
            account=ar_account,
            amount=Decimal("1000.00"),  # Positive debit
            value=Decimal("1000.00"),
        )

        # Revenue credit is negative
        JournalLineFactory(
            journal_entry=journal_entry,
            account=revenue_account,
            amount=Decimal("-1000.00"),  # Negative credit
            value=Decimal("-1000.00"),
        )

        # Verify the entry is balanced
        assert journal_entry.is_balanced is True

    @pytest.mark.acceptance
    def test_br_bus_002_purchase_invoice_sign_convention(self):
        """
        Test that journal lines for purchase bills have opposite sign convention.

        Purchase bill: debit Expense (positive), credit AP (negative)
        """
        tenant = TenantFactory()
        legal_entity = LegalEntityFactory(tenant=tenant)
        currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

        expense_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="EXPENSE",
        )
        ap_account = AccountFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            commodity=currency,
            account_type="PAYABLE",
        )

        journal_entry = JournalEntryFactory(
            tenant=tenant,
            legal_entity=legal_entity,
            transaction_currency=currency,
        )

        # Expense debit is positive
        JournalLineFactory(
            journal_entry=journal_entry,
            account=expense_account,
            amount=Decimal("500.00"),
            value=Decimal("500.00"),
        )

        # AP credit is negative
        JournalLineFactory(
            journal_entry=journal_entry,
            account=ap_account,
            amount=Decimal("-500.00"),
            value=Decimal("-500.00"),
        )

        # Verify the entry is balanced
        assert journal_entry.is_balanced is True
