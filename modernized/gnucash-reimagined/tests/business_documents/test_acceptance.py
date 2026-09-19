"""
Acceptance tests for behavior-contract rules assigned to business-documents service.

These tests verify the P0 business rules that must be preserved:
- BR-BUS-001: Invoice posting is one-way
- BR-BUS-002: Invoice amounts are always stored positive

Tests are tagged with rule IDs for traceability.
"""
import pytest
from django.test import TestCase
from decimal import Decimal
from apps.business_documents.models import (
    Party, PartyRole, AccountingDocument, DocumentType, DocumentDirection,
    DocumentStatus, DocumentLine
)
from tests.business_documents.factories import (
    PartyFactory, AccountingDocumentFactory, DocumentLineFactory,
    TenantFactory, LegalEntityFactory, CurrencyFactory, AccountFactory
)
from apps.business_documents.services.posting import DocumentPostingService
from apps.accounting.models import JournalEntry


@pytest.mark.acceptance
class TestBR_BUS_001_InvoicePostingIsOneWay(TestCase):
    """
    BR-BUS-001: Invoice posting is one-way

    Given: An Invoice that is not yet posted
    When: posting is initiated
    Then: a new Lot is created; a new Transaction is created; the invoice is marked posted;
          attempting to post an already-posted invoice returns NULL
    """

    def setUp(self):
        """Set up test data"""
        self.tenant = TenantFactory()
        self.legal_entity = LegalEntityFactory(tenant=self.tenant)
        self.party = PartyFactory(tenant=self.tenant, roles=[PartyRole.CUSTOMER])
        # Same tenant as everything else - a Currency is tenant-scoped, and
        # CurrencyFactory() with no argument would build its own.
        self.currency = CurrencyFactory(tenant=self.tenant)

        # Revenue account the invoice line posts against.
        self.account = AccountFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            commodity=self.currency,
            account_type='INCOME',
        )
        # DocumentPostingService._get_receivable_account looks up an account of
        # type RECEIVABLE scoped to the document's tenant and legal entity, and
        # raises ValueError if there is none. The fixture never created one, so
        # posting could not get past its first step.
        self.receivable_account = AccountFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            commodity=self.currency,
            account_type='RECEIVABLE',
        )

        # Create a draft invoice
        self.document = AccountingDocumentFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            party=self.party,
            currency=self.currency,
            status=DocumentStatus.DRAFT,
            document_type=DocumentType.INVOICE,
            direction=DocumentDirection.SALES
        )

        # Add a line item
        self.line = DocumentLineFactory(
            document=self.document,
            account=self.account,
            quantity=Decimal('2.0000'),
            unit_price=Decimal('100.0000')
        )

        # Mock user.
        # `email` is the USERNAME_FIELD on the unified User model and is
        # non-null + unique, so it is required here; the previous call passed
        # only username/password and raised TypeError.
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            email='testuser@example.com', password='testpass'
        )

        self.posting_service = DocumentPostingService()

    def test_document_starts_as_draft(self):
        """Document should start in draft status"""
        self.assertEqual(self.document.status, DocumentStatus.DRAFT)
        self.assertFalse(self.document.is_posted)

    def test_can_post_draft_document(self):
        """Should be able to post a draft document"""
        self.assertTrue(self.document.can_post())

    def test_posting_creates_journal_entry(self):
        """Posting should create a journal entry in accounting engine"""
        # The unconditional pytest.xfail("Accounting engine not yet
        # implemented") that used to sit here was stale: the accounting engine
        # is implemented and its golden suite is green, so it was silently
        # disabling every assertion below it.
        journal_entry = self.posting_service.post_document(self.document, self.user)

        self.assertIsNotNone(journal_entry)
        self.assertTrue(journal_entry.is_posted)

    def test_posting_marks_document_as_posted(self):
        """Posting should mark document as posted"""
        # See the note above - the unconditional xfail has been removed.
        #
        # post_document() now owns the whole lifecycle, so this test no longer
        # calls mark_posted() itself. That manual call is what let a posted
        # JournalEntry sit alongside a document the service had left in DRAFT
        # without any test noticing.
        journal_entry = self.posting_service.post_document(self.document, self.user)

        self.assertEqual(self.document.status, DocumentStatus.POSTED)
        self.assertTrue(self.document.is_posted)
        self.assertIsNotNone(self.document.posted_at)
        self.assertEqual(self.document.posted_by, self.user)
        self.assertEqual(self.document.journal_entry, journal_entry)

        # The ledger entry is posted, not merely created.
        self.assertTrue(journal_entry.is_posted)

        # BR-BUS-001: a second posting is rejected and leaves the ledger alone.
        # The count is asserted, not just the exception, because "raises" and
        # "raised before creating a second journal entry" are different
        # guarantees and only the second one protects the books.
        with self.assertRaises(ValueError) as context:
            self.posting_service.post_document(self.document, self.user)

        self.assertIn("already been posted", str(context.exception))
        self.assertEqual(
            JournalEntry.objects.filter(source_document=self.document).count(), 1
        )
        self.document.refresh_from_db()
        self.assertEqual(self.document.journal_entry, journal_entry)

    def test_cannot_post_already_posted_document(self):
        """BR-BUS-001: Attempting to post an already-posted invoice should fail"""
        # Mark document as posted
        self.document.status = DocumentStatus.POSTED
        self.document.save()

        # Attempt to post again should fail
        with self.assertRaises(ValueError) as context:
            self.posting_service.post_document(self.document, self.user)

        self.assertIn("already been posted", str(context.exception))

    def test_posted_document_cannot_be_modified(self):
        """Posted documents should not be modifiable"""
        # Mark document as posted
        self.document.status = DocumentStatus.POSTED
        self.document.save()

        # Verify document is posted
        self.assertTrue(self.document.is_posted)

        # In real implementation, there should be database-level triggers
        # preventing modification of posted documents
        # For now, we verify the status
        self.assertFalse(self.document.can_post())
        self.assertFalse(self.document.can_cancel())


