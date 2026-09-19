-- PostgreSQL Triggers for Journal Immutability Enforcement
-- ADR-010: Database-level enforcement of posted journal immutability
--
-- These triggers prevent UPDATE/DELETE on posted financial records
-- at the database layer, providing defense-in-depth with application-layer guards.
--
-- IMPORTANT: CHECK constraints cannot enforce this because they validate
-- row values and cannot compare OLD vs NEW state.

-- Prevent UPDATE on posted journal entries
CREATE OR REPLACE FUNCTION prevent_posted_journal_entry_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if the OLD row was posted
    IF OLD.is_posted = TRUE THEN
        RAISE EXCEPTION 'Cannot modify posted journal entry %. Use reversal or correcting entry workflow instead.',
            OLD.guid
            USING ERRCODE = 'P0001',
                  HINT = 'Create a reversal or correcting entry to modify posted financial records.';
    END IF;

    -- Allow the update if not posted
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Prevent DELETE on posted journal entries
CREATE OR REPLACE FUNCTION prevent_posted_journal_entry_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_posted = TRUE THEN
        RAISE EXCEPTION 'Cannot delete posted journal entry %. Use void workflow (creates reversal) instead.',
            OLD.guid
            USING ERRCODE = 'P0001',
                  HINT = 'Use the void workflow which creates a reversal entry instead of deleting.';
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Prevent UPDATE on journal lines of posted entries
CREATE OR REPLACE FUNCTION prevent_posted_journal_line_update()
RETURNS TRIGGER AS $$
DECLARE
    v_is_posted BOOLEAN;
BEGIN
    -- Check if the parent journal entry is posted
    SELECT is_posted INTO v_is_posted
    FROM accounting_engine_journalentry
    WHERE guid = OLD.journal_entry_id;

    IF v_is_posted = TRUE THEN
        RAISE EXCEPTION 'Cannot modify journal line % of posted journal entry %. Use reversal or correcting entry workflow instead.',
            OLD.guid,
            OLD.journal_entry_id
            USING ERRCODE = 'P0001',
                  HINT = 'Create a reversal or correcting entry to modify posted financial records.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Prevent DELETE on journal lines of posted entries
CREATE OR REPLACE FUNCTION prevent_posted_journal_line_delete()
RETURNS TRIGGER AS $$
DECLARE
    v_is_posted BOOLEAN;
BEGIN
    SELECT is_posted INTO v_is_posted
    FROM accounting_engine_journalentry
    WHERE guid = OLD.journal_entry_id;

    IF v_is_posted = TRUE THEN
        RAISE EXCEPTION 'Cannot delete journal line % of posted journal entry %. Use void workflow instead.',
            OLD.guid,
            OLD.journal_entry_id
            USING ERRCODE = 'P0001',
                  HINT = 'Use the void workflow which creates a reversal entry instead of deleting.';
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Prevent UPDATE on immutable posted journal entries (snapshot table)
CREATE OR REPLACE FUNCTION prevent_immutable_journal_entry_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Cannot modify immutable posted journal entry %. This data is permanently frozen.',
        OLD.guid
        USING ERRCODE = 'P0001',
              HINT = 'Immutable posted journal entries cannot be modified. Create a new entry if needed.';
END;
$$ LANGUAGE plpgsql;

-- Prevent UPDATE on immutable posted journal lines (snapshot table)
CREATE OR REPLACE FUNCTION prevent_immutable_journal_line_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Cannot modify immutable posted journal line %. This data is permanently frozen.',
        OLD.guid
        USING ERRCODE = 'P0001',
              HINT = 'Immutable posted journal lines cannot be modified. Create a new entry if needed.';
END;
$$ LANGUAGE plpgsql;

-- Prevent deletion of audit events
CREATE OR REPLACE FUNCTION prevent_audit_event_deletion()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Cannot delete audit events. Audit trail is immutable.'
        USING ERRCODE = 'P0001',
              HINT = 'Audit events are permanently preserved for compliance.';
END;
$$ LANGUAGE plpgsql;

-- Create triggers for journal entries
DROP TRIGGER IF EXISTS trg_prevent_posted_journal_entry_update ON accounting_engine_journalentry;
CREATE TRIGGER trg_prevent_posted_journal_entry_update
    BEFORE UPDATE ON accounting_engine_journalentry
    FOR EACH ROW
    EXECUTE FUNCTION prevent_posted_journal_entry_update();

DROP TRIGGER IF EXISTS trg_prevent_posted_journal_entry_delete ON accounting_engine_journalentry;
CREATE TRIGGER trg_prevent_posted_journal_entry_delete
    BEFORE DELETE ON accounting_engine_journalentry
    FOR EACH ROW
    EXECUTE FUNCTION prevent_posted_journal_entry_delete();

-- Create triggers for journal lines
DROP TRIGGER IF EXISTS trg_prevent_posted_journal_line_update ON accounting_engine_journalline;
CREATE TRIGGER trg_prevent_posted_journal_line_update
    BEFORE UPDATE ON accounting_engine_journalline
    FOR EACH ROW
    EXECUTE FUNCTION prevent_posted_journal_line_update();

DROP TRIGGER IF EXISTS trg_prevent_posted_journal_line_delete ON accounting_engine_journalline;
CREATE TRIGGER trg_prevent_posted_journal_line_delete
    BEFORE DELETE ON accounting_engine_journalline
    FOR EACH ROW
    EXECUTE FUNCTION prevent_posted_journal_line_delete();

-- Create triggers for audit events (immutable)
DROP TRIGGER IF EXISTS trg_prevent_audit_event_deletion ON accounting_engine_auditevent;
CREATE TRIGGER trg_prevent_audit_event_deletion
    BEFORE DELETE ON accounting_engine_auditevent
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_event_deletion();

-- Note: Immutable snapshot tables (accounting_engine_immutable_posted_journal_entry
-- and accounting_engine_immutable_posted_journal_line) would have triggers if they
-- were actual tables. Since they're managed=False views, the main table triggers
-- provide the enforcement.
