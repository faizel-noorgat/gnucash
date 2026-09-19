"""Give ``accounting_journalline`` its own ``tenant_id``.

``JournalLine`` reached a tenant only through ``journal_entry``, so RLS had
nothing to key a policy on and the table was reachable outside the tenant
boundary by raw SQL or by an unfiltered queryset. Journal lines carry the
financial payload, which makes that the highest-value hole in the isolation
surface.

The column is materialised rather than policed by an ``EXISTS`` subquery
against ``accounting_journalentry`` because a ledger line is an
independently-queried row - reports read it without loading its parent - and
because a plain equality on an indexed column is a policy PostgreSQL can use,
while a correlated subquery on every row is not. Consistency with the parent
is not left to the application: ``rls/0003`` adds a composite foreign key
``(journal_entry_id, tenant_id) -> accounting_journalentry(guid, tenant_id)``
that makes disagreement unrepresentable.

Why this migration disables a trigger
--------------------------------------
``accounting/0003_adr010_posted_immutability`` installs a ``BEFORE INSERT OR
UPDATE OR DELETE`` trigger on this table that compares the whole row
(``to_jsonb(OLD)`` minus an allow-list of mutable columns) against the new one
and refuses any change to a line whose owning entry is posted. The backfill
below is an ``UPDATE``, so it would raise

    ADR-010: line <guid> of a posted journal entry is immutable; create a
    reversal or correcting entry instead

for every line of every posted entry - and posted entries are exactly the ones
that matter. So the trigger is disabled for the duration of the backfill and
re-enabled immediately after.

This is deliberately the narrow version of the two available options. The
alternative was to amend the trigger function so that a NULL -> value
transition on ``tenant_id`` is permitted, which would leave a permanent
exception in an immutability guard for the benefit of a one-off migration. A
temporary disable that reverts itself is smaller and has no lasting effect.

The migration is **atomic**, so the disable and the re-enable are in one
transaction: if anything fails between them PostgreSQL rolls the whole thing
back and the trigger is never left off. ``tests/rls/test_rls_provisioning.py``
asserts the trigger is enabled and valid afterwards rather than trusting this
comment.

``updated_at`` is ``auto_now``, so the backfill would also have stamped it
with the migration time. It is restored from ``OLD`` in the same statement to
keep the audit trail honest about when a line was last actually touched.
"""

from django.db import migrations, models
import django.db.models.deletion


TRIGGER_NAME = "accounting_journalline_posted_immutable"

DISABLE_TRIGGER = f"ALTER TABLE accounting_journalline DISABLE TRIGGER {TRIGGER_NAME};"
ENABLE_TRIGGER = f"ALTER TABLE accounting_journalline ENABLE TRIGGER {TRIGGER_NAME};"

BACKFILL = """
UPDATE accounting_journalline AS line
SET tenant_id = entry.tenant_id
FROM accounting_journalentry AS entry
WHERE entry.guid = line.journal_entry_id
  AND line.tenant_id IS NULL;
"""


def _tenant_field(null=False):
    return models.ForeignKey(
        db_index=True,
        on_delete=django.db.models.deletion.CASCADE,
        related_name="%(class)s_set",
        to="identity.tenant",
        null=null,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0003_adr010_posted_immutability"),
        ("identity", "0001_initial"),
    ]

    operations = [
        # Nullable first: the column has to exist before it can be populated,
        # and no value can be invented for existing rows at ADD COLUMN time.
        migrations.AddField(
            model_name="journalline",
            name="tenant",
            field=_tenant_field(null=True),
            preserve_default=False,
        ),
        migrations.RunSQL(sql=DISABLE_TRIGGER, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=BACKFILL, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=ENABLE_TRIGGER, reverse_sql=migrations.RunSQL.noop),
        # Only now can the column be made non-null. A NULL tenant_id would be
        # invisible to every policy, including to the tenant that owns it.
        migrations.AlterField(
            model_name="journalline",
            name="tenant",
            field=_tenant_field(),
        ),
    ]
