"""Isolation tests for the child tables that reach a tenant through a parent.

Two years of "the parent is policed, so the child is covered" is what left
``accounting_journalline`` - the table holding the ledger's debit and credit
amounts - readable by any tenant that ran raw SQL against it. A child is not
covered by its parent's policy. It is covered by its own, or by nothing.

Every isolation assertion here is made as ``app_user`` inside ``rls_session()``.
Django's own connection is the ``postgres`` superuser, and a superuser bypasses
row-level security even against a table with ``FORCE ROW LEVEL SECURITY``, so an
assertion made through it would pass whatever the policies said.

The read and write paths are both exercised deliberately. A policy that filters
SELECT while leaving INSERT, UPDATE and DELETE open is not a boundary: the row a
tenant cannot read is still a row it can overwrite.
"""

import uuid
from decimal import Decimal

import pytest
from django.db import connection, transaction

from apps.accounting.models import JournalLine
from apps.business_documents.models import DocumentAttachment, DocumentLine
from apps.document_intelligence.models import DocumentExtraction
from apps.identity.models import AdvisorAccessGrant
from tests.rls.conftest import rls_session, scalar

pytestmark = pytest.mark.django_db(transaction=True)


#: (label, attribute name in the `child_rows` fixture). The five children that
#: carry their own tenant_id, plus the indirectly-scoped advisor grant.
CHILD_KINDS = [
    ("journal line", "journal_line"),
    ("document line", "document_line"),
    ("document attachment", "attachment"),
    ("document extraction", "extraction"),
    ("document match", "match"),
    ("advisor access grant", "advisor_grant"),
]


def _count(table: str) -> int:
    return scalar(f"SELECT count(*) FROM {table}")


# --------------------------------------------------------------------------
# Reads and writes across the tenant boundary
# --------------------------------------------------------------------------


@pytest.mark.parametrize("label,key", CHILD_KINDS, ids=[k for _, k in CHILD_KINDS])
def test_tenant_cannot_read_another_tenants_child_rows(child_rows, two_tenants, label, key):
    """Raw SQL over a child table returns only the tenant in context."""
    tenant_a = two_tenants["tenant_a"]
    row_a = child_rows[f"{key}_a"]
    row_b = child_rows[f"{key}_b"]
    table = row_a._meta.db_table
    pk_column = row_a._meta.pk.column

    with rls_session(tenant=tenant_a.guid):
        # Tenant A sees its own row and the table holds nothing else for it.
        assert scalar(f"SELECT count(*) FROM {table}") == 1
        assert (
            scalar(
                f"SELECT count(*) FROM {table} WHERE {pk_column} = %s", [row_a.pk]
            )
            == 1
        )
        # ...and knocking on tenant B's row by primary key returns nothing.
        assert (
            scalar(
                f"SELECT count(*) FROM {table} WHERE {pk_column} = %s", [row_b.pk]
            )
            == 0
        )


@pytest.mark.parametrize("label,key", CHILD_KINDS, ids=[k for _, k in CHILD_KINDS])
def test_queryset_without_a_tenant_filter_is_contained(child_rows, two_tenants, label, key):
    """The backstop: a queryset with no tenant filter at all is still scoped.

    This is the exact shape of the bug RLS exists to catch - application code
    that forgets ``.filter(tenant=...)`` - so the ORM is given no help.
    """
    model = child_rows[f"{key}_a"].__class__
    with rls_session(tenant=two_tenants["tenant_a"].guid):
        assert model.objects.count() == 1
    with rls_session(tenant=two_tenants["tenant_b"].guid):
        assert model.objects.count() == 1


def test_tenant_cannot_insert_a_journal_line_under_another_tenants_entry(
    child_rows, two_tenants, decimal_amount
):
    """An INSERT hung off tenant B's entry is refused, not silently retenanted.

    The composite foreign key added in ``rls/0003`` is what makes this a
    constraint rather than a convention: the child names a tenant *and* a
    parent, and PostgreSQL requires a parent that has both.
    """
    entry_b = child_rows["journal_entry_b"]
    account_b = two_tenants["account_b1"]

    with pytest.raises(Exception) as exc, rls_session(tenant=two_tenants["tenant_a"].guid):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO accounting_journalline "
                "(guid, journal_entry_id, account_id, amount, value, memo, "
                " action, reconcile_status, online_id, created_at, updated_at, tenant_id) "
                "VALUES (%s, %s, %s, %s, %s, '', '', 'NOT_CLEARED', '', now(), now(), %s)",
                [
                    uuid.uuid4(),
                    entry_b.guid,
                    account_b.guid,
                    Decimal("1.0000000000"),
                    Decimal("1.0000000000"),
                    two_tenants["tenant_a"].guid,
                ],
            )

    # Either the write policy refuses the row (tenant mismatch) or the
    # composite key does (no such parent in tenant A). Both are correct; what
    # matters is that it did not land.
    assert "row-level security policy" in str(exc.value) or "foreign key" in str(exc.value)
    assert _count("accounting_journalline") == 2


