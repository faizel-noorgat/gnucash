"""
Document posting service - handles posting documents to accounting engine

Integrates directly with apps.accounting.services.posting.PostingService
to ensure atomic transaction execution.
"""
from django.db import transaction
from typing import TYPE_CHECKING

from apps.business_documents.models import (
    AccountingDocument,
    DocumentDirection,
)

if TYPE_CHECKING:
    # Accounting models are resolved at runtime via apps.get_model() inside each
    # method, to avoid a cross-app import cycle. These imports exist only so the
    # string return annotations below resolve for type checkers.
    from apps.accounting.models import Account, JournalEntry

# JournalEntry.num is 50 wide while AccountingDocument.document_number is 100,
# and JournalLine.memo is 1024 wide while DocumentLine.description is an
# unbounded TextField. Both engine models run full_clean() on save, so an
# over-long value would abort the posting rather than truncate silently.
_MAX_ENTRY_NUM = 50
_MAX_MEMO = 1024


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

        Builds a balanced journal entry from the document's lines and hands it
        to the accounting engine's PostingService, which owns creation, balance
        validation and the posting transition. The document itself is left
        untouched: marking it posted is a separate one-way transition the caller
        performs with ``document.mark_posted(user, journal_entry)``, exactly as
        the legacy view did.

        Args:
            document: The accounting document to post
            user: The user performing the posting

        Returns:
            The created JournalEntry, already posted

        Raises:
            ValueError: If document cannot be posted or is invalid
        """
        # Validate document
        if document.is_posted:
            raise ValueError("Document has already been posted")

        if not document.can_post():
            raise ValueError(f"Document in {document.status} status cannot be posted")

        # Import here: the accounting app imports business_documents models, so
        # a module-level import would close a cycle.
        from apps.accounting.services.posting import PostingService

        journal_entry = PostingService.create_and_post_journal_entry(
            tenant=document.tenant,
            legal_entity=document.legal_entity,
            date=document.document_date,
            description=f"{document.get_document_type_display()} {document.document_number}",
            lines=self._build_journal_lines(document),
            transaction_currency=document.currency,
            user=user,
            reference=document.reference_number,
            num=document.document_number[:_MAX_ENTRY_NUM],
            source_document=document,
        )

        return journal_entry

    def _build_journal_lines(self, document: AccountingDocument) -> list[dict]:
        """
        Convert the document's lines into accounting-engine line dicts.

        BR-BUS-002: document line amounts are always stored positive; the sign
        for the split is carried by the entry, not by the document. So the
        stored ``doc_line.total`` is never negated in place - each document line
        becomes a pair of splits, and the debit/credit direction is expressed by
        which side takes ``+total`` and which takes ``-total``. That is the
        engine's own convention (see
        tests/accounting/golden/test_br_bus_001_002.py: a sales invoice debits AR
        positive and credits revenue negative).

        Only the settlement account the direction actually needs is resolved: a
        sales invoice posts AR and must not require an AP account to exist, and
        vice versa.
        """
        if document.direction == DocumentDirection.SALES:
            # Sales: debit AR, credit the line's income account.
            settlement_account = self._get_receivable_account(document)
            settlement_on_debit_side = True
        elif document.direction == DocumentDirection.PURCHASE:
            # Purchase: debit the line's expense account, credit AP.
            settlement_account = self._get_payable_account(document)
            settlement_on_debit_side = False
        else:
            raise ValueError(f"Unknown document direction: {document.direction}")

        lines = []
        for doc_line in document.lines.all():
            amount = doc_line.total
            memo = doc_line.description[:_MAX_MEMO]

            if settlement_on_debit_side:
                lines.append(self._journal_line(settlement_account, amount, memo))
                lines.append(self._journal_line(doc_line.account, -amount, memo))
            else:
                lines.append(self._journal_line(doc_line.account, amount, memo))
                lines.append(self._journal_line(settlement_account, -amount, memo))

        return lines

    @staticmethod
    def _journal_line(account: 'Account', amount, memo: str) -> dict:
        """
        Build one split for PostingService.create_and_post_journal_entry.

        ``amount`` is in the account's commodity and ``value`` in the
        transaction currency; documents are single-currency here, so the two
        are equal.
        """
        return {
            "account": account,
            "amount": amount,
            "value": amount,
            "memo": memo,
        }

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
