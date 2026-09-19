"""
Enable, force and police row-level security on the tenant-scoped tables.

The policy on every table is the same shape:

    tenant_id = get_current_tenant_id()

with ``FOR ALL TO PUBLIC``, so it governs SELECT, INSERT, UPDATE and DELETE for
every role. ``TO PUBLIC`` rather than a named role is deliberate: naming
``app_user`` would leave the policy inapplicable to any other non-owner role,
and PostgreSQL's default when RLS is on and no policy applies is *deny*, so the
failure mode of a misnamed role is a total outage rather than a silent leak.
The policy describes the table's security model, not one caller's.

Entity narrowing
----------------
Tables that also carry ``legal_entity_id`` get a second predicate:

    AND (get_current_entity_id() IS NULL OR legal_entity_id = get_current_entity_id())

Absent entity context means "the whole tenant", which is the common case and
must not start returning nothing. Present entity context narrows to that legal
entity. A row whose ``legal_entity_id`` is NULL is invisible while entity
context is set - fail closed rather than treat an unscoped row as a wildcard.

Why FORCE as well as ENABLE
---------------------------
``ENABLE`` alone exempts the table owner, and an owner can simply
``ALTER TABLE ... DISABLE ROW LEVEL SECURITY``. ``FORCE`` closes that. It is not
a complete answer on its own - a *superuser* still bypasses RLS regardless of
FORCE, which is why the runtime connects as ``app_user`` (created in 0001, owns
nothing, no BYPASSRLS) and why the RLS tests drive their assertions through
``SET ROLE app_user`` rather than through Django's own superuser connection.

Scope: tables with a direct ``tenant_id`` column
------------------------------------------------
``TENANT_SCOPED_TABLES`` below lists every table carrying its own ``tenant_id``.
Tables that are tenant-scoped only *transitively* - ``accounting_journalline``,
``business_documents_document_line``, ``advisor_access_grants`` and the other
child tables, which reach a tenant only through a parent FK - are NOT policed
here, because their policy needs an ``EXISTS`` subquery against the parent. That
is a real remaining gap; see the RLS section of the Memory Bank.

The list is frozen here rather than imported from a shared module on purpose: a
migration must keep meaning the same thing after the application changes. The
test suite asserts coverage by introspecting PostgreSQL instead, so adding a
tenant-scoped model without a migration fails a test rather than going unnoticed.
"""

from django.db import migrations

# (table, has_legal_entity_column). Derived from the live model registry.
TENANT_SCOPED_TABLES = [
    # --- accounting ---
    ("accounting_account", True),
    ("accounting_auditevent", True),
    ("accounting_bankaccount", True),
    ("accounting_bankreconciliation", False),
    ("accounting_bankstatement", False),
    ("accounting_banktransaction", False),
    ("accounting_commodity", False),
    ("accounting_exchangerate", False),
    ("accounting_fiscalperiod", True),
    ("accounting_intercompanyrelationship", False),
    ("accounting_interentityevent", False),
    ("accounting_journalentry", True),
    ("accounting_lot", True),
    ("accounting_mappings", True),
    ("accounting_paymentterm", False),
    ("accounting_taxrule", False),
    # --- identity ---
    ("api_tokens", False),
    ("client_engagements", False),
    ("legal_entities", False),
    ("memberships", False),
    ("notification_preferences", False),
    ("notifications", False),
    ("roles", False),
    ("workflow_instances", False),
    # --- business documents ---
    ("business_documents_accounting_document", True),
    ("business_documents_approval_workflow", False),
    ("business_documents_party", False),
    # --- document intelligence ---
    ("documents", True),
    ("mapping_suggestions", False),
    ("review_decision_log", False),
    ("review_queue", False),
    # --- reporting ---
    ("reporting_analyticinsight", False),
    ("reporting_analyticquery", False),
    ("reporting_dashboard", False),
    ("reporting_reportdefinition", False),
    ("reporting_reportinstance", False),
]

POLICY_NAME = "tenant_isolation"


def _predicate(has_legal_entity: bool) -> str:
    """The USING / WITH CHECK expression for one table."""
    parts = ["tenant_id = get_current_tenant_id()"]
    if has_legal_entity:
        parts.append(
            "(get_current_entity_id() IS NULL "
            "OR legal_entity_id = get_current_entity_id())"
        )
    return " AND ".join(parts)


def _apply_sql() -> str:
    statements = []
    for table, has_legal_entity in TENANT_SCOPED_TABLES:
        predicate = _predicate(has_legal_entity)
        statements.append(
            f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n"
            f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;\n"
            f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table};\n"
            f"CREATE POLICY {POLICY_NAME} ON {table} FOR ALL TO PUBLIC\n"
            f"    USING ({predicate})\n"
            f"    WITH CHECK ({predicate});"
        )
    return "\n".join(statements)


def _revert_sql() -> str:
    statements = []
    for table, _ in TENANT_SCOPED_TABLES:
        statements.append(
            f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table};\n"
            f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;\n"
            f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"
        )
    return "\n".join(statements)


class Migration(migrations.Migration):
    dependencies = [
        ("rls", "0001_rls_functions_and_app_role"),
        # The policies reference columns on these tables, so they must exist.
        ("identity", "0001_initial"),
        ("accounting", "0001_initial"),
        ("business_documents", "0001_initial"),
        ("document_intelligence", "0001_initial"),
        ("reporting", "0001_initial"),
    ]

    # One statement per table, and PostgreSQL will not accept CREATE POLICY for
    # a table whose ALTER TABLE ... ENABLE ran in a rolled-back transaction. Per
    # statement autocommit keeps the two in lockstep and makes a mid-list failure
    # legible instead of leaving a partially-applied schema.
    atomic = False

    operations = [
        migrations.RunSQL(sql=_apply_sql(), reverse_sql=_revert_sql()),
    ]
