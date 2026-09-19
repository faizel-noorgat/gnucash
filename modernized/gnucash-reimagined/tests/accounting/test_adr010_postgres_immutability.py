"""
ADR-010 at the database level: PostgreSQL must be the final enforcement boundary.

The golden suite proves the ORM/service layer refuses to mutate posted journals.
These tests deliberately bypass that layer — ``QuerySet.update()``, raw SQL, and
``DELETE`` — so that a failure can only come from the triggers installed by
``apps/accounting/migrations/0003_adr010_posted_immutability.py``.

Every assertion checks for ``DatabaseError``. Django's ``ValidationError`` is
NOT a ``DatabaseError``, so if a model-level guard were doing the work these
tests would fail rather than pass — that is the point.
"""

import pytest
from decimal import Decimal

from django.db import DatabaseError, connection, transaction

from apps.accounting.models import JournalEntry, JournalLine
from apps.accounting.models.journals import TransactionMetadata
from apps.accounting.services.posting import PostingService
from apps.accounting.services.reversal import ReversalService
from tests.accounting.golden.factories import (
    AccountFactory,
    CommodityFactory,
    JournalEntryFactory,
    JournalLineFactory,
    LegalEntityFactory,
    TenantFactory,
)

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _posted_entry():
    """Build a genuinely posted entry via the normal lifecycle.

    draft -> lines -> post. Nothing here constructs a posted row directly,
    because a posted row with no lines is itself a state production code would
    not produce.
    """
    tenant = TenantFactory()
    legal_entity = LegalEntityFactory(tenant=tenant)
    currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)

    entry = JournalEntryFactory(
        tenant=tenant,
        legal_entity=legal_entity,
        transaction_currency=currency,
    )
    debit_account = AccountFactory(
        tenant=tenant, legal_entity=legal_entity, commodity=currency
    )
    credit_account = AccountFactory(
        tenant=tenant, legal_entity=legal_entity, commodity=currency
    )
    JournalLineFactory(
        journal_entry=entry,
        account=debit_account,
        amount=Decimal("100.00"),
        value=Decimal("100.00"),
    )
    JournalLineFactory(
        journal_entry=entry,
        account=credit_account,
        amount=Decimal("-100.00"),
        value=Decimal("-100.00"),
    )

    entry.post()
    entry.refresh_from_db()
    assert entry.is_posted is True
    return entry, debit_account


def _draft_entry():
    tenant = TenantFactory()
    legal_entity = LegalEntityFactory(tenant=tenant)
    currency = CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)
    entry = JournalEntryFactory(
        tenant=tenant,
        legal_entity=legal_entity,
        transaction_currency=currency,
    )
    account = AccountFactory(
        tenant=tenant, legal_entity=legal_entity, commodity=currency
    )
    line = JournalLineFactory(
        journal_entry=entry,
        account=account,
        amount=Decimal("100.00"),
        value=Decimal("100.00"),
    )
    return entry, line


# --------------------------------------------------------------------------
# 1-3: UPDATE of financial facts on posted records
# --------------------------------------------------------------------------

def test_queryset_update_cannot_alter_posted_entry_financial_field():
    """1. QuerySet.update() on a posted entry's financial field is rejected."""
    entry, _ = _posted_entry()

    with pytest.raises(DatabaseError, match="ADR-010"):
        with transaction.atomic():
            JournalEntry.objects.filter(pk=entry.pk).update(
                description="tampered by a data script"
            )

    entry.refresh_from_db()
    assert entry.description != "tampered by a data script"


def test_queryset_update_cannot_alter_posted_line_amount():
    """2a. QuerySet.update() may not change a posted line's amount."""
    entry, _ = _posted_entry()
    line = entry.lines.first()

    with pytest.raises(DatabaseError, match="ADR-010"):
        with transaction.atomic():
            JournalLine.objects.filter(pk=line.pk).update(amount=Decimal("999999.99"))

    line.refresh_from_db()
    assert line.amount != Decimal("999999.99")


