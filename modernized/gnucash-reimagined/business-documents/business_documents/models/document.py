"""
AccountingDocument model - unified entity for invoices, bills, credit notes
"""
from django.db import models
from django.conf import settings
import uuid
from decimal import Decimal


class DocumentDirection(models.TextChoices):
    """Direction of the document (sales or purchase)"""
    SALES = 'SALES', 'Sales'
    PURCHASE = 'PURCHASE', 'Purchase'


class DocumentType(models.TextChoices):
    """Type of accounting document"""
    INVOICE = 'INVOICE', 'Invoice'
    BILL = 'BILL', 'Bill'
    CREDIT_NOTE = 'CREDIT_NOTE', 'Credit Note'
    DEBIT_NOTE = 'DEBIT_NOTE', 'Debit Note'


class DocumentStatus(models.TextChoices):
    """Status of the document in its lifecycle"""
    DRAFT = 'DRAFT', 'Draft'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    POSTED = 'POSTED', 'Posted'
    CANCELLED = 'CANCELLED', 'Cancelled'


class AccountingDocument(models.Model):
    """
    Unified accounting document entity for invoices, bills, credit notes.

    Key Behaviors:
    - Draft documents may be incomplete/unbalanced
    - Posting creates JournalEntry in Accounting Engine
    - Posted documents cannot be modified (only corrected via reversal/credit note)
    """
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'identity.Tenant',
        on_delete=models.CASCADE,
        related_name='accounting_documents',
        db_index=True
    )
    legal_entity = models.ForeignKey(
        'identity.LegalEntity',
        on_delete=models.CASCADE,
        related_name='accounting_documents',
        db_index=True
    )

    # Document identification
    document_number = models.CharField(max_length=100, blank=True, db_index=True)
    reference_number = models.CharField(max_length=100, blank=True, help_text="External reference")

    # Document type and direction
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    direction = models.CharField(max_length=10, choices=DocumentDirection.choices)

    # Counterparty
    party = models.ForeignKey(
        Party,
        on_delete=models.CASCADE,
        related_name='accounting_documents',
        db_index=True
    )

    # Dates
    document_date = models.DateField(help_text="Date on the document")
    due_date = models.DateField(null=True, blank=True, help_text="Payment due date")

    # Status
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.DRAFT
    )

    # Currency and amounts
    currency = models.ForeignKey(
        'accounting.Currency',
        on_delete=models.PROTECT,
        related_name='documents'
    )
    subtotal = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Sum of line items before tax"
    )
    tax_total = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Total tax amount"
    )
    discount_total = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Total discount amount"
    )
    total = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Total amount including tax and discount"
    )

    # Payment terms
    payment_terms = models.ForeignKey(
        'accounting.PaymentTerm',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )

    # Posting information
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_documents'
    )
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_documents'
    )

    # Notes and description
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True, help_text="Terms and conditions")

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_documents'
    )
    version = models.PositiveIntegerField(default=1, help_text="Optimistic concurrency version")

    class Meta:
        db_table = 'business_documents_accounting_document'
        verbose_name = 'Accounting Document'
        verbose_name_plural = 'Accounting Documents'
        ordering = ['-document_date', '-created_at']
        unique_together = [
            ['tenant', 'document_number'],
        ]
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'party']),
            models.Index(fields=['tenant', 'document_date']),
            models.Index(fields=['tenant', 'document_type']),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} {self.document_number or self.guid}"

    @property
    def is_posted(self) -> bool:
        """Check if document has been posted"""
        return self.status == DocumentStatus.POSTED

    @property
    def is_draft(self) -> bool:
        """Check if document is in draft status"""
        return self.status == DocumentStatus.DRAFT

    def can_post(self) -> bool:
        """Check if document can be posted"""
        return self.status in [DocumentStatus.APPROVED, DocumentStatus.DRAFT]

    def can_approve(self) -> bool:
        """Check if document can be approved"""
        return self.status == DocumentStatus.PENDING_APPROVAL

    def can_cancel(self) -> bool:
        """Check if document can be cancelled"""
        return self.status in [DocumentStatus.DRAFT, DocumentStatus.PENDING_APPROVAL]

    def mark_posted(self, user, journal_entry):
        """
        Mark document as posted (one-way operation).

        BR-BUS-001: Invoice posting is one-way - once posted, cannot post again.
        """
        if self.is_posted:
            raise ValueError("Document has already been posted")

        self.status = DocumentStatus.POSTED
        self.posted_at = timezone.now()
        self.posted_by = user
        self.journal_entry = journal_entry
        self.save()