def test_child_tenant_cannot_disagree_with_its_parent(child_rows, two_tenants):
    """A child cannot be relabelled into another tenant.

    Stated as the invariant rather than as a policy: even with full write
    permission, there is no parent row that would satisfy the composite key, so
    the UPDATE is rejected by the database rather than by a check somebody has
    to remember to write.
    """
    line_b = child_rows["journal_line_b"]

    with pytest.raises(Exception) as exc, transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE accounting_journalline SET tenant_id = %s WHERE guid = %s",
                [two_tenants["tenant_a"].guid, line_b.guid],
            )

    assert "foreign key" in str(exc.value)

    # And the row is untouched: still in tenant B, still attached to B's entry.
    line_b.refresh_from_db()
    assert line_b.tenant_id == two_tenants["tenant_b"].guid


def test_tenant_cannot_update_another_tenants_child_rows(child_rows, two_tenants):
    """An UPDATE aimed across the boundary matches no rows at all."""
    line_b = child_rows["journal_line_b"]

    with rls_session(tenant=two_tenants["tenant_a"].guid):
        changed = JournalLine.objects.filter(pk=line_b.pk).update(memo="Renamed by A")
        assert changed == 0

    line_b.refresh_from_db()
    assert line_b.memo == ""


def test_tenant_cannot_delete_another_tenants_child_rows(child_rows, two_tenants):
    """A DELETE aimed across the boundary matches no rows at all."""
    line_b = child_rows["journal_line_b"]

    with rls_session(tenant=two_tenants["tenant_a"].guid):
        deleted, _ = JournalLine.objects.filter(pk=line_b.pk).delete()
        assert deleted == 0

    assert JournalLine.objects.filter(pk=line_b.pk).exists()


def test_child_rows_are_contained_for_every_policed_kind(child_rows, two_tenants):
    """One sweep asserting each child table holds exactly two rows overall.

    Counted as the unrestricted owner, so a table that had silently failed to
    receive its fixture rows could not make the per-tenant assertions above
    pass by being empty.
    """
    for _, key in CHILD_KINDS:
        table = child_rows[f"{key}_a"]._meta.db_table
        assert _count(table) == 2, f"{table} did not receive both fixture rows"


def test_every_policed_child_kind_is_exercised(child_rows):
    """Guard the guard: this module covers every child that was given a fix.

    A per-table test that quietly stops being parametrised looks identical to
    one that passes, so the set of children exercised here is asserted against
    the set the migration policed rather than left implicit in a list literal.
    """
    from tests.rls.test_rls_provisioning import (
        DIRECTLY_SCOPED_CHILDREN,
        INDIRECTLY_SCOPED_TABLES,
    )

    exercised = {child_rows[f"{key}_a"]._meta.db_table for _, key in CHILD_KINDS}
    expected = DIRECTLY_SCOPED_CHILDREN | {"advisor_access_grants"}

    assert expected <= exercised, "children policed but never exercised: " + ", ".join(
        sorted(expected - exercised)
    )
    assert exercised <= (DIRECTLY_SCOPED_CHILDREN | INDIRECTLY_SCOPED_TABLES)


# --------------------------------------------------------------------------
# Indirectly-scoped children
# --------------------------------------------------------------------------


def test_advisor_grant_is_visible_only_through_its_engagement(child_rows, two_tenants):
    """An access-control record derives its tenant from its engagement.

    ``advisor_access_grants`` has no ``tenant_id`` of its own and deliberately
    is not given one: its tenancy *is* its engagement, and duplicating it would
    create a second place for the answer to live. The policy reaches the tenant
    with an ``EXISTS`` instead.
    """
    grant_a = child_rows["advisor_grant_a"]
    grant_b = child_rows["advisor_grant_b"]

    with rls_session(tenant=two_tenants["tenant_a"].guid):
        visible = set(AdvisorAccessGrant.objects.values_list("pk", flat=True))
        assert visible == {grant_a.pk}

    with rls_session(tenant=two_tenants["tenant_b"].guid):
        visible = set(AdvisorAccessGrant.objects.values_list("pk", flat=True))
        assert visible == {grant_b.pk}

    with rls_session():
        assert AdvisorAccessGrant.objects.count() == 0


