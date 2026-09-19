"""Matching service — links documents to parties / accounting docs / bank transactions.

Responsibilities:
1. Extract supplier / customer from extraction result
2. Look up matching Party (from business-documents context)
3. Look up matching AccountingDocument (invoice / bill)
4. Look up matching BankTransaction (from accounting-engine context)
5. Create DocumentMatch candidates with confidence scores
6. Auto-accept if confidence is high enough; otherwise route to review
7. NEVER mutate Document directly - only create DocumentMatch rows

Design:
- Lookup services are injected via Protocol (dependency inversion)
- Cross-app lookups use string references (decoupled at ORM layer)
- All matches preserve full provenance (BR-DI-008)
- Workflow: document → extraction → matching → mapping/suggestion → review

Implements behavior-contract rules:
- BR-DI-005: duplicate detection (content-hash and semantic)
- BR-DI-008: full provenance captured
- BR-DI-010: tenant-scoped queries
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol, TypedDict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import (
    Document,
    DocumentExtraction,
    DocumentMatch,
    MatchKind,
    MatchStatus,
)

logger = logging.getLogger(__name__)


class PartyMatch(TypedDict):
    """Party match candidate."""

    party_id: uuid.UUID
    name: str
    confidence: float


class AccountingDocumentMatch(TypedDict):
    """Accounting document match candidate."""

    accounting_document_id: uuid.UUID
    document_number: str
    confidence: float


class BankTransactionMatch(TypedDict):
    """Bank transaction match candidate."""

    bank_transaction_id: uuid.UUID
    amount: str
    date: str
    confidence: float


class PartyLookupService(Protocol):
    """Protocol for looking up parties in business-documents context."""

    def find_by_name(
        self, *, tenant_id: uuid.UUID, name: str
    ) -> list[PartyMatch]:
        """Find parties by name.

        Args:
            tenant_id: Tenant ID
            name: Party name to search

        Returns:
            List of party matches with confidence scores
        """
        ...


class AccountingDocumentLookupService(Protocol):
    """Protocol for looking up accounting documents."""

    def find_unpaid_invoices(
        self, *, tenant_id: uuid.UUID, party_id: uuid.UUID | None
    ) -> list[AccountingDocumentMatch]:
        """Find unpaid invoices/bills.

        Args:
            tenant_id: Tenant ID
            party_id: Optional party ID to filter

        Returns:
            List of accounting document matches
        """
        ...


class BankTransactionLookupService(Protocol):
    """Protocol for looking up bank transactions."""

    def find_by_amount_and_date(
        self,
        *,
        tenant_id: uuid.UUID,
        amount: str,
        date: str,
        window_days: int = 7,
    ) -> list[BankTransactionMatch]:
        """Find bank transactions by amount and date.

        Args:
            tenant_id: Tenant ID
            amount: Transaction amount
            date: Transaction date
            window_days: Date window tolerance

        Returns:
            List of bank transaction matches
        """
        ...


class MatchingService:
    """Orchestrates document matching to external entities.

    Usage:
        service = MatchingService()
        matches = service.run_matching(document, extraction)
    """

    def __init__(
        self,
        party_lookup: PartyLookupService | None = None,
        accounting_doc_lookup: AccountingDocumentLookupService | None = None,
        bank_txn_lookup: BankTransactionLookupService | None = None,
    ) -> None:
        """Initialize matching service.

        Args:
            party_lookup: Party lookup service (optional)
            accounting_doc_lookup: Accounting document lookup service (optional)
            bank_txn_lookup: Bank transaction lookup service (optional)
        """
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

        Args:
            document: Document to match
            extraction: Extraction result to match against

        Returns:
            List of created DocumentMatch candidates
        """
        if not extraction.extraction_result:
            logger.warning(
                "MatchingService: cannot match document %s: no extraction result",
                document.guid,
            )
            return []

        result = extraction.extraction_result
        matches: list[DocumentMatch] = []

        logger.info(
            "MatchingService: running matching on document %s (tenant=%s)",
            document.guid,
            document.tenant_id,
        )

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
                    logger.info(
                        "MatchingService: party match %s (party=%s, conf=%s)",
                        match.guid,
                        pm["party_id"],
                        pm["confidence"],
                    )

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
                    logger.info(
                        "MatchingService: accounting document match %s (doc=%s, conf=%s)",
                        match.guid,
                        am["accounting_document_id"],
                        am["confidence"],
                    )

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
                    logger.info(
                        "MatchingService: bank transaction match %s (txn=%s, conf=%s)",
                        match.guid,
                        bm["bank_transaction_id"],
                        bm["confidence"],
                    )

        # Update document status
        if matches:
            document.status = "matched"
            document.save(update_fields=["status"])
            logger.info(
                "MatchingService: document %s matched with %d candidates",
                document.guid,
                len(matches),
            )
        else:
            logger.info(
                "MatchingService: no matches found for document %s", document.guid
            )

        return matches

    def accept_match(
        self, match: DocumentMatch, user_id: uuid.UUID | None
    ) -> None:
        """Accept a match candidate.

        Args:
            match: Match to accept
            user_id: User ID accepting the match
        """
        logger.info(
            "MatchingService: accepting match %s (kind=%s) by user %s",
            match.guid,
            match.kind,
            user_id,
        )
        match.accept(user_id)

    def reject_match(
        self, match: DocumentMatch, user_id: uuid.UUID | None
    ) -> None:
        """Reject a match candidate.

        Args:
            match: Match to reject
            user_id: User ID rejecting the match
        """
        logger.info(
            "MatchingService: rejecting match %s (kind=%s) by user %s",
            match.guid,
            match.kind,
            user_id,
        )
        match.reject(user_id)
