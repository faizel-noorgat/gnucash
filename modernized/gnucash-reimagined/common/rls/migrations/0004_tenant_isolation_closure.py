"""Close the tenant isolation surface, and name the role it applies to.

Four changes, in one place because they are one decision.

**1. The principal is named, not PUBLIC.** Every policy from 0002 was ``TO
PUBLIC``. The reasoning there was that naming a role leaves the policy
inapplicable to any other role, and PostgreSQL's default for a table with RLS
enabled and no applicable policy is *deny* - so a misnamed role is an outage,
not a leak. That reasoning is still true, and it is still the wrong trade. A
policy is a statement about who may reach the table; ``PUBLIC`` makes it a
statement about nobody in particular, and it silently extends to every role
that is ever granted privileges on the table. Least privilege and default deny
mean the policy names ``app_user`` and anything else is denied until someone
writes it a policy on purpose. ``ALTER POLICY`` is used rather than DROP and
re-CREATE so the predicates written in 0002 are not restated here and cannot
drift from what was reviewed.

**2. The five tables given their own ``tenant_id`` in the app migrations get a
policy.** They are children of an entity-scoped parent - a journal entry, an
accounting document, a document - so they carry the parent's entity narrowing
as well as their own tenant equality: a line of a journal entry belonging to
legal entity X is invisible while entity context is set to Y. A row whose
parent has a NULL ``legal_entity_id`` is invisible while entity context is
set, which is the same fail-closed rule 0002 applies to the parents themselves.

**3. Tables that reach a tenant only through a parent get an ``EXISTS``
policy.** Duplicating ``tenant_id`` onto these would make the model worse:
``role_permissions`` is a pure join, ``workflow_transitions`` and
``reporting_dashboardwidget`` are components whose identity is meaningless
apart from their parent, and ``advisor_access_grants`` is an access-control
record whose tenancy *is* its engagement. These get::

    EXISTS (SELECT 1 FROM parent p
            WHERE p.guid = child.parent_id
              AND p.tenant_id = get_current_tenant_id())

with a matching ``WITH CHECK``, because protecting SELECT while leaving INSERT
and UPDATE open is not a boundary at all.

Note what these do *not* need. An ``EXISTS`` subquery is itself subject to the
policies on the table it reads, so entity narrowing on the parent propagates to
the child for free - a reconciliation audit log reaches its tenant through its
journal line, and that line is already narrowed by the entity of its entry.
Only the tables policed by a direct equality need the entity clause spelled
out.

**4. The pre-context read set.** ``AuthorizationService.can_access_tenant()``
is what decides whether a caller may assume a tenant, and it reads the very
tables the policies confine: memberships, advisor grants, engagements and the
tenant row itself. With no tenant context set those reads return nothing and
the answer is ``False`` for everyone - including the legitimate member. So four
tables carry a second, *permissive* ``FOR SELECT`` policy granting a caller
their own rows::

    memberships          user_id = get_current_user_id()
    tenants              EXISTS (a membership of mine in that tenant)
    advisor_access_grants practice_user_id = get_current_user_id()
    client_engagements   EXISTS (a practice membership of mine in that practice)

Permissive policies are OR'd, so these widen SELECT only. Writes still require
a tenant context, because the ``FOR ALL`` policy's ``WITH CHECK`` is unchanged.
The set is deliberately minimal and stated as a set: "before you have chosen a
tenant, you may see your own memberships, your own grants, your firm's
engagements, and the tenants you belong to." A middleware bug that forgets to
set context then yields zero rows rather than the wrong tenant's data - the
failure mode is an outage, which is the direction isolation should fail in.

The ``tenants`` policy deserves one more note. Its primary key *is* the tenant,
so the tenant equality is ``guid = get_current_tenant_id()`` rather than
``tenant_id = ...``. Registration creates a tenant before any membership exists,
so no SELECT policy can authorise reading it back; INSERT therefore has its own
carve-out requiring an authenticated user who records themselves as
``created_by``. That is the whole of the bootstrap allowance, and it grants
nothing but the ability to create a tenant row - reading it, or any other
tenant, still requires a membership or an active context.
"""

from django.db import migrations