@pytest.mark.acceptance
class TestBR_BUS_002_InvoiceAmountsAlwaysPositive(TestCase):
    """
    BR-BUS-002: Invoice amounts are always stored positive

    Given: An Invoice or Bill or Credit Note with entries
    When: entry values are converted to posting splits
    Then: amounts in entries are always stored as positive values;
          the sign for the split is determined by the owner type (customer vs vendor/employee)
    """

    def setUp(self):
        """Set up test data"""
        self.tenant = TenantFactory()
        self.legal_entity = LegalEntityFactory(tenant=self.tenant)
        self.customer = PartyFactory(tenant=self.tenant, roles=[PartyRole.CUSTOMER])
        self.vendor = PartyFactory(tenant=self.tenant, roles=[PartyRole.VENDOR])
        self.currency = CurrencyFactory()
        self.account = AccountFactory(tenant=self.tenant)

    def test_sales_invoice_amounts_are_positive(self):
        """Sales invoice (customer) should have positive amounts"""
        document = AccountingDocumentFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            party=self.customer,
            currency=self.currency,
            document_type=DocumentType.INVOICE,
            direction=DocumentDirection.SALES
        )

        line = DocumentLineFactory(
            document=document,
            account=self.account,
            quantity=Decimal('5.0000'),
            unit_price=Decimal('100.0000')
        )

        # Amounts should be positive
        self.assertGreater(line.subtotal, Decimal('0'))
        self.assertGreater(line.total, Decimal('0'))

    def test_purchase_bill_amounts_are_positive(self):
        """Purchase bill (vendor) should have positive amounts"""
        document = AccountingDocumentFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            party=self.vendor,
            currency=self.currency,
            document_type=DocumentType.BILL,
            direction=DocumentDirection.PURCHASE
        )

        line = DocumentLineFactory(
            document=document,
            account=self.account,
            quantity=Decimal('3.0000'),
            unit_price=Decimal('50.0000')
        )

        # Amounts should be positive
        self.assertGreater(line.subtotal, Decimal('0'))
        self.assertGreater(line.total, Decimal('0'))

    def test_credit_note_amounts_are_positive(self):
        """Credit note should have positive amounts (sign determined by context)"""
        document = AccountingDocumentFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            party=self.customer,
            currency=self.currency,
            document_type=DocumentType.CREDIT_NOTE,
            direction=DocumentDirection.SALES
        )

        line = DocumentLineFactory(
            document=document,
            account=self.account,
            quantity=Decimal('2.0000'),
            unit_price=Decimal('75.0000')
        )

        # Amounts should be positive
        self.assertGreater(line.subtotal, Decimal('0'))
        self.assertGreater(line.total, Decimal('0'))

    def test_quantity_must_be_positive(self):
        """Quantity must be positive"""
        document = AccountingDocumentFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            party=self.customer,
            currency=self.currency
        )

        # Attempt to create line with negative quantity should fail
        with self.assertRaises(Exception):
            DocumentLineFactory(
                document=document,
                account=self.account,
                quantity=Decimal('-5.0000'),
                unit_price=Decimal('100.0000')
            )

    def test_unit_price_cannot_be_negative(self):
        """Unit price cannot be negative"""
        document = AccountingDocumentFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            party=self.customer,
            currency=self.currency
        )

        # Attempt to create line with negative unit price should fail
        with self.assertRaises(Exception):
            DocumentLineFactory(
                document=document,
                account=self.account,
                quantity=Decimal('5.0000'),
                unit_price=Decimal('-100.0000')
            )

    def test_line_total_calculation(self):
        """Line total should be quantity × unit_price"""
        document = AccountingDocumentFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            party=self.customer,
            currency=self.currency
        )

        line = DocumentLineFactory(
            document=document,
            account=self.account,
            quantity=Decimal('10.0000'),
            unit_price=Decimal('25.5000')
        )

        expected_subtotal = Decimal('255.0000')
        self.assertEqual(line.subtotal, expected_subtotal)


