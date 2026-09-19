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


#: Children that reach a tenant through a parent rather than through a column
#: of their own. Listed explicitly so that dropping one from a policy migration
#: fails here instead of quietly halving the isolation surface.
INDIRECTLY_SCOPED_TABLES = {
    "accounting_counterpartposting",
    "accounting_reconciliationauditlog",
    "accounting_transactionmetadata",
    "advisor_access_grants",
    "business_documents_approval_step",
    "document_extraction_versions",
    "reporting_dashboardwidget",
    "role_permissions",
    "workflow_transitions",
}

#: Children given their own tenant_id, which the column sweep above already
#: covers - named here to document which ones those are.
DIRECTLY_SCOPED_CHILDREN = {
    "accounting_journalline",
    "business_documents_document_attachment",
    "business_documents_document_line",
    "document_extractions",
    "document_matches",
}


def test_a_policy_alone_does_not_count_as_isolation():
    """Guard the guard: creating a policy without enabling RLS does nothing.

    PostgreSQL only consults policies once ``relrowsecurity`` is set on the
    table, so a table can have a perfectly good policy listed in
    ``pg_policies`` and still be wide open. That is a silent no-op rather than
    an error, and it is exactly the bug the first draft of ``rls/0004`` shipped:
    14 child tables received policies and were never enabled, with every other
    assertion in this file still passing.
    """
    flags = _rls_flags()
    not_enforced = []
    for table in sorted(_policed_tables()):
        enabled, forced = flags.get(table, (False, False))
        if not (enabled and forced):
            not_enforced.append(f"{table} (enabled={enabled}, forced={forced})")

    assert not not_enforced, (
        "tables with a policy but without FORCE ROW LEVEL SECURITY, where the "
        "policy is never evaluated: " + ", ".join(not_enforced)
    )


def test_the_indirectly_scoped_children_are_actually_policed():
    """The 9 children that derive their tenant from a parent are covered."""
    flags = _rls_flags()
    uncovered = sorted(
        table
        for table in INDIRECTLY_SCOPED_TABLES
        if table not in _policed_tables() or not all(flags.get(table, (False, False)))
    )
    assert not uncovered, "indirectly-scoped tables left outside RLS: " + ", ".join(
        uncovered
    )


def test_no_policy_applies_to_public():
    """Every policy names the runtime role, so other roles stay default-denied.

    A policy left at ``TO PUBLIC`` extends itself to every role that is ever
    granted privileges on the table - the opposite of least privilege, and
    invisible in review because the policy reads as if it were scoped.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tablename, policyname, roles::text
            FROM pg_policies WHERE schemaname = 'public' AND roles = '{public}'
            """
        )
        public_policies = cursor.fetchall()

    assert not public_policies, "policies granted TO PUBLIC: " + ", ".join(
        f"{table}.{name}" for table, name, _ in public_policies
    )


def test_every_policy_names_only_the_runtime_role():
    """And the role it names is the one the application is supposed to use."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT unnest(roles)::text FROM pg_policies
            WHERE schemaname = 'public'
            """
        )
        principals = {row[0] for row in cursor.fetchall()}

    assert principals == {"app_user"}, f"unexpected policy principals: {principals}"


def test_child_tenant_cannot_disagree_with_its_parent_at_the_schema_level():
    """The composite keys that make a retenanted child unrepresentable exist."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT conrelid::regclass::text
            FROM pg_constraint
            WHERE contype = 'f' AND array_length(conkey, 1) = 2
            """
        )
        with_composite_fk = {row[0] for row in cursor.fetchall()}

    assert with_composite_fk == DIRECTLY_SCOPED_CHILDREN, (
        "tables whose tenant_id is checked against their parent's: "
        f"{sorted(with_composite_fk)}"
    )


def test_the_posted_immutability_trigger_survived_the_tenant_backfill():
    """The ADR-010 guard is enabled after ``accounting/0004`` disabled it.

    That migration turns the trigger off to backfill ``tenant_id`` on lines of
    posted entries - the whole-row comparison would otherwise refuse the
    ``UPDATE`` - and turns it back on. If it ever fails between the two, this
    is what notices.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tgenabled FROM pg_trigger
            WHERE tgrelid = 'accounting_journalline'::regclass
              AND tgname = 'accounting_journalline_posted_immutable'
            """
        )
        row = cursor.fetchone()

    assert row is not None, "the ADR-010 line-immutability trigger is missing"
    # 'O' = enabled and fires in origin mode, the normal state.
    assert row[0] == "O", f"the ADR-010 trigger is disabled (tgenabled={row[0]!r})"


# --------------------------------------------------------------------------
# The runtime-role system check
# --------------------------------------------------------------------------


def _runtime_role_warnings():
    from django.core import checks

    return [m for m in checks.run_checks(databases=["default"]) if m.id == "rls.W001"]


def test_the_check_warns_when_the_connection_can_bypass_rls():
    """The suite's own connection is the case the check exists to catch.

    Django's test connection is the ``postgres`` superuser, so with
    ``RLS_ENABLED`` on this is exactly the misconfiguration a deployment would
    ship: complete, correct policies that nothing is enforcing.
    """
    from django.test import override_settings

    with override_settings(RLS_ENABLED=True):
        warnings = _runtime_role_warnings()

    assert warnings, "a superuser connection did not raise the bypass warning"
    assert "advisory" in warnings[0].msg


def test_the_check_is_silent_when_rls_is_disabled():
    """Development runs with RLS off; there is nothing to bypass there."""
    from django.test import override_settings

    with override_settings(RLS_ENABLED=False):
        assert _runtime_role_warnings() == []


def test_the_check_is_silent_for_a_role_that_cannot_bypass_rls():
    """And it does not fire for the role the application is meant to use.

    Run as ``app_user`` - owns nothing, no BYPASSRLS, not a superuser - the
    check must stay quiet, or it would be noise on every correct deployment.
    """
    from django.db import transaction
    from django.test import override_settings

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE app_user")
        with override_settings(RLS_ENABLED=True):
            assert _runtime_role_warnings() == []


def test_no_runtime_role_is_a_superuser_or_bypasses_rls():
    """No application role may sit above the policies.

    ``app_user`` is checked directly elsewhere; this is the broader statement,
    that no role the application could plausibly connect as holds either
    escape. A superuser bypasses RLS even against a FORCEd table, so this is
    the one property that makes every other assertion in this suite meaningful.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT rolname, rolsuper, rolbypassrls
            FROM pg_roles
            WHERE rolname NOT LIKE 'pg\\_%'
            ORDER BY rolname
            """
        )
        roles = cursor.fetchall()

    privileged = [
        f"{name} (superuser={is_super}, bypassrls={bypasses})"
        for name, is_super, bypasses in roles
        if name != "postgres" and (is_super or bypasses)
    ]
    assert not privileged, "non-superuser roles above the policies: " + ", ".join(
        privileged
    )


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
