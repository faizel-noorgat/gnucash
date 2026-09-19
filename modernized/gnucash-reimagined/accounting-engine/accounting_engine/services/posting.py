"""
Posting service for journal entries.

Implements ACID-compliant posting logic with:
- Double-entry balance validation (BR-ACCT-001, BR-ACCT-002)
- Fiscal period locking
- Optimistic/pessimistic concurrency control
- Idempotency key enforcement
- Immutable audit trail
"""

import uuid
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounting_engine.models import (
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

    Ensures ACID compliance and accounting invariants.
    """

    @staticmethod
    def post_journal_entry(
        journal_entry: JournalEntry,
        user=None,
        idempotency_key: Optional[str] = None,
    ) -> JournalEntry:
        """
        Post a journal entry with full validation.

        This is a synchronous operation for ACID compliance.
        Uses REPEATABLE READ isolation level.

        Steps:
        1. Check idempotency key
        2. Validate balance (BR-ACCT-001, BR-ACCT-002)
        3. Check fiscal period
        4. Lock and post
        5. Create audit event
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
    ) -> JournalEntry:
        """
        Create and post a journal entry in one atomic operation.

        lines: list of dicts with keys: account, amount, value, memo
        """
        with transaction.atomic():
            # Create journal entry
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
    def create_reversal_entry(
        original_entry: JournalEntry,
        user=None,
        description: Optional[str] = None,
    ) -> JournalEntry:
        """
        Create a reversal entry for a posted journal.

        A reversal entry exactly offsets the original entry.
        """
        if not original_entry.is_posted:
            raise ValidationError("Can only reverse posted journal entries.")

        reversal_desc = description or f"Reversal of: {original_entry.description}"

        # Create reversal lines (opposite signs)
        reversal_lines = []
        for line in original_entry.lines.all():
            reversal_lines.append({
                "account": line.account,
                "amount": -line.amount,
                "value": -line.value,
                "memo": f"Reversal: {line.memo}",
            })

        # Create and post reversal
        return PostingService.create_and_post_journal_entry(
            tenant=original_entry.tenant,
            legal_entity=original_entry.legal_entity,
            date=timezone.now().date(),
            description=reversal_desc,
            lines=reversal_lines,
            transaction_currency=original_entry.transaction_currency,
            user=user,
        )

    @staticmethod
    def void_journal_entry(
        journal_entry: JournalEntry,
        user=None,
        reason: str = "",
    ) -> JournalEntry:
        """
        Void a journal entry by creating a reversal.

        This is the proper way to "delete" a posted journal entry.
        """
        if not journal_entry.is_posted:
            raise ValidationError("Can only void posted journal entries.")

        # Create reversal
        reversal = PostingService.create_reversal_entry(
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