def test_queryset_update_cannot_alter_posted_line_account():
    """2b. QuerySet.update() may not re-point a posted line at another account."""
    entry, _ = _posted_entry()
    other_account = AccountFactory(
        tenant=entry.tenant,
        legal_entity=entry.legal_entity,
        commodity=entry.transaction_currency,
    )
    line = entry.lines.first()

    with pytest.raises(DatabaseError, match="ADR-010"):
        with transaction.atomic():
            JournalLine.objects.filter(pk=line.pk).update(account=other_account)


def test_raw_sql_update_cannot_alter_posted_line_value():
    """3. Raw SQL bypassing the ORM entirely is still rejected."""
    entry, _ = _posted_entry()
    line = entry.lines.first()

    with pytest.raises(DatabaseError, match="ADR-010"):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE accounting_journalline SET value = %s WHERE guid = %s",
                    [Decimal("1.00"), line.pk],
                )

    line.refresh_from_db()
    assert line.value != Decimal("1.00")


def test_raw_sql_update_cannot_unpost_a_posted_entry():
    """BR-BUS-001 at the database level: posting is one-way."""
    entry, _ = _posted_entry()

    with pytest.raises(DatabaseError, match="BR-BUS-001"):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE accounting_journalentry SET is_posted = false, status = %s "
                    "WHERE guid = %s",
                    ["draft", entry.pk],
                )

    entry.refresh_from_db()
    assert entry.is_posted is True
    assert entry.status == "posted"


# --------------------------------------------------------------------------
# 4-5: DELETE of posted records
# --------------------------------------------------------------------------

def test_delete_of_posted_entry_is_rejected():
    """4. A posted entry cannot be deleted, even though its lines are gone first."""
    entry, _ = _posted_entry()

    with pytest.raises(DatabaseError, match="ADR-010"):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM accounting_journalentry WHERE guid = %s", [entry.pk]
                )

    assert JournalEntry.objects.filter(pk=entry.pk).exists()


def test_delete_of_posted_line_is_rejected():
    """5. A posted line cannot be deleted."""
    entry, _ = _posted_entry()
    line = entry.lines.first()

    with pytest.raises(DatabaseError, match="ADR-010"):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM accounting_journalline WHERE guid = %s", [line.pk]
                )

    assert JournalLine.objects.filter(pk=line.pk).exists()


def test_queryset_delete_of_posted_entry_is_rejected():
    """4b. ORM-level bulk delete of a posted entry does not succeed.

    Unlike the raw-SQL case above, this asserts only ``DatabaseError`` and not
    the ADR-010 message, because on the ORM path the refusal can come from
    either of two places and which one wins is ordering-dependent:

    1. the trigger (the collector nullifies FKs before deleting, tripping the
       UPDATE arm), or
    2. an unrelated defect - ``ImmutablePostedJournalEntry`` /
       ``ImmutablePostedJournalLine`` declare ``managed = False`` and have no
       tables, yet Django's deletion collector still follows their relations
       and dies with 'relation ... does not exist'.

    Either way the delete is refused, which is the invariant that matters. The
    raw-SQL test is the one that proves the trigger specifically. Once (2) is
    fixed, this test can assert the ADR-010 message directly.
    """
    entry, _ = _posted_entry()

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            JournalEntry.objects.filter(pk=entry.pk).delete()

    assert JournalEntry.objects.filter(pk=entry.pk).exists()


def test_new_line_cannot_be_added_to_a_posted_entry():
    """A BEFORE UPDATE/DELETE-only trigger would miss this: it is an INSERT.

    Uses bulk_create because it skips Model.save()/full_clean(), so the ORM's
    own guard is bypassed and only the database can stop it. That is also a
    real bypass path worth defending against.
    """
    entry, _ = _posted_entry()
    account = entry.lines.first().account

    with pytest.raises(DatabaseError, match="ADR-010"):
        with transaction.atomic():
            JournalLine.objects.bulk_create([
                JournalLine(
                    journal_entry=entry,
                    account=account,
                    amount=Decimal("50.00"),
                    value=Decimal("50.00"),
                )
            ])

    assert entry.lines.count() == 2


# --------------------------------------------------------------------------
# 6: operational metadata stays mutable
# --------------------------------------------------------------------------