def test_indirect_child_insert_requires_a_parent_in_the_current_tenant(
    child_rows, two_tenants
):
    """``WITH CHECK`` covers the derived tables too, not just their SELECT."""
    engagement_b = child_rows["engagement_b"]
    role_b = child_rows["advisor_grant_b"].tenant_role

    with pytest.raises(Exception) as exc, rls_session(tenant=two_tenants["tenant_a"].guid):
        AdvisorAccessGrant.objects.create(
            engagement=engagement_b,
            practice_user=two_tenants["advisor_a"],
            tenant_role=role_b,
        )

    assert "row-level security policy" in str(exc.value)


# --------------------------------------------------------------------------
# Reconciling a child with its parent
# --------------------------------------------------------------------------


def test_derived_tenant_is_populated_without_the_caller_supplying_it(
    child_rows, two_tenants
):
    """Ordinary callers never choose a child's tenant.

    The fixture builds every child through plain ``objects.create()`` with no
    ``tenant`` argument at all, and the column is populated from the parent.
    This is the convenience half of the design; the composite key is the half
    that holds when the ORM is bypassed.
    """
    expected_parents = {
        "journal_line": "journal_entry_a",
        "document_line": "document_a",
        "attachment": "document_a",
        "extraction": "intelligence_document_a",
    }

    for key, parent_key in expected_parents.items():
        child = child_rows[f"{key}_a"]
        assert child.tenant_id is not None, f"{key} was saved with no tenant"
        # The derived value is the parent's tenant, not merely non-null.
        assert child.tenant_id == child_rows[parent_key].tenant_id
        assert child.tenant_id == two_tenants["tenant_a"].guid


def test_a_child_with_no_parent_cannot_be_saved(two_tenants):
    """A child whose parent is unset raises rather than storing a NULL tenant.

    A NULL ``tenant_id`` matches no policy, so the row would exist and be
    readable by nobody - including the tenant that wrote it. Failing at the
    write is the only point at which that is still debuggable.
    """
    with pytest.raises(ValueError) as exc:
        JournalLine(
            account=two_tenants["account_a1"],
            amount=Decimal("1.0"),
            value=Decimal("1.0"),
        ).save()

    assert "journal_entry" in str(exc.value)


# --------------------------------------------------------------------------
# Entity scope
# --------------------------------------------------------------------------


def test_entity_scope_narrows_child_rows_too(child_rows, two_tenants):
    """Entity context narrows the children, not just their parents.

    Without this, an accountant scoped to one legal entity would still be able
    to read another entity's ledger lines in the same tenant - given the
    document or entry id, which is exactly what a report hands out.
    """
    tenant_a = two_tenants["tenant_a"]

    with rls_session(tenant=tenant_a.guid):
        assert JournalLine.objects.count() == 1

    with rls_session(tenant=tenant_a.guid, entity=two_tenants["entity_a1"].guid):
        assert JournalLine.objects.count() == 1

    # Tenant A's own second entity holds none of these rows, and an entity
    # belonging to another tenant certainly does not.
    with rls_session(tenant=tenant_a.guid, entity=two_tenants["entity_a2"].guid):
        assert JournalLine.objects.count() == 0

    with rls_session(tenant=tenant_a.guid, entity=two_tenants["entity_b1"].guid):
        assert JournalLine.objects.count() == 0


# --------------------------------------------------------------------------
# Failing closed
# --------------------------------------------------------------------------


def test_children_are_invisible_without_tenant_context(child_rows):
    """No context means no rows - on every policed child, not just the parent."""
    with rls_session():
        for model in (JournalLine, DocumentLine, DocumentAttachment, DocumentExtraction):
            assert model.objects.count() == 0
        assert AdvisorAccessGrant.objects.count() == 0
        for _, key in CHILD_KINDS:
            table = child_rows[f"{key}_a"]._meta.db_table
            assert scalar(f"SELECT count(*) FROM {table}") == 0, table


def test_malformed_tenant_context_still_raises_on_a_child_table(child_rows):
    """The fail-loud contract holds on the children as well as the parents."""
    with pytest.raises(Exception) as exc, transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE app_user")
            cursor.execute("SELECT set_config('app.current_tenant_id', 'not-a-uuid', true)")
        JournalLine.objects.count()

    assert "invalid input syntax for type uuid" in str(exc.value)