@pytest.mark.acceptance
class TestBRTAX003_DiscountOrderingModes(TestCase):
    """
    BR-TAX-003: Discount ordering modes

    Given: An Entry with a discount and a tax
    When: discount_how is applied
    Then:
      - PRETAX: discount on pretax, tax on (pretax - discount)
      - SAMETIME: discount on pretax, tax on pretax
      - POSTTAX: discount on (pretax + tax), tax on pretax
    """

    def setUp(self):
        """Set up test data"""
        self.tenant = TenantFactory()
        self.legal_entity = LegalEntityFactory(tenant=self.tenant)
        self.customer = PartyFactory(tenant=self.tenant, roles=[PartyRole.CUSTOMER])
        self.currency = CurrencyFactory()
        self.account = AccountFactory(tenant=self.tenant)

        self.document = AccountingDocumentFactory(
            tenant=self.tenant,
            legal_entity=self.legal_entity,
            party=self.customer,
            currency=self.currency
        )

    def test_pretax_discount_mode(self):
        """PRETAX: discount applied before tax calculation"""
        from apps.business_documents.models.line import DiscountOrderingMode

        line = DocumentLineFactory(
            document=self.document,
            account=self.account,
            quantity=Decimal('1.0000'),
            unit_price=Decimal('100.0000'),
            discount_percentage=Decimal('10.00'),
            discount_ordering_mode=DiscountOrderingMode.PRETAX,
            tax_rule=None  # Simplified for now
        )

        # Subtotal = 100
        self.assertEqual(line.subtotal, Decimal('100.0000'))
        # Discount = 10% of 100 = 10
        self.assertEqual(line.discount_value, Decimal('10.0000'))

    def test_sametime_discount_mode(self):
        """SAMETIME: discount and tax calculated independently on pretax"""
        from apps.business_documents.models.line import DiscountOrderingMode

        line = DocumentLineFactory(
            document=self.document,
            account=self.account,
            quantity=Decimal('1.0000'),
            unit_price=Decimal('100.0000'),
            discount_percentage=Decimal('10.00'),
            discount_ordering_mode=DiscountOrderingMode.SAMETIME,
            tax_rule=None
        )

        # Subtotal = 100
        self.assertEqual(line.subtotal, Decimal('100.0000'))
        # Discount = 10% of 100 = 10
        self.assertEqual(line.discount_value, Decimal('10.0000'))

    def test_posttax_discount_mode(self):
        """POSTTAX: discount applied after tax"""
        from apps.business_documents.models.line import DiscountOrderingMode

        line = DocumentLineFactory(
            document=self.document,
            account=self.account,
            quantity=Decimal('1.0000'),
            unit_price=Decimal('100.0000'),
            discount_percentage=Decimal('10.00'),
            discount_ordering_mode=DiscountOrderingMode.POSTTAX,
            tax_rule=None
        )

        # Subtotal = 100
        self.assertEqual(line.subtotal, Decimal('100.0000'))
        # Discount = 10% of 100 = 10
        self.assertEqual(line.discount_value, Decimal('10.0000'))
