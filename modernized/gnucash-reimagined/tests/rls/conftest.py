"""
Fixtures and helpers for the RLS integration tests.

These tests are deliberately unusual: the rest of the suite runs as the
``postgres`` superuser, and a superuser bypasses row-level security entirely -
even against a table with ``FORCE ROW LEVEL SECURITY``. Django's own connection
therefore cannot demonstrate isolation, and a test that asserted anything about
RLS through it would pass no matter what the policies said.

So every assertion here is made from inside ``rls_session()``, which drops to the
non-owner, non-superuser ``app_user`` role with ``SET LOCAL ROLE`` and sets the
context GUCs with ``set_config(..., true)``. Both are transaction-scoped, which
is exactly the propagation mechanism under test.
"""

from contextlib import contextmanager
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection

from apps.identity.models import Membership
from tests.business_documents.factories import (
    AccountFactory,
    CurrencyFactory,
    LegalEntityFactory,
    PartyFactory,
    TenantFactory,
)

#: The role the application is expected to run as in every real environment.
APP_ROLE = "app_user"


@contextmanager
def rls_session(tenant=None, user=None, entity=None, role=APP_ROLE):
    """Run the block as ``role`` with the given RLS context.

    Mirrors what ``common.middleware.tenant`` does for a request: the same three
    GUCs, set transaction-locally, so that PostgreSQL's ``get_current_*_id()``
    helpers see them. A value of ``None`` means "leave this GUC unset", which is
    how the missing-context cases are expressed.

    Assumes an ambient transaction (``django_db(transaction=True)`` plus this
    ``atomic()`` gives a real one, not a savepoint).
    """
    from django.db import transaction

    with transaction.atomic():
        with connection.cursor() as cursor:
            if role is not None:
                cursor.execute(f"SET LOCAL ROLE {role}")
            for variable, value in (
                ("app.current_tenant_id", tenant),
                ("app.current_user_id", user),
                ("app.current_entity_id", entity),
            ):
                if value is not None:
                    cursor.execute(
                        "SELECT set_config(%s, %s, true)", [variable, str(value)]
                    )
        yield


@contextmanager
def app_role(role=APP_ROLE):
    """Assume the runtime role for the block, setting no context at all.

    Setting context is only half of what makes RLS work: the connecting role
    must also be one that RLS applies to. ``app_user`` is that role in every
    real environment, but Django's connection here is the ``postgres``
    superuser, which bypasses RLS regardless of FORCE. Tests for code that sets
    its own context - the Celery task base class - therefore have to establish
    the role themselves and then let the code under test supply the context.
    """
    from django.db import transaction

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL ROLE {role}")
        yield


def scalar(sql, params=None):
    """Run a query and return the first column of the first row."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
    return row[0] if row else None


@pytest.fixture
def two_tenants():
    """Two tenants whose data must never be visible to one another.

    Tenant A carries two legal entities so that entity scoping can be exercised
    inside a single tenant; tenant B carries one.
    """
    tenant_a = TenantFactory(name="Tenant A", slug="tenant-a")
    entity_a1 = LegalEntityFactory(tenant=tenant_a, name="A Entity One")
    entity_a2 = LegalEntityFactory(tenant=tenant_a, name="A Entity Two")
    currency_a = CurrencyFactory(tenant=tenant_a)
    account_a1 = AccountFactory(
        tenant=tenant_a,
        legal_entity=entity_a1,
        commodity=currency_a,
        name="A account in entity one",
    )
    account_a2 = AccountFactory(
        tenant=tenant_a,
        legal_entity=entity_a2,
        commodity=currency_a,
        name="A account in entity two",
    )
    party_a = PartyFactory(tenant=tenant_a)

    tenant_b = TenantFactory(name="Tenant B", slug="tenant-b")
    entity_b1 = LegalEntityFactory(tenant=tenant_b, name="B Entity One")
    currency_b = CurrencyFactory(tenant=tenant_b)
    account_b1 = AccountFactory(
        tenant=tenant_b,
        legal_entity=entity_b1,
        commodity=currency_b,
        name="B account",
    )
    party_b = PartyFactory(tenant=tenant_b)

    # Users. Built here rather than in a fixture of their own because every
    # authorisation question in this suite is "which of these may see what".
    #
    # `member_a` holds an active membership in tenant A and nothing else - the
    # direct route into a tenant.
    # `advisor_a` / `advisor_b` hold no membership at all and reach a tenant
    # only through a practice engagement and a grant, which is the second and
    # quite different route `can_access_tenant()` recognises.
    user_model = get_user_model()
    member_a = user_model.objects.create_user(
        email="member-a@example.com", password="testpass123"
    )
    member_b = user_model.objects.create_user(
        email="member-b@example.com", password="testpass123"
    )
    advisor_a = user_model.objects.create_user(
        email="advisor-a@example.com", password="testpass123"
    )
    advisor_b = user_model.objects.create_user(
        email="advisor-b@example.com", password="testpass123"
    )
    outsider = user_model.objects.create_user(
        email="outsider@example.com", password="testpass123"
    )

    Membership.objects.create(user=member_a, tenant=tenant_a, status="active")
    Membership.objects.create(user=member_b, tenant=tenant_b, status="active")

    return {
        "tenant_a": tenant_a,
        "entity_a1": entity_a1,
        "entity_a2": entity_a2,
        "account_a1": account_a1,
        "account_a2": account_a2,
        "party_a": party_a,
        "tenant_b": tenant_b,
        "entity_b1": entity_b1,
        "account_b1": account_b1,
        "party_b": party_b,
        "member_a": member_a,
        "member_b": member_b,
        "advisor_a": advisor_a,
        "advisor_b": advisor_b,
        "outsider": outsider,
    }


@pytest.fixture
def decimal_amount():
    """A representative monetary value, kept out of the fixtures' literals."""
    return Decimal("100.0000")


