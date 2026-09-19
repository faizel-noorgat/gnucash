"""
Provisioning tests: the database really has the RLS layer the design claims.

These assert against PostgreSQL's own catalogues rather than against the
migration's table list, so adding a tenant-scoped model without a matching
migration fails here instead of leaving an unprotected table behind.
"""

import pytest
from django.db import connection

from tests.rls.conftest import scalar

pytestmark = pytest.mark.django_db(transaction=True)

#: Tables that legitimately carry a ``tenant_id`` column but are not policed.
#: Empty - every such table is expected to be under forced RLS.
UNPOLICED_EXCEPTIONS: set[str] = set()


def _tables_with_tenant_column():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND column_name = 'tenant_id'
            """
        )
        return {row[0] for row in cursor.fetchall()} - UNPOLICED_EXCEPTIONS


def _rls_flags():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
            """
        )
        return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}


def _policed_tables():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT tablename FROM pg_policies WHERE schemaname = 'public'")
        return {row[0] for row in cursor.fetchall()}


def test_every_tenant_scoped_table_exists_in_the_catalogue():
    """Guard the guard: the introspection must actually find the tables."""
    tables = _tables_with_tenant_column()
    assert "accounting_account" in tables
    assert "business_documents_accounting_document" in tables
    assert len(tables) >= 30


def test_every_tenant_scoped_table_has_rls_enabled_and_forced():
    """ENABLE alone exempts the owner; FORCE closes that hole."""
    flags = _rls_flags()
    missing = []
    for table in sorted(_tables_with_tenant_column()):
        enabled, forced = flags.get(table, (False, False))
        if not (enabled and forced):
            missing.append(f"{table} (enabled={enabled}, forced={forced})")

    assert not missing, (
        "tenant-scoped tables without FORCE ROW LEVEL SECURITY: " + ", ".join(missing)
    )


def test_every_tenant_scoped_table_has_an_isolation_policy():
    """RLS with no applicable policy is default-deny, which is a silent outage."""
    policed = _policed_tables()
    missing = sorted(_tables_with_tenant_column() - policed)
    assert not missing, "tenant-scoped tables with no policy: " + ", ".join(missing)


def test_app_user_cannot_bypass_rls():
    """The runtime role is neither a superuser nor a BYPASSRLS role."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app_user'")
        row = cursor.fetchone()

    assert row is not None, "app_user role was never created"
    is_superuser, bypasses_rls = row
    assert not is_superuser, "app_user must not be a superuser"
    assert not bypasses_rls, "app_user must not have BYPASSRLS"


def test_app_user_owns_no_tables():
    """A table's owner can always drop its own security policy."""
    owned = scalar(
        """
        SELECT count(*)
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_roles r ON r.oid = c.relowner
        WHERE n.nspname = 'public' AND r.rolname = 'app_user'
        """
    )
    assert owned == 0, f"app_user owns {owned} objects; ownership is itself a bypass"


def test_context_helpers_return_uuid_columns():
    """The helpers must be uuid-typed, matching every model primary key.

    ``get_current_user_id`` and ``get_current_entity_id`` previously declared
    ``RETURNS integer`` against UUID columns, so the cast raised inside a handler
    that swallowed it and the functions returned NULL for every input. (B-0004)
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.proname, t.typname
            FROM pg_proc p
            JOIN pg_type t ON t.oid = p.prorettype
            WHERE p.proname IN (
                'get_current_tenant_id', 'get_current_user_id', 'get_current_entity_id'
            )
            """
        )
        signatures = dict(cursor.fetchall())

    assert signatures, "none of the RLS context helpers were created"
    assert signatures == {
        "get_current_tenant_id": "uuid",
        "get_current_user_id": "uuid",
        "get_current_entity_id": "uuid",
    }


def test_context_helpers_return_null_when_unset():
    """Absent context is NULL - the deny-everything input, not an error."""
    assert scalar("SELECT get_current_tenant_id()::text") is None
    assert scalar("SELECT get_current_user_id()::text") is None
    assert scalar("SELECT get_current_entity_id()::text") is None
