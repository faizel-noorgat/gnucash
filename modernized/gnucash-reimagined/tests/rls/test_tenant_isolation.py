"""
PostgreSQL row-level-security isolation tests.

Every assertion in this module is made from inside ``rls_session()``, i.e. as
``app_user`` with the context GUCs set transaction-locally. Asserting through
Django's default connection would prove nothing, because that connection is the
``postgres`` superuser and a superuser bypasses RLS whether or not the table has
``FORCE ROW LEVEL SECURITY`` set.
"""

import pytest
from django.db import connection, transaction

from apps.accounting.models import Account
from apps.business_documents.models import Party
from tests.rls.conftest import rls_session, scalar

pytestmark = pytest.mark.django_db(transaction=True)


def _account_names():
    return set(Account.objects.values_list("name", flat=True))


# --------------------------------------------------------------------------
# Reads and writes across the tenant boundary
# --------------------------------------------------------------------------


def test_tenant_cannot_read_another_tenants_rows(two_tenants):
    """Tenant A sees its own accounts and none of tenant B's."""
    with rls_session(tenant=two_tenants["tenant_a"].guid):
        visible = _account_names()
        assert visible == {
            two_tenants["account_a1"].name,
            two_tenants["account_a2"].name,
        }
        assert Account.objects.filter(pk=two_tenants["account_b1"].pk).count() == 0

    # Tenant B's account is genuinely there, so the empty result above is the
    # policy working rather than a row that was never created. This read runs as
    # the unrestricted owner, outside rls_session().
    assert Account.objects.filter(pk=two_tenants["account_b1"].pk).count() == 1


def test_queryset_without_any_tenant_filter_cannot_leak(two_tenants):
    """The backstop: an unfiltered queryset is still tenant-scoped.

    This is the shape of the bug RLS exists to prevent - application code that
    forgets ``.filter(tenant=...)``. The ORM is given no help here at all.
    """
    with rls_session(tenant=two_tenants["tenant_b"].guid):
        assert Account.objects.all().count() == 1
        assert _account_names() == {two_tenants["account_b1"].name}

    with rls_session(tenant=two_tenants["tenant_a"].guid):
        assert Account.objects.all().count() == 2


def test_raw_sql_cannot_bypass_isolation(two_tenants):
    """Hand-written SQL gets the same treatment as the ORM.

    No manager, no queryset, no ORM hook - just a cursor.
    """
    with rls_session(tenant=two_tenants["tenant_a"].guid):
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM accounting_account ORDER BY name")
            names = {row[0] for row in cursor.fetchall()}
        assert names == {
            two_tenants["account_a1"].name,
            two_tenants["account_a2"].name,
        }

        # Even an unqualified count over the whole table cannot see tenant B.
        assert scalar("SELECT count(*) FROM accounting_account") == 2


def test_tenant_cannot_write_another_tenants_rows(two_tenants):
    """An INSERT attributed to another tenant is rejected by the policy."""
    from tests.business_documents.factories import AccountFactory, CurrencyFactory

    tenant_a = two_tenants["tenant_a"]
    tenant_b = two_tenants["tenant_b"]

    with pytest.raises(Exception) as exc, rls_session(tenant=tenant_a.guid):
        AccountFactory(
            tenant=tenant_b,
            legal_entity=two_tenants["entity_b1"],
            commodity=CurrencyFactory(tenant=tenant_b),
            name="Smuggled into tenant B",
        )

    assert "row-level security policy" in str(exc.value)
    assert not Account.objects.filter(name="Smuggled into tenant B").exists()


def test_tenant_cannot_update_another_tenants_rows(two_tenants):
    """An UPDATE aimed at another tenant matches no rows at all."""
    with rls_session(tenant=two_tenants["tenant_a"].guid):
        changed = Account.objects.filter(pk=two_tenants["account_b1"].pk).update(
            name="Renamed by tenant A"
        )
        assert changed == 0

    two_tenants["account_b1"].refresh_from_db()
    assert two_tenants["account_b1"].name == "B account"


def test_tenant_cannot_delete_another_tenants_rows(two_tenants):
    """A DELETE aimed at another tenant matches no rows at all."""
    with rls_session(tenant=two_tenants["tenant_a"].guid):
        deleted, _ = Account.objects.filter(pk=two_tenants["account_b1"].pk).delete()
        assert deleted == 0

    assert Account.objects.filter(pk=two_tenants["account_b1"].pk).exists()


# --------------------------------------------------------------------------
# Failing closed
# --------------------------------------------------------------------------


def test_missing_tenant_context_returns_no_tenant_rows(two_tenants):
    """With no context set, a tenant-scoped table yields nothing.

    Not an error and not everything - nothing. The rows exist (asserted after
    the block, as the unrestricted owner), so the empty result is the policy
    working rather than an empty table.
    """
    with rls_session():
        assert Account.objects.all().count() == 0
        assert Party.objects.all().count() == 0
        assert scalar("SELECT count(*) FROM accounting_account") == 0

    assert Account.objects.count() >= 3


def test_tenant_context_that_is_not_a_uuid_fails_loudly(two_tenants):
    """A malformed context raises; it does not quietly become NULL.

    This is the defect the previous SQL functions encoded with
    ``EXCEPTION WHEN OTHERS THEN RETURN NULL``: every bad value silently
    degraded to the same "no rows" result as a legitimately absent context, so a
    bug in whatever writes the context was indistinguishable from normal
    operation.
    """
    with pytest.raises(Exception) as exc, transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE app_user")
            cursor.execute(
                "SELECT set_config('app.current_tenant_id', 'not-a-uuid', true)"
            )
        Account.objects.count()

    assert "invalid input syntax for type uuid" in str(exc.value)


def test_transaction_local_context_does_not_leak_to_the_next_transaction(two_tenants):
    """Context set in one transaction is gone in the next one.

    Same connection, same session, no cleanup in between - ``SET LOCAL`` is what
    makes this safe under connection pooling.
    """
    with rls_session(tenant=two_tenants["tenant_a"].guid):
        assert Account.objects.count() == 2

    with rls_session():
        assert Account.objects.count() == 0

    with rls_session(tenant=two_tenants["tenant_b"].guid):
        assert Account.objects.count() == 1


# --------------------------------------------------------------------------
# Entity scope within a tenant
# --------------------------------------------------------------------------


def test_entity_scope_narrows_within_a_tenant(two_tenants):
    """Entity context narrows a tenant's rows to one legal entity."""
    tenant_a = two_tenants["tenant_a"]

    with rls_session(tenant=tenant_a.guid):
        assert Account.objects.count() == 2

    with rls_session(tenant=tenant_a.guid, entity=two_tenants["entity_a1"].guid):
        assert _account_names() == {two_tenants["account_a1"].name}

    with rls_session(tenant=tenant_a.guid, entity=two_tenants["entity_a2"].guid):
        assert _account_names() == {two_tenants["account_a2"].name}


def test_entity_scope_from_another_tenant_yields_nothing(two_tenants):
    """A tenant's context cannot be narrowed with a foreign entity's id."""
    with rls_session(
        tenant=two_tenants["tenant_a"].guid, entity=two_tenants["entity_b1"].guid
    ):
        assert Account.objects.count() == 0