def _build_child_rows(two_tenants):
    """One row of every policed child kind, in each of the two tenants.

    Built as the unrestricted owner (this runs outside ``rls_session``), so a
    later assertion that a tenant cannot see one of these rows is testing the
    policy rather than an insert that never happened.

    Two shapes are represented deliberately:

    * children that carry their own ``tenant_id`` - journal lines, document
      lines, attachments, extractions - policed by an equality on that column;
    * children that reach a tenant through a parent - advisor access grants -
      policed by an ``EXISTS`` against it.
    """
    from datetime import date

    from apps.accounting.models import JournalEntry, JournalLine
    from apps.business_documents.models import (
        AccountingDocument,
        DocumentAttachment,
        DocumentLine,
    )
    from apps.document_intelligence.models import (
        Document as IntelligenceDocument,
        DocumentExtraction,
        DocumentMatch,
        DocumentSource,
    )
    from apps.identity.models import (
        AdvisorAccessGrant,
        ClientEngagement,
        Practice,
        PracticeMembership,
        Role,
    )

    rows = {}
    for key, tenant_key, entity_key, account_key, party_key in (
        ("a", "tenant_a", "entity_a1", "account_a1", "party_a"),
        ("b", "tenant_b", "entity_b1", "account_b1", "party_b"),
    ):
        tenant = two_tenants[tenant_key]
        entity = two_tenants[entity_key]
        account = two_tenants[account_key]
        party = two_tenants[party_key]

        entry = JournalEntry.objects.create(
            date=date.today(),
            description=f"Entry owned by tenant {key.upper()}",
            transaction_currency=account.commodity,
            tenant=tenant,
            legal_entity=entity,
        )
        # tenant is deliberately not passed: the model derives it from the
        # entry, which is the behaviour ordinary callers rely on.
        line = JournalLine.objects.create(
            journal_entry=entry,
            account=account,
            amount=Decimal("10.0000000000"),
            value=Decimal("10.0000000000"),
        )

        document = AccountingDocument.objects.create(
            tenant=tenant,
            legal_entity=entity,
            document_number=f"INV-{key.upper()}-0001",
            document_type="invoice",
            direction="sales",
            party=party,
            document_date=date.today(),
            currency=account.commodity,
        )
        document_line = DocumentLine.objects.create(
            document=document,
            line_number=1,
            description=f"Line owned by tenant {key.upper()}",
            quantity=Decimal("1.0000"),
            unit_price=Decimal("100.0000"),
            account=account,
        )
        attachment = DocumentAttachment.objects.create(
            document=document,
            filename=f"{key}.pdf",
            content_type="application/pdf",
            size=11,
            storage_key=f"tenant-{key}/{key}.pdf",
            content_hash=f"hash-{key}",
        )

        intelligence_document = IntelligenceDocument.objects.create(
            tenant_id=tenant.guid,
            original_file_key=f"originals/{key}.pdf",
            content_hash=IntelligenceDocument.compute_sha256(key.encode()),
            mime_type="application/pdf",
            original_filename=f"{key}.pdf",
            size_bytes=11,
            source=DocumentSource.WEB_UPLOAD,
        )
        extraction = DocumentExtraction.objects.create(
            document=intelligence_document,
            version=1,
            ocr_provider="mock",
            ocr_model_version="1",
            extraction_model_version="1",
        )
        match = DocumentMatch.objects.create(
            document=intelligence_document,
            kind="party",
            status="proposed",
        )

        practice = Practice.objects.create(
            name=f"Practice {key.upper()}", slug=f"practice-{key}"
        )
        role = Role.objects.create(name=f"Advisor role {key.upper()}", tenant=tenant)
        # Active, not the default 'pending': can_access_tenant() treats a
        # pending engagement as no access at all, which is the point of the
        # status field and would make the advisor tests pass for the wrong
        # reason.
        engagement = ClientEngagement.objects.create(
            practice=practice, tenant=tenant, status="active"
        )
        grant = AdvisorAccessGrant.objects.create(
            engagement=engagement,
            practice_user=two_tenants[f"advisor_{key}"],
            tenant_role=role,
        )
        PracticeMembership.objects.create(
            user=two_tenants[f"advisor_{key}"], practice=practice, status="active"
        )

        rows[f"journal_entry_{key}"] = entry
        rows[f"journal_line_{key}"] = line
        rows[f"document_{key}"] = document
        rows[f"document_line_{key}"] = document_line
        rows[f"attachment_{key}"] = attachment
        rows[f"intelligence_document_{key}"] = intelligence_document
        rows[f"extraction_{key}"] = extraction
        rows[f"match_{key}"] = match
        rows[f"advisor_grant_{key}"] = grant
        rows[f"engagement_{key}"] = engagement
        rows[f"practice_{key}"] = practice

    return rows


@pytest.fixture
def child_rows(two_tenants):
    """Rows of every policed child kind, one per tenant - see the builder."""
    return _build_child_rows(two_tenants)
