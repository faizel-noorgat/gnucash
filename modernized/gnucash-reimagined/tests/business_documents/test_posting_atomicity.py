"""
Fault-injection proof of the atomic posting boundary.

``DocumentPostingService.post_document()`` posts a journal entry through the
accounting engine and then marks the document posted, both inside a single
``transaction.atomic()``. Until now that guarantee was asserted only by
construction - the acceptance suite exercises the success path and the
already-posted guard, but never a failure *partway through*.

The tests here run under ``django_db(transaction=True)`` on purpose. With
pytest's default database access a test runs inside a test-managed atomic
block, so ``post_document()``'s ``atomic()`` degrades to a SAVEPOINT and
"rolled back" means "undid work that was never committed anyway". The claim
under test is that nothing is left *committed*, so the transaction has to be a
real one: PostgreSQL BEGIN, then a real ROLLBACK.

No production code is modified for this, and no bypass is added. The fault is
injected by patching an application boundary - ``AuditEvent.log`` - which is
the last step ``post_document()`` performs before it returns.
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.auth import get_user_model

from apps.accounting.models import AuditEvent, JournalEntry
from apps.accounting.models.audit import AuditAction
from apps.business_documents.models import (
    AccountingDocument,
    DocumentDirection,
    DocumentStatus,
    DocumentType,
    PartyRole,
)
from apps.business_documents.services.posting import DocumentPostingService
from tests.business_documents.factories import (
    AccountFactory,
    AccountingDocumentFactory,
    CurrencyFactory,
    DocumentLineFactory,
    LegalEntityFactory,
    PartyFactory,
    TenantFactory,
)

pytestmark = pytest.mark.django_db(transaction=True)


class InjectedPostingError(RuntimeError):
    """Raised by the test to abort a posting after the ledger write."""


@pytest.fixture
def posting_fixture():
    """A draft invoice that is ready to post, plus the actor to post it as.

    Mirrors the setup in tests/business_documents/test_acceptance.py: the
    document needs a settlement account of the type its direction requires, and
    every tenant-scoped row has to belong to the same tenant.
    """
    tenant = TenantFactory()
    legal_entity = LegalEntityFactory(tenant=tenant)
    party = PartyFactory(tenant=tenant, roles=[PartyRole.CUSTOMER])
    currency = CurrencyFactory(tenant=tenant)

    income_account = AccountFactory(
        tenant=tenant,
        legal_entity=legal_entity,
        commodity=currency,
        account_type='INCOME',
    )
    # _get_receivable_account raises if no RECEIVABLE account exists for the
    # document's tenant and entity.
    AccountFactory(
        tenant=tenant,
        legal_entity=legal_entity,
        commodity=currency,
        account_type='RECEIVABLE',
    )

    document = AccountingDocumentFactory(
        tenant=tenant,
        legal_entity=legal_entity,
        party=party,
        currency=currency,
        status=DocumentStatus.DRAFT,
        document_type=DocumentType.INVOICE,
        direction=DocumentDirection.SALES,
    )
    DocumentLineFactory(
        document=document,
        account=income_account,
        quantity=Decimal('2.0000'),
        unit_price=Decimal('100.0000'),
    )

    user = get_user_model().objects.create_user(
        email='posting-atomicity@example.com',
        password='testpass',
    )

    return SimpleNamespace(
        tenant=tenant,
        legal_entity=legal_entity,
        document=document,
        user=user,
        service=DocumentPostingService(),
    )


def test_posting_commits_journal_and_document_together(posting_fixture):
    """Control: with no fault, both writes survive the transaction.

    The fault-injection test below asserts that a great deal is absent
    afterwards. That assertion is only meaningful next to evidence that the
    rows are normally present - otherwise a posting path that silently wrote
    nothing at all would satisfy it just as well.
    """
    fx = posting_fixture

    journal_entry = fx.service.post_document(fx.document, fx.user)

    fx.document.refresh_from_db()
    assert fx.document.status == DocumentStatus.POSTED
    assert fx.document.posted_at is not None
    assert fx.document.posted_by == fx.user
    assert fx.document.journal_entry_id == journal_entry.pk

    assert journal_entry.is_posted
    assert JournalEntry.objects.get(pk=journal_entry.pk).is_posted
    assert AuditEvent.objects.filter(action=AuditAction.DOCUMENT_POSTED).count() == 1


def test_fault_after_journal_posted_rolls_back_the_whole_posting(posting_fixture):
    """A failure after the ledger write leaves no trace of the posting.

    The fault fires at the last step ``post_document()`` performs, so at that
    moment the journal entry has been created *and* posted by the accounting
    engine, and the document has already been marked posted. Everything the
    service did must therefore be undone by the rollback.
    """
    fx = posting_fixture
    real_audit_log = AuditEvent.log
    observed = {}

    def fault_at_last_step(*args, **kwargs):
        # Pass every other audit write through. PostingService.post_journal_entry
        # logs JOURNAL_POSTED from inside the engine, so failing there would
        # abort before the document was ever marked posted - an earlier
        # boundary than the one this test is about.
        if kwargs.get('action') != AuditAction.DOCUMENT_POSTED:
            return real_audit_log(*args, **kwargs)

        # Read the transaction's own uncommitted state at the instant of the
        # fault. This is the evidence that the posting really did get as far as
        # the ledger and the document row before we pulled the rug - without
        # it, the rollback assertions below cannot be told apart from "posting
        # failed before it wrote anything".
        observed['journal_states'] = list(
            JournalEntry.objects.filter(source_document_id=fx.document.pk).values_list(
                'is_posted', flat=True
            )
        )
        observed['document_status'] = AccountingDocument.objects.get(
            pk=fx.document.pk
        ).status

        raise InjectedPostingError(
            'injected: journal entry posted and document marked posted, '
            'post_document() not yet returned'
        )

    with (
        mock.patch.object(AuditEvent, 'log', fault_at_last_step),
        pytest.raises(InjectedPostingError),
    ):
        fx.service.post_document(fx.document, fx.user)

    # The fault landed after the ledger write, not before it.
    assert observed['journal_states'] == [True]
    assert observed['document_status'] == DocumentStatus.POSTED

    # The document is exactly as it was: unposted, with no posting metadata and
    # no journal reference.
    fx.document.refresh_from_db()
    assert fx.document.status == DocumentStatus.DRAFT
    assert fx.document.posted_at is None
    assert fx.document.posted_by is None
    assert fx.document.journal_entry_id is None

    # The ledger entry the engine created and posted is gone, not merely
    # unreferenced - a zero count is the whole point, since an orphaned posted
    # entry would corrupt the books just as surely as a missing one.
    assert JournalEntry.objects.filter(source_document_id=fx.document.pk).count() == 0
    assert JournalEntry.objects.count() == 0

    # Neither audit event survives: not DOCUMENT_POSTED, and not the engine's
    # own JOURNAL_POSTED written earlier in the same transaction.
    assert AuditEvent.objects.count() == 0
