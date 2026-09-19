"""
ADR-010: enforce posted-journal immutability in PostgreSQL.

The application layer already refuses to mutate posted journals
(``JournalEntry.clean`` / ``JournalLine.clean``), but that only covers paths
that go through ``Model.save()``. ``QuerySet.update()``, bulk operations, raw
SQL, and data-fix scripts bypass it entirely. This migration makes PostgreSQL
the final enforcement boundary.

Protected: ``accounting_journalentry`` and ``accounting_journalline``.

Not protected, deliberately:

* ``accounting_transactionmetadata`` - review state, comments and external
  references are operational and must stay mutable after posting.
* ``accounting_immutable_posted_journal_entry`` /
  ``accounting_immutable_posted_journal_line`` - these models declare
  ``managed = False``, so no such tables exist. Their intended role (a
  separate immutable snapshot table) is currently unimplemented; this
  migration protects the live tables instead.

Design notes:
* The protected/unprotected split is expressed as an ALLOW-LIST of mutable
  columns, and the comparison is done over the whole row (``to_jsonb(OLD)``
  minus the mutable keys vs the same for ``NEW``). Any column added later is
  therefore protected by default rather than silently unprotected.
* ``BEFORE INSERT`` is also guarded on lines: adding a line to an entry that is
  already posted changes the financial result just as much as editing one, and
  a UPDATE/DELETE-only trigger would miss it entirely.
* There is no bypass flag, no session-variable escape hatch and no
  ``force=True``. Corrections go through reversal / correcting entries, which
  create new rows rather than mutating posted ones.
"""

from django.db import migrations

# Columns that remain mutable after posting, per table. Everything else is frozen.
MUTABLE_ENTRY_COLUMNS = ["updated_at"]

MUTABLE_LINE_COLUMNS = [
    "updated_at",
    # Reconciliation metadata: reconciliation happens *after* posting, so these
    # must stay writable or the normal bank-reconciliation workflow breaks.
    "reconcile_status",
    "date_reconciled",
    "online_id",
]


def _jsonb_minus(columns):
    """Build the SQL fragment `to_jsonb(<row>) - 'a' - 'b' ...` for a column list."""
    return "".join(f" - '{column}'" for column in columns)


FORWARD_SQL = f"""
-- ---------------------------------------------------------------------------
-- Journal entries: once posted, frozen except for {MUTABLE_ENTRY_COLUMNS}.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION accounting_forbid_posted_entry_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.is_posted IS TRUE THEN
            RAISE EXCEPTION
                'ADR-010: posted journal entry % cannot be deleted; create a reversal instead',
                OLD.guid
                USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN OLD;
    END IF;

    -- An entry that was not already posted is ordinary, editable data.
    IF OLD.is_posted IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    -- BR-BUS-001: posting is one-way. Give this its own message because it is
    -- the most likely thing a caller will try.
    IF NEW.is_posted IS NOT TRUE THEN
        RAISE EXCEPTION
            'BR-BUS-001: posted journal entry % cannot be un-posted; create a reversal or correcting entry instead',
            OLD.guid
            USING ERRCODE = 'restrict_violation';
    END IF;

    -- Everything except the mutable operational columns is frozen.
    IF (to_jsonb(OLD){_jsonb_minus(MUTABLE_ENTRY_COLUMNS)})
       IS DISTINCT FROM
       (to_jsonb(NEW){_jsonb_minus(MUTABLE_ENTRY_COLUMNS)})
    THEN
        RAISE EXCEPTION
            'ADR-010: posted journal entry % is immutable; create a reversal or correcting entry instead',
            OLD.guid
            USING ERRCODE = 'restrict_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER accounting_journalentry_posted_immutable
BEFORE UPDATE OR DELETE ON accounting_journalentry
FOR EACH ROW EXECUTE FUNCTION accounting_forbid_posted_entry_mutation();

-- ---------------------------------------------------------------------------
-- Journal lines: protected whenever the OWNING entry is posted.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION accounting_forbid_posted_line_mutation()
RETURNS TRIGGER AS $$
DECLARE
    old_parent_posted boolean;
    new_parent_posted boolean;
BEGIN
    IF TG_OP = 'DELETE' THEN
        SELECT is_posted INTO old_parent_posted
        FROM accounting_journalentry WHERE guid = OLD.journal_entry_id;

        IF old_parent_posted IS TRUE THEN
            RAISE EXCEPTION
                'ADR-010: line % of a posted journal entry cannot be deleted; create a reversal instead',
                OLD.guid
                USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN OLD;
    END IF;

    IF TG_OP = 'INSERT' THEN
        SELECT is_posted INTO new_parent_posted
        FROM accounting_journalentry WHERE guid = NEW.journal_entry_id;

        IF new_parent_posted IS TRUE THEN
            RAISE EXCEPTION
                'ADR-010: cannot add line % to posted journal entry %; create a reversal or correcting entry instead',
                NEW.guid, NEW.journal_entry_id
                USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN NEW;
    END IF;

    -- UPDATE. Both the old and the new parent are checked, so a line cannot be
    -- smuggled out of a posted entry by re-pointing it at a draft one.
    SELECT is_posted INTO old_parent_posted
    FROM accounting_journalentry WHERE guid = OLD.journal_entry_id;
    SELECT is_posted INTO new_parent_posted
    FROM accounting_journalentry WHERE guid = NEW.journal_entry_id;

    IF old_parent_posted IS NOT TRUE AND new_parent_posted IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    IF (to_jsonb(OLD){_jsonb_minus(MUTABLE_LINE_COLUMNS)})
       IS DISTINCT FROM
       (to_jsonb(NEW){_jsonb_minus(MUTABLE_LINE_COLUMNS)})
    THEN
        RAISE EXCEPTION
            'ADR-010: line % of a posted journal entry is immutable; create a reversal or correcting entry instead',
            OLD.guid
            USING ERRCODE = 'restrict_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER accounting_journalline_posted_immutable
BEFORE INSERT OR UPDATE OR DELETE ON accounting_journalline
FOR EACH ROW EXECUTE FUNCTION accounting_forbid_posted_line_mutation();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS accounting_journalline_posted_immutable ON accounting_journalline;
DROP TRIGGER IF EXISTS accounting_journalentry_posted_immutable ON accounting_journalentry;
DROP FUNCTION IF EXISTS accounting_forbid_posted_line_mutation();
DROP FUNCTION IF EXISTS accounting_forbid_posted_entry_mutation();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