def test_reconciliation_metadata_remains_mutable_after_posting():
    """6a. Reconciliation happens AFTER posting - it must not be frozen."""
    entry, _ = _posted_entry()
    line = entry.lines.first()

    assert line.reconcile_status == "NOT_CLEARED"

    with transaction.atomic():
        JournalLine.objects.filter(pk=line.pk).update(reconcile_status="RECONCILED")

    line.refresh_from_db()
    assert line.reconcile_status == "RECONCILED"


def test_online_id_remains_mutable_after_posting():
    """6b. Bank-matching metadata is operational."""
    entry, _ = _posted_entry()
    line = entry.lines.first()

    with transaction.atomic():
        JournalLine.objects.filter(pk=line.pk).update(online_id="BANK-REF-123")

    line.refresh_from_db()
    assert line.online_id == "BANK-REF-123"


def test_transaction_metadata_remains_mutable_after_posting():
    """6c. Review state / comments / external refs live in a separate table."""
    entry, _ = _posted_entry()

    metadata = TransactionMetadata.objects.create(journal_entry=entry)
    metadata.comments = "Reviewed by the accountant on Monday."
    metadata.review_status = "APPROVED"
    metadata.external_reference = "EXT-42"
    metadata.save()

    metadata.refresh_from_db()
    assert metadata.comments == "Reviewed by the accountant on Monday."
    assert metadata.review_status == "APPROVED"


# --------------------------------------------------------------------------
# 7: drafts remain fully editable
# --------------------------------------------------------------------------

def test_draft_entry_and_line_remain_editable():
    """7. Immutability must not leak backwards onto unposted data."""
    entry, line = _draft_entry()

    with transaction.atomic():
        JournalEntry.objects.filter(pk=entry.pk).update(description="still a draft")
        JournalLine.objects.filter(pk=line.pk).update(amount=Decimal("250.00"))

    entry.refresh_from_db()
    line.refresh_from_db()
    assert entry.description == "still a draft"
    assert line.amount == Decimal("250.00")

    # Raw SQL for the delete: Django's collector is broken by the unrelated
    # managed = False models, which has nothing to do with draft editability.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM accounting_journalline WHERE guid = %s", [line.pk]
            )

    assert entry.lines.count() == 0


def test_draft_entry_can_be_deleted():
    """7b. Deleting a draft entry is normal data management.

    Uses raw SQL for the same reason as the test above.
    """
    entry, _ = _draft_entry()

    with transaction.atomic():
        with connection.cursor() as cursor:
            # Lines first: the FK is not ON DELETE CASCADE, and Django is not
            # doing the ordering for us here.
            cursor.execute(
                "DELETE FROM accounting_journalline WHERE journal_entry_id = %s",
                [entry.pk],
            )
            cursor.execute(
                "DELETE FROM accounting_journalentry WHERE guid = %s", [entry.pk]
            )

    assert not JournalEntry.objects.filter(pk=entry.pk).exists()


# --------------------------------------------------------------------------
# 8: corrections still work, because they create new records
# --------------------------------------------------------------------------

def test_reversal_workflow_still_succeeds_on_a_posted_entry():
    """8a. Corrections create NEW rows; they never mutate the posted original."""
    entry, _ = _posted_entry()
    original_line_amounts = sorted(l.amount for l in entry.lines.all())

    with transaction.atomic():
        reversal = ReversalService.create_reversal_entry(
            original_entry=entry,
            description="Correcting the March invoice",
        )

    assert reversal.pk != entry.pk
    assert reversal.is_posted is True

    entry.refresh_from_db()
    assert entry.is_posted is True
    assert sorted(l.amount for l in entry.lines.all()) == original_line_amounts


def test_void_workflow_still_succeeds_on_a_posted_entry():
    """8b. Voiding posts a reversal and leaves the original intact."""
    entry, _ = _posted_entry()

    with transaction.atomic():
        reversal = PostingService.void_journal_entry(entry, reason="duplicate entry")

    assert reversal.pk != entry.pk

    entry.refresh_from_db()
    assert entry.is_posted is True
    assert entry.status == "posted"
    assert JournalEntry.objects.filter(pk=entry.pk).exists()
