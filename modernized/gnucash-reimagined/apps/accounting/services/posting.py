"""
Posting service for journal entries.

Implements ACID-compliant posting logic with:
- Double-entry balance validation (BR-ACCT-001, BR-ACCT-002)
- Fiscal period locking
- Optimistic/pessimistic concurrency control
- Idempotency key enforcement
- Immutable audit trail

Accounting Semantics:
    Posting is the process of making a journal entry permanent and immutable.
    Once posted, a journal entry cannot be modified (ADR-010).

    The posting process ensures:
    1. The journal entry is balanced (debits = credits)
    2. The fiscal period is open for posting
    3. Idempotency keys prevent duplicate posting
    4. Audit trail is created for compliance

    Posting Flow:
    1. Validate balance (BR-ACCT-001, BR-ACCT-002)
    2. Check fiscal period (must be OPEN)
    3. Check idempotency key (prevent duplicates)
    4. Lock journal entry (pessimistic locking)
    5. Mark as posted (status=POSTED, is_posted=True)
    6. Create audit event (immutable record)
    7. Return posted entry

    Concurrency Control:
    Pessimistic locking (SELECT FOR UPDATE) ensures that concurrent
    posting attempts are serialized. This prevents race conditions
    where the same journal entry could be posted twice.
"""

import uuid
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounting.models import (
    Account,
    AuditEvent,
    FiscalPeriod,
    JournalEntry,
    JournalLine,
    JournalEntryStatus,
)