APP_ROLE = "app_user"
POLICY_NAME = "tenant_isolation"

# The 36 tables policed in 0002. Re-listed rather than imported: a migration
# must keep meaning the same thing after the application changes, and importing
# a list out of another migration would let an edit to 0002 silently change
# what 0004 does.
DIRECT_TENANT_TABLES = [
    "accounting_account",
    "accounting_auditevent",
    "accounting_bankaccount",
    "accounting_bankreconciliation",
    "accounting_bankstatement",
    "accounting_banktransaction",
    "accounting_commodity",
    "accounting_exchangerate",
    "accounting_fiscalperiod",
    "accounting_intercompanyrelationship",
    "accounting_interentityevent",
    "accounting_journalentry",
    "accounting_lot",
    "accounting_mappings",
    "accounting_paymentterm",
    "accounting_taxrule",
    "api_tokens",
    "client_engagements",
    "legal_entities",
    "memberships",
    "notification_preferences",
    "notifications",
    "roles",
    "workflow_instances",
    "business_documents_accounting_document",
    "business_documents_approval_workflow",
    "business_documents_party",
    "documents",
    "mapping_suggestions",
    "review_decision_log",
    "review_queue",
    "reporting_analyticinsight",
    "reporting_analyticquery",
    "reporting_dashboard",
    "reporting_reportdefinition",
    "reporting_reportinstance",
]

#: (child, parent, child FK column) - children that now carry their own
#: tenant_id. The parent is entity-scoped, so the policy narrows by entity too.
DIRECT_CHILDREN = [
    ("accounting_journalline", "accounting_journalentry", "journal_entry_id"),
    (
        "business_documents_document_line",
        "business_documents_accounting_document",
        "document_id",
    ),
    (
        "business_documents_document_attachment",
        "business_documents_accounting_document",
        "document_id",
    ),
    ("document_extractions", "documents", "document_id"),
    ("document_matches", "documents", "document_id"),
]

#: (child, parent, child FK column) - children whose tenancy stays derived.
INDIRECT_CHILDREN = [
    (
        "accounting_transactionmetadata",
        "accounting_journalentry",
        "journal_entry_id",
    ),
    (
        "accounting_counterpartposting",
        "accounting_interentityevent",
        "inter_entity_event_id",
    ),
    (
        "accounting_reconciliationauditlog",
        "accounting_journalline",
        "journal_line_id",
    ),
    (
        "business_documents_approval_step",
        "business_documents_approval_workflow",
        "workflow_id",
    ),
    ("document_extraction_versions", "documents", "document_id"),
    ("reporting_dashboardwidget", "reporting_dashboard", "dashboard_id"),
    ("workflow_transitions", "workflow_instances", "workflow_instance_id"),
]

#: Tables carrying a permissive self-scoped SELECT policy, so that the
#: authorization decision can be made before any tenant context exists.
PRECONTEXT_READ_POLICIES = [
    (
        "memberships",
        "own_membership_read",
        "user_id = get_current_user_id()",
    ),
    (
        "tenants",
        "member_tenant_read",
        "EXISTS (SELECT 1 FROM memberships m "
        "WHERE m.tenant_id = tenants.guid "
        "AND m.user_id = get_current_user_id())",
    ),
    (
        "advisor_access_grants",
        "own_grant_read",
        "practice_user_id = get_current_user_id()",
    ),
    (
        "client_engagements",
        "practice_member_read",
        "EXISTS (SELECT 1 FROM practice_memberships pm "
        "WHERE pm.practice_id = client_engagements.practice_id "
        "AND pm.user_id = get_current_user_id())",
    ),
]

#: Roles are nullable-tenant: a system role is shared by every tenant and
#: ``AuthorizationService.has_permission`` explicitly matches
#: ``Q(tenant=tenant) | Q(tenant__isnull=True)``. A bare equality would make
#: every system role invisible and silently remove the permissions it grants.
#: The ``is_system_role`` half keeps an accidental NULL from becoming global.
ROLES_PREDICATE = (
    "(tenant_id = get_current_tenant_id() "
    "OR (tenant_id IS NULL AND is_system_role))"
)

