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
from django.db import connection

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
    }


@pytest.fixture
def decimal_amount():
    """A representative monetary value, kept out of the fixtures' literals."""
    return Decimal("100.0000")
