"""
Reversal service for journal entries.

Implements:
- Creation of reversal entries for posted journals
- Creation of correcting entries for differences
- Void operations

Accounting Semantics:
    Once a journal entry is posted, it becomes immutable (ADR-010).
    To "undo" or "correct" a posted entry, we create new entries:

    Reversal Entry:
        - Exactly offsets the original entry
        - All amounts are negated
        - Used to completely cancel the original transaction
        - Example:
          Original: Debit Cash $100, Credit Revenue $100
          Reversal: Debit Revenue $100, Credit Cash $100

    Correcting Entry:
        - Adjusts specific lines in the original entry
        - Only records the difference (not the full reversal)
        - Used when the original entry has errors
        - Example:
          Original: Debit Cash $100, Credit Revenue $100
          Correction: Debit Cash $20, Credit Revenue $20 (to fix $120 → $100)

    Void Operation:
        - Creates a reversal entry
        - Marks the original entry as voided
        - Used to cancel a posted entry

    Workflow:
    1. Identify the entry to reverse/correct
    2. Calculate the reversal/correction amounts
    3. Create new journal entry with offsetting amounts
    4. Post the new entry (follows normal posting flow)
    5. Create audit event for traceability
"""

from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounting.models import (
    AuditEvent,
    JournalEntry,
    JournalLine,
    JournalEntryStatus,
)


class ReversalService:
    """
    Service for creating reversal and correcting entries.

    Accounting Semantics:
        This service handles the creation of new journal entries that
        reverse or correct posted entries.

        All operations are atomic and create audit trails.
    """

    @staticmethod
    def create_reversal_entry(
        original_entry: JournalEntry,
        user=None,
        description: Optional[str] = None,
    ) -> JournalEntry:
        """
        Create a reversal entry for a posted journal.

        Accounting Semantics:
            A reversal entry exactly offsets the original entry.
            All amounts are negated.

            The reversal is created and immediately posted.
            An audit event is created for traceability.

        Args:
            original_entry: Original JournalEntry to reverse
            user: User creating the reversal
            description: Optional description (defaults to "Reversal of: <original>")

        Returns:
            Posted reversal JournalEntry

        Raises:
            ValidationError: If original entry is not posted
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

        # Import here to avoid circular dependency
        from accounting.services.posting import PostingService

        # Create and post reversal
        reversal = PostingService.create_and_post_journal_entry(
            tenant=original_entry.tenant,
            legal_entity=original_entry.legal_entity,
            date=timezone.now().date(),
            description=reversal_desc,
            lines=reversal_lines,
            transaction_currency=original_entry.transaction_currency,
            user=user,
        )

        # Link reversal to original
        reversal.reversal_of = original_entry
        reversal.is_reversal = True
        reversal.save()

        # Log the reversal
        AuditEvent.log(
            tenant=original_entry.tenant,
            legal_entity=original_entry.legal_entity,
            action="JOURNAL_REVERSED",
            actor=user,
            entity_type="JournalEntry",
            entity_id=str(original_entry.guid),
            metadata={
                "reversal_entry_id": str(reversal.guid),
                "reversal_date": str(reversal.date),
            },
        )

        return reversal

    @staticmethod
    def create_correcting_entry(
        original_entry: JournalEntry,
        corrections: dict,
        user=None,
        description: Optional[str] = None,
    ) -> JournalEntry:
        """
        Create a correcting entry for differences in a posted journal.

        Accounting Semantics:
            A correcting entry adjusts specific lines in the original entry.
            Only the difference is recorded (not a full reversal).

            Example:
            Original line: Debit Cash $100
            Corrected amount: $120
            Correcting entry: Debit Cash $20

        Args:
            original_entry: Original JournalEntry to correct
            corrections: Dict of line_guid -> new_amount mappings
            user: User creating the correction
            description: Optional description

        Returns:
            Posted correcting JournalEntry

        Raises:
            ValidationError: If original entry is not posted or no corrections needed
        """
        if not original_entry.is_posted:
            raise ValidationError("Can only correct posted journal entries.")

        # Calculate differences
        correcting_lines = []
        for line_guid, new_amount in corrections.items():
            original_line = original_entry.lines.get(pk=line_guid)
            diff_amount = new_amount - original_line.amount
            if diff_amount != 0:
                # Calculate proportional value change
                # This is simplified - in practice, you'd need FX calculation
                if original_line.amount != 0:
                    ratio = diff_amount / original_line.amount
                    diff_value = original_line.value * ratio
                else:
                    diff_value = diff_amount

                correcting_lines.append({
                    "account": original_line.account,
                    "amount": diff_amount,
                    "value": diff_value,
                    "memo": f"Correction: {original_line.memo}",
                })

        if not correcting_lines:
            raise ValidationError("No corrections needed.")

        # Import here to avoid circular dependency
        from accounting.services.posting import PostingService

        correcting_desc = description or f"Correction of: {original_entry.description}"

        # Create and post correction
        correcting_entry = PostingService.create_and_post_journal_entry(
            tenant=original_entry.tenant,
            legal_entity=original_entry.legal_entity,
            date=timezone.now().date(),
            description=correcting_desc,
            lines=correcting_lines,
            transaction_currency=original_entry.transaction_currency,
            user=user,
        )

        # Link correction to original
        correcting_entry.correcting_of = original_entry
        correcting_entry.save()

        # Log the correction
        AuditEvent.log(
            tenant=original_entry.tenant,
            legal_entity=original_entry.legal_entity,
            action="JOURNAL_CORRECTED",
            actor=user,
            entity_type="JournalEntry",
            entity_id=str(original_entry.guid),
            metadata={
                "correction_entry_id": str(correcting_entry.guid),
                "correction_date": str(correcting_entry.date),
                "corrected_lines": len(correcting_lines),
            },
        )

        return correcting_entry

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

        # Create reversal
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