#: ``role_permissions`` is a pure join onto roles, so it inherits that rule.
ROLE_PERMISSIONS_PREDICATE = (
    "EXISTS (SELECT 1 FROM roles r WHERE r.guid = role_permissions.role_id "
    "AND (r.tenant_id = get_current_tenant_id() "
    "OR (r.tenant_id IS NULL AND r.is_system_role)))"
)

ADVISOR_GRANTS_PREDICATE = (
    "EXISTS (SELECT 1 FROM client_engagements e "
    "WHERE e.guid = advisor_access_grants.engagement_id "
    "AND e.tenant_id = get_current_tenant_id())"
)

TENANTS_ISOLATION_PREDICATE = "guid = get_current_tenant_id()"


def _policy_sql(table, predicate, *, name=POLICY_NAME):
    """The policy alone, for a table that is already enabled and forced."""
    return (
        f"DROP POLICY IF EXISTS {name} ON {table};\n"
        f"CREATE POLICY {name} ON {table} FOR ALL TO {APP_ROLE}\n"
        f"    USING ({predicate})\n"
        f"    WITH CHECK ({predicate});"
    )


def _enable_and_policy(table, predicate):
    """``ENABLE`` + ``FORCE`` RLS, then the policy, for a newly policed table.

    Creating a policy on a table whose RLS is not enabled does nothing at all:
    PostgreSQL only consults policies once ``relrowsecurity`` is set, so the
    table stays wide open while ``pg_policies`` cheerfully lists it. That is a
    silent no-op rather than an error, which is why every table policed here
    goes through this function rather than being handed a bare policy, and why
    ``tests/rls/test_rls_provisioning.py`` asserts the ``relforcerowsecurity``
    flag rather than the mere existence of a policy.
    """
    return (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n"
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;\n"
        + _policy_sql(table, predicate)
    )


def _apply_sql() -> str:
    statements = []

    # 1. Re-principal the tables policed in 0002. ALTER POLICY rather than
    #    recreating them: the predicate was written and reviewed once, in 0002,
    #    and restating it here would give it a second chance to be wrong.
    for table in DIRECT_TENANT_TABLES:
        statements.append(
            f"ALTER POLICY {POLICY_NAME} ON {table} TO {APP_ROLE};"
        )

    # `roles` additionally needs its predicate widened for system roles.
    statements.append(
        f"ALTER POLICY {POLICY_NAME} ON roles TO {APP_ROLE}\n"
        f"    USING ({ROLES_PREDICATE})\n"
        f"    WITH CHECK ({ROLES_PREDICATE});"
    )

    # 2. Children that now carry their own tenant_id. The entity clause mirrors
    #    0002's rule for their parents: absent entity context means the whole
    #    tenant, and a NULL legal_entity_id on the parent is hidden rather than
    #    treated as a wildcard.
    for child, parent, fk_column in DIRECT_CHILDREN:
        predicate = (
            "tenant_id = get_current_tenant_id() "
            "AND (get_current_entity_id() IS NULL OR EXISTS ("
            f"SELECT 1 FROM {parent} p "
            f"WHERE p.guid = {child}.{fk_column} "
            "AND p.legal_entity_id = get_current_entity_id()))"
        )
        statements.append(_enable_and_policy(child, predicate))

    # 3. Children whose tenancy stays derived through a parent.
    for child, parent, fk_column in INDIRECT_CHILDREN:
        predicate = (
            "EXISTS (SELECT 1 FROM "
            f"{parent} p WHERE p.guid = {child}.{fk_column} "
            "AND p.tenant_id = get_current_tenant_id())"
        )
        statements.append(_enable_and_policy(child, predicate))

    statements.append(
        _enable_and_policy("role_permissions", ROLE_PERMISSIONS_PREDICATE)
    )
    statements.append(
        _enable_and_policy("advisor_access_grants", ADVISOR_GRANTS_PREDICATE)
    )

    # 4. The tenant registry itself. Its primary key is the tenant id, so the
    #    equality is on `guid`, and INSERT is separable from SELECT because
    #    registration creates a tenant before any membership can authorise
    #    reading it back.
    statements.append(
        "ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;\n"
        "ALTER TABLE tenants FORCE ROW LEVEL SECURITY;\n"
        + _policy_sql("tenants", TENANTS_ISOLATION_PREDICATE)
        + "\nCREATE POLICY tenant_self_registration ON tenants "
        f"FOR INSERT TO {APP_ROLE}\n"
        "    WITH CHECK (get_current_user_id() IS NOT NULL "
        "AND created_by_id = get_current_user_id());"
    )

    # The advisor route needs the tenant row too. `can_access_tenant()` cannot
    # approve access to a tenant the caller is not even allowed to load, so
    # without this an advisor is refused with a valid, active grant.
    #
    # This predicate is deliberately WEAKER than the authorization rule, and
    # that is the point. It answers "which tenants may you ask about", not
    # "which tenants may you use" - the decision stays in the service, in one
    # place. It therefore ignores grant status, revocation and expiry on
    # purpose: a policy that mirrored those would be a second copy of the
    # rule, and the failure mode of a second copy that drifts is a legitimate
    # advisor being locked out. Answering too generously costs nothing here,
    # because the row it reveals is one the caller already has a grant against.
    statements.append(
        f"DROP POLICY IF EXISTS advisor_tenant_read ON tenants;\n"
        f"CREATE POLICY advisor_tenant_read ON tenants FOR SELECT TO {APP_ROLE}\n"
        "    USING (EXISTS (\n"
        "        SELECT 1 FROM advisor_access_grants g\n"
        "        JOIN client_engagements e ON e.guid = g.engagement_id\n"
        "        WHERE e.tenant_id = tenants.guid\n"
        "          AND g.practice_user_id = get_current_user_id()));"
    )

    # 5. The pre-context read set.
    for table, name, predicate in PRECONTEXT_READ_POLICIES:
        statements.append(
            f"DROP POLICY IF EXISTS {name} ON {table};\n"
            f"CREATE POLICY {name} ON {table} FOR SELECT TO {APP_ROLE}\n"
            f"    USING ({predicate});"
        )

    return "\n".join(statements)