class PostingService:
    """
    Service for posting journal entries.

    Accounting Semantics:
        This service ensures ACID compliance and accounting invariants
        during the posting process.

        All posting operations are atomic - either the entire operation
        succeeds, or it fails completely. This ensures data integrity.

        Key Invariants:
        - Journal entries must balance (BR-ACCT-001)
        - Balance checked per commodity (BR-ACCT-002)
        - Fiscal period must be OPEN
        - Idempotency keys prevent duplicates
        - Posted entries are immutable (ADR-010)
    """

    @staticmethod
    def post_journal_entry(
        journal_entry: JournalEntry,
        user=None,
        idempotency_key: Optional[str] = None,
    ) -> JournalEntry:
        """
        Post a journal entry with full validation.

        Accounting Semantics:
            This is a synchronous operation for ACID compliance.
            Uses REPEATABLE READ isolation level.

            Steps:
            1. Check idempotency key (prevent duplicates)
            2. Validate balance (BR-ACCT-001, BR-ACCT-002)
            3. Check fiscal period (must be OPEN)
            4. Lock and post (pessimistic locking)
            5. Create audit event (immutable record)

        Args:
            journal_entry: JournalEntry to post
            user: User performing the post action
            idempotency_key: Optional key to prevent duplicate posting

        Returns:
            Posted JournalEntry

        Raises:
            ValidationError: If validation fails or entry already posted
        """
        # Check if already posted
        if journal_entry.is_posted:
            raise ValidationError("Journal entry is already posted.")

        # Check idempotency
        if idempotency_key:
            existing = JournalEntry.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                if existing.guid == journal_entry.guid:
                    return journal_entry  # Same entry, return it
                raise ValidationError(
                    f"Idempotency key {idempotency_key} already used for another entry."
                )

        # Validate balance
        if not journal_entry.is_balanced:
            raise ValidationError("Cannot post unbalanced journal entry.")

        # Check fiscal period
        period = FiscalPeriod.get_period_for_date(
            journal_entry.tenant,
            journal_entry.legal_entity,
            journal_entry.date,
        )
        if period and not period.is_open:
            raise ValidationError(
                f"Cannot post to {period.status} fiscal period {period.name}."
            )

        # Atomic posting with pessimistic locking
        with transaction.atomic():
            # Lock the journal entry
            locked_je = JournalEntry.objects.select_for_update().get(pk=journal_entry.pk)

            # Double-check it's not posted (race condition protection)
            if locked_je.is_posted:
                raise ValidationError("Journal entry was posted by another transaction.")

            # Mark as posted
            locked_je.status = JournalEntryStatus.POSTED
            locked_je.is_posted = True
            locked_je.posted_at = timezone.now()
            locked_je.posted_by = user
            if idempotency_key:
                locked_je.idempotency_key = idempotency_key
            locked_je.save()

            # Create audit event
            AuditEvent.log(
                tenant=locked_je.tenant,
                legal_entity=locked_je.legal_entity,
                action="JOURNAL_POSTED",
                actor=user,
                entity_type="JournalEntry",
                entity_id=str(locked_je.guid),
                metadata={
                    "date": str(locked_je.date),
                    "description": locked_je.description,
                    "line_count": locked_je.lines.count(),
                    "total_amount": str(sum(
                        abs(line.amount) for line in locked_je.lines.all()
                    )),
                },
            )

        return locked_je

    @staticmethod
    def create_and_post_journal_entry(
        tenant,
        legal_entity,
        date,
        description: str,
        lines: list[dict],
        transaction_currency,
        user=None,
        idempotency_key: Optional[str] = None,
        reference: str = "",
        num: str = "",
        source_document=None,
        reversal_of=None,
        is_reversal: bool = False,
        correcting_of=None,
    ) -> JournalEntry:
        """
        Create and post a journal entry in one atomic operation.

        Accounting Semantics:
            This is a convenience method that creates a journal entry
            with all its lines and immediately posts it.

            The entire operation is atomic - either everything succeeds,
            or everything fails.

        Args:
            tenant: Multi-tenant isolation
            legal_entity: Legal entity context
            date: Transaction date
            description: Narration/description
            lines: List of dicts with keys: account, amount, value, memo
            transaction_currency: Currency for the transaction
            user: User performing the action
            idempotency_key: Optional key to prevent duplicates
            reference: External reference number
            num: Entry number
            source_document: Linked business document

        Returns:
            Posted JournalEntry
        """
        with transaction.atomic():
            # Create journal entry.
            # The reversal/correction links are passed in HERE rather than being
            # attached afterwards: this method posts the entry before it
            # returns, and ADR-010 makes a posted entry immutable, so a
            # subsequent `entry.reversal_of = ...; entry.save()` is rejected by
            # the database trigger.
            journal_entry = JournalEntry.objects.create(
                date=date,
                description=description,
                reference=reference,
                num=num,
                transaction_currency=transaction_currency,
                tenant=tenant,
                legal_entity=legal_entity,
                source_document=source_document,
                idempotency_key=idempotency_key,
                reversal_of=reversal_of,
                is_reversal=is_reversal,
                correcting_of=correcting_of,
            )

            # Create journal lines
            for line_data in lines:
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account=line_data["account"],
                    amount=line_data["amount"],
                    value=line_data["value"],
                    memo=line_data.get("memo", ""),
                )

            # Post immediately
            return PostingService.post_journal_entry(
                journal_entry=journal_entry,
                user=user,
                idempotency_key=idempotency_key,
            )

    @staticmethod
    def void_journal_entry(
        journal_entry: JournalEntry,
        user=None,
        reason: str = "",
    ) -> JournalEntry:
        """
        Void a journal entry by creating a reversal.

        Accounting Semantics:
            This is the proper way to "delete" a posted journal entry.
            A reversal entry is created that exactly offsets the original.

            The original entry remains in the system (audit trail),
            but its effect is cancelled by the reversal.

        Args:
            journal_entry: JournalEntry to void
            user: User performing the void action
            reason: Reason for voiding

        Returns:
            Reversal JournalEntry

        Raises:
            ValidationError: If entry is not posted
        """
        if not journal_entry.is_posted:
            raise ValidationError("Can only void posted journal entries.")

        # Create reversal.
        # NOTE: `create_reversal_entry` lives on ReversalService, not on
        # PostingService. This previously read `PostingService.create_reversal_entry`
        # and raised AttributeError on every call, so voiding a posted entry never
        # worked. Imported locally because reversal.py imports PostingService in
        # turn, and a module-level import here would be circular.
        from apps.accounting.services.reversal import ReversalService

        reversal = ReversalService.create_reversal_entry(
            original_entry=journal_entry,
            user=user,
            description=f"Void: {journal_entry.description}",
        )

        # Log the void action
        AuditEvent.log(
            tenant=journal_entry.tenant,
            legal_entity=journal_entry.legal_entity,
            action="JOURNAL_VOIDED",
            actor=user,
            entity_type="JournalEntry",
            entity_id=str(journal_entry.guid),
            metadata={
                "reason": reason,
                "reversal_entry_id": str(reversal.guid),
            },
        )

        return reversal
