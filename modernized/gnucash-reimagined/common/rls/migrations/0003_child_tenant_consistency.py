"""Make a child's ``tenant_id`` impossible to disagree with its parent's.

Five tables now carry their own ``tenant_id`` while still being owned by a
parent row - journal lines, document lines, document attachments, extractions
and matches. That gives RLS a plain column to key on, but it also creates a way
to be wrong that did not exist before: a child marked as belonging to tenant A
while its parent belongs to tenant B. Written naively, that is a row that one
tenant can read and the other owns.

The mechanism
-------------
A **composite foreign key**::

    FOREIGN KEY (parent_id, tenant_id) REFERENCES parent (guid, tenant_id)

PostgreSQL will only accept a child row when a parent row exists with that
``guid`` *and* that ``tenant_id``, which is exactly the invariant. It is
declarative - it lives in the catalogue next to the other constraints, not in a
trigger or in application code - and it is checked on every INSERT and every
UPDATE of either column, including from raw SQL that never went near the ORM.

Why not a trigger
-----------------
A ``BEFORE INSERT OR UPDATE`` trigger could do the same job, and would
additionally allow the parent lookup to *fill the column in*. It was rejected
because a trigger that silently rewrites a caller-supplied ``tenant_id``
converts an application bug into a successful write with different data. The
composite key rejects the write instead, loudly, at the point of the mistake.
The application-side half - ``TenantDerivedChildModel.derive_tenant_id()`` -
fills the column in for callers that go through ``save()``, so ordinary code
never chooses a tenant at all and never sees the error.

Why the parent gets a UNIQUE constraint
---------------------------------------
A composite foreign key needs a unique constraint on the referenced columns.
``(guid, tenant_id)`` is trivially unique because ``guid`` is already the
primary key - so this adds no real constraint, only the index PostgreSQL needs
to check the reference. That redundant index is the one cost of this design.

``ON DELETE CASCADE`` mirrors the ``on_delete=models.CASCADE`` the models
declare, so a raw ``DELETE`` of a parent behaves the way the ORM says it does
rather than failing on a reference the ORM would have cleaned up itself.

Reverse
-------
Drops the constraints and their indexes. The ``tenant_id`` columns themselves
belong to the app migrations and are dropped by reversing those.
"""

from django.db import migrations

#: (child table, child FK column, parent table). Every pair is
#: ``ON DELETE CASCADE``, matching the models.
CHILD_PARENTS = [
    ("accounting_journalline", "journal_entry_id", "accounting_journalentry"),
    (
        "business_documents_document_line",
        "document_id",
        "business_documents_accounting_document",
    ),
    (
        "business_documents_document_attachment",
        "document_id",
        "business_documents_accounting_document",
    ),
    ("document_extractions", "document_id", "documents"),
    ("document_matches", "document_id", "documents"),
]


def _unique_name(parent: str) -> str:
    return f"{parent}_guid_tenant_uniq"


def _fk_name(child: str) -> str:
    return f"{child}_parent_tenant_fk"


def _index_name(child: str) -> str:
    return f"{child}_parent_tenant_idx"


def _apply_sql() -> str:
    statements = []

    # One UNIQUE per parent, even though two children may share a parent.
    for parent in sorted({parent for _, _, parent in CHILD_PARENTS}):
        statements.append(
            f"ALTER TABLE {parent} ADD CONSTRAINT {_unique_name(parent)} "
            f"UNIQUE (guid, tenant_id);"
        )

    for child, fk_column, parent in CHILD_PARENTS:
        statements.append(
            f"ALTER TABLE {child} ADD CONSTRAINT {_fk_name(child)} "
            f"FOREIGN KEY ({fk_column}, tenant_id) "
            f"REFERENCES {parent} (guid, tenant_id) ON DELETE CASCADE;"
        )
        # PostgreSQL does not create an index for the referencing side of a
        # foreign key. Without this, every cascade delete from a parent
        # sequentially scans the child table.
        statements.append(
            f"CREATE INDEX {_index_name(child)} ON {child} ({fk_column}, tenant_id);"
        )

    return "\n".join(statements)


def _revert_sql() -> str:
    statements = []
    for child, _fk_column, parent in CHILD_PARENTS:
        statements.append(f"DROP INDEX IF EXISTS {_index_name(child)};")
        statements.append(
            f"ALTER TABLE {child} DROP CONSTRAINT IF EXISTS {_fk_name(child)};"
        )
    for parent in sorted({parent for _, _, parent in CHILD_PARENTS}):
        statements.append(
            f"ALTER TABLE {parent} DROP CONSTRAINT IF EXISTS {_unique_name(parent)};"
        )
    return "\n".join(statements)


class Migration(migrations.Migration):
    dependencies = [
        ("rls", "0002_rls_tenant_isolation_policies"),
        # The columns this constraint spans must exist first. Each of these
        # migrations adds a nullable column, backfills it and makes it NOT NULL.
        ("accounting", "0004_journalline_tenant"),
        ("business_documents", "0004_document_children_tenant"),
        ("document_intelligence", "0002_extraction_and_match_tenant"),
    ]

    operations = [
        migrations.RunSQL(sql=_apply_sql(), reverse_sql=_revert_sql()),
    ]