def _revert_sql() -> str:
    statements = []
    for table, name, _ in PRECONTEXT_READ_POLICIES:
        statements.append(f"DROP POLICY IF EXISTS {name} ON {table};")

    statements.append("DROP POLICY IF EXISTS advisor_tenant_read ON tenants;")
    statements.append("DROP POLICY IF EXISTS tenant_self_registration ON tenants;")
    statements.append(f"DROP POLICY IF EXISTS {POLICY_NAME} ON tenants;")
    statements.append("ALTER TABLE tenants NO FORCE ROW LEVEL SECURITY;")
    statements.append("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY;")

    for table in ("role_permissions", "advisor_access_grants"):
        statements.append(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table};")
        statements.append(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        statements.append(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    for child, _, _ in DIRECT_CHILDREN + INDIRECT_CHILDREN:
        statements.append(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {child};")
        statements.append(f"ALTER TABLE {child} NO FORCE ROW LEVEL SECURITY;")
        statements.append(f"ALTER TABLE {child} DISABLE ROW LEVEL SECURITY;")

    # Put the principal back the way 0002 left it, and the roles predicate with
    # it, so reversing this migration returns the schema to a state 0002 alone
    # would have produced.
    for table in DIRECT_TENANT_TABLES:
        statements.append(f"ALTER POLICY {POLICY_NAME} ON {table} TO PUBLIC;")

    statements.append(
        f"ALTER POLICY {POLICY_NAME} ON roles TO PUBLIC\n"
        "    USING (tenant_id = get_current_tenant_id())\n"
        "    WITH CHECK (tenant_id = get_current_tenant_id());"
    )

    return "\n".join(statements)


class Migration(migrations.Migration):
    dependencies = [
        ("rls", "0003_child_tenant_consistency"),
    ]

    # Per-statement autocommit, for the same reason 0002 uses it: `ALTER POLICY`
    # on a table whose RLS state is mid-change inside a rolled-back transaction
    # is rejected, and a mid-list failure is far easier to read when the
    # statements before it are already committed.
    atomic = False

    operations = [
        migrations.RunSQL(sql=_apply_sql(), reverse_sql=_revert_sql()),
    ]
