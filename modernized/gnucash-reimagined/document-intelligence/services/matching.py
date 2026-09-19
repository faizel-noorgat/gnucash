"""Matching service — links documents to parties / accounting docs / bank txns.

Responsibilities:
1. Extract supplier / customer from extraction result
2. Look up matching Party (from business-documents context)
3. Look up matching AccountingDocument (invoice / bill)
4. Look up matching BankTransaction (from accounting-engine context)
5. Create DocumentMatch candidates with confidence scores
6. Auto-accept if confidence is high enough; otherwise route to review
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol, TypedDict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import Document, DocumentExtraction, DocumentMatch, MatchKind, MatchStatus

logger = logging.getLogger(__name__)


class PartyMatch(TypedDict):
    party_id: uuid.UUID
    name: str
    confidence: float


class AccountingDocumentMatch(TypedDict):
    accounting_document_id: uuid.UUID
    document_number: str
    confidence: float


class BankTransactionMatch(TypedDict):
    bank_transaction_id: uuid.UUID
    amount: str
    date: str
    confidence: float


class PartyLookupService(Protocol):
    """Protocol for looking up parties in business-documents context."""

    def find_by_name(self, *, tenant_id: uuid.UUID, name: str) -> list[Partymatch]: ...


class AccountingDocumentLookupService(Protocol):
    """Protocol for looking up accounting documents."""

    def find_unpaid_invoices(
        self, *, tenant_id: uuid.UUID, party_id: uuid.UUID | None
    ) -> list[AccountingDocumentMatch]: ...


class BankTransactionLookupService(Protocol):
    """Protocol for looking up bank transactions."""

    def find_by_amount_and_date(
        self, *, tenant_id: uuid.UUID, amount: str, date: str, window_days: int = 7
    ) -> list[BankTransactionMatch]: ...


class MatchingService:
    """Orchestrates document matching."""

    def __init__(
        self,
        party_lookup: PartyLookupService | None = None,
        accounting_doc_lookup: AccountingDocumentLookupService | None = None,
        bank_txn_lookup: BankTransactionLookupService | None = None,
    ) -> None:
        self.party_lookup = party_lookup
        self.accounting_doc_lookup = accounting_doc_lookup
        self.bank_txn_lookup = bank_txn_lookup
        self.conf = settings.DOCUMENT_INTELLIGENCE

    def run_matching(
        self, document: Document, extraction: DocumentExtraction
    ) -> list[DocumentMatch]:
        """Run matching pipeline on an extracted document.

        Creates DocumentMatch candidates for:
        - Party (supplier / customer)
        - AccountingDocument (existing invoice / bill)
        - BankTransaction (unreconciled bank feed)

        Returns list of created matches.
        """
        if not extraction.extraction_result:
            logger.warning("Cannot match document %s: no extraction result", document.guid)
            return []

        result = extraction.extraction_result
        matches: list[DocumentMatch] = []

        with transaction.atomic():
            # 1. Match party
            if self.party_lookup and result.get("supplier_name"):
                party_matches = self.party_lookup.find_by_name(
                    tenant_id=document.tenant_id,
                    name=result["supplier_name"],
                )
                for pm in party_matches:
                    match = DocumentMatch.objects.create(
                        document=document,
                        extraction=extraction,
                        kind=MatchKind.PARTY,
                        target_party_id=pm["party_id"],
                        confidence=pm["confidence"],
                        evidence={"matched_name": pm["name"]},
                    )
                    matches.append(match)

            # 2. Match accounting document (invoice / bill)
            if self.accounting_doc_lookup and result.get("invoice_number"):
                party_id = matches[0].target_party_id if matches else None
                acct_matches = self.accounting_doc_lookup.find_unpaid_invoices(
                    tenant_id=document.tenant_id,
                    party_id=party_id,
                )
                for am in acct_matches:
                    match = DocumentMatch.objects.create(
                        document=document,
                        extraction=extraction,
                        kind=MatchKind.ACCOUNTING_DOCUMENT,
                        target_accounting_document_id=am["accounting_document_id"],
                        confidence=am["confidence"],
                        evidence={"document_number": am["document_number"]},
                    )
                    matches.append(match)

            # 3. Match bank transaction
            if (
                self.bank_txn_lookup
                and result.get("total_amount")
                and result.get("invoice_date")
            ):
                bank_matches = self.bank_txn_lookup.find_by_amount_and_date(
                    tenant_id=document.tenant_id,
                    amount=result["total_amount"],
                    date=result["invoice_date"],
                )
                for bm in bank_matches:
                    match = DocumentMatch.objects.create(
                        document=document,
                        extraction=extraction,
                        kind=MatchKind.BANK_TRANSACTION,
                        target_bank_transaction_id=bm["bank_transaction_id"],
                        confidence=bm["confidence"],
                        evidence={"amount": bm["amount"], "date": bm["date"]},
                    )
                    matches.append(match)

        # Update document status
        if matches:
            document.status = "matched"
            document.save(update_fields=["status"])

        logger.info(
            "Matching completed for document %s: %d matches",
            document.guid,
            len(matches),
        )
        return matches
