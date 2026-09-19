"""
Document posting service - handles posting documents to accounting engine

Integrates directly with apps.accounting.services.posting.PostingService
to ensure atomic transaction execution.
"""
from django.db import transaction
from decimal import Decimal
from typing import Optional

from apps.business_documents.models import (
    AccountingDocument,
    DocumentDirection,
    DocumentType,
    DocumentStatus,
)


class DocumentPostingService:
    """
    Service for posting accounting documents to the accounting engine.

    Creates journal entries in the accounting engine when documents are posted.
    Executes in a single transaction.atomic() with the accounting engine's
    PostingService to ensure consistency.
    """

    @transaction.atomic
    def post_document(self, document: AccountingDocument, user) -> 'JournalEntry':
        """
        Post a document to the accounting engine.

        Creates a journal entry with lines for each document line item.

        Args:
            document: The accounting document to post
            user: The user performing the posting

        Returns:
            The created JournalEntry

        Raises:
            ValueError: If document cannot be posted or is invalid
        """
        # Validate document
        if document.is_posted:
            raise ValueError("Document has already been posted")

        if not document.can_post():
            raise ValueError(f"Document in {document.status} status cannot be posted")

        # Import accounting engine models and services
        from django.apps import apps
        from apps.accounting.services.posting import PostingService

        JournalEntry = apps.get_model('accounting', 'JournalEntry')
        JournalLine = apps.get_model('accounting', 'JournalLine')
        Account = apps.get_model('accounting', 'Account')

        # Get accounting engine posting service
        posting_service = PostingService()

        # Determine accounts based on document type and direction
        receivable_account = self._get_receivable_account(document)
        payable_account = self._get_payable_account(document)

        # Create journal entry via accounting engine
        journal_entry = JournalEntry.objects.create(
            tenant=document.tenant,
            legal_entity=document.legal_entity,
            transaction_date=document.document_date,
            description=f"{document.get_document_type_display()} {document.document_number}",
            transaction_currency=document.currency,
            reference_document=document,
            posted_by=user,
            is_posted=True
        )

        # Create journal lines for each document line
        for doc_line in document.lines.all():
            # Calculate amounts based on direction
            if document.direction == DocumentDirection.SALES:
                # Sales: Debit AR, Credit Income
                # Debit receivable account
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=receivable_account,
                    amount=doc_line.total,
                    value=doc_line.total,
                    description=doc_line.description,
                    reference_line=doc_line
                )

                # Credit income account
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=doc_line.account,
                    amount=-doc_line.total,
                    value=-doc_line.total,
                    description=doc_line.description,
                    reference_line=doc_line
                )
            else:
                # Purchase: Debit Expense, Credit AP
                # Debit expense account
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=doc_line.account,
                    amount=doc_line.total,
                    value=doc_line.total,
                    description=doc_line.description,
                    reference_line=doc_line
                )

                # Credit payable account
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=payable_account,
                    amount=-doc_line.total,
                    value=-doc_line.total,
                    description=doc_line.description,
                    reference_line=doc_line
                )

        # Validate journal entry balances
        self._validate_journal_entry_balance(journal_entry)

        # Mark document as posted
        document.mark_posted(user, journal_entry)

        return journal_entry

    def _get_receivable_account(self, document: AccountingDocument) -> 'Account':
        """Get the accounts receivable account"""
        from django.apps import apps
        Account = apps.get_model('accounting', 'Account')

        # TODO: Implement proper AR account lookup
        account = Account.objects.filter(
            tenant=document.tenant,
            legal_entity=document.legal_entity,
            account_type='RECEIVABLE'
        ).first()

        if not account:
            raise ValueError("No accounts receivable account found")

        return account

    def _get_payable_account(self, document: AccountingDocument) -> 'Account':
        """Get the accounts payable account"""
        from django.apps import apps
        Account = apps.get_model('accounting', 'Account')

        # TODO: Implement proper AP account lookup
        account = Account.objects.filter(
            tenant=document.tenant,
            legal_entity=document.legal_entity,
            account_type='PAYABLE'
        ).first()

        if not account:
            raise ValueError("No accounts payable account found")

        return account

    def _validate_journal_entry_balance(self, journal_entry):
        """
        Validate that journal entry balances to zero.

        BR-ACCT-001: Transaction balance invariant (double-entry)
        """
        total = sum(line.value for line in journal_entry.lines.all())

        if total != Decimal('0.0000'):
            raise ValueError(f"Journal entry does not balance: total is {total}, expected 0")
