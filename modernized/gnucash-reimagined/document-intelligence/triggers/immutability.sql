-- PostgreSQL triggers for immutability enforcement.
--
-- These triggers provide database-level enforcement of the immutability
-- invariants for Document Intelligence (BR-DI-001, BR-DI-002, BR-DI-003, BR-DI-009).
--
-- NOTE: CHECK constraints validate row values but CANNOT compare OLD vs NEW.
-- For immutability of specific columns after initial insert, we need
-- BEFORE UPDATE triggers.

-- ===========================================================================
-- Trigger 1: Document immutability
-- ===========================================================================
-- These columns are IMMUTABLE after insert:
--   original_file_key, content_hash, mime_type, original_filename,
--   size_bytes, uploaded_at, uploaded_by, tenant_id

CREATE OR REPLACE FUNCTION enforce_document_immutability()
RETURNS TRIGGER AS $$
BEGIN
    -- If any immutable field has changed, reject the UPDATE
    IF NEW.original_file_key IS DISTINCT FROM OLD.original_file_key THEN
        RAISE EXCEPTION 'BR-DI-002: original_file_key is immutable'
            USING HINT = 'The original object-storage reference cannot be changed after upload.';
    END IF;

    IF NEW.content_hash IS DISTINCT FROM OLD.content_hash THEN
        RAISE EXCEPTION 'BR-DI-001: content_hash is immutable'
            USING HINT = 'The SHA-256 content hash cannot be changed after upload.';
    END IF;

    IF NEW.mime_type IS DISTINCT FROM OLD.mime_type THEN
        RAISE EXCEPTION 'mime_type is immutable'
            USING HINT = 'The MIME type cannot be changed after upload.';
    END IF;

    IF NEW.original_filename IS DISTINCT FROM OLD.original_filename THEN
        RAISE EXCEPTION 'original_filename is immutable'
            USING HINT = 'The original filename cannot be changed after upload.';
    END IF;

    IF NEW.size_bytes IS DISTINCT FROM OLD.size_bytes THEN
        RAISE EXCEPTION 'size_bytes is immutable'
            USING HINT = 'The file size cannot be changed after upload.';
    END IF;

    IF NEW.uploaded_at IS DISTINCT FROM OLD.uploaded_at THEN
        RAISE EXCEPTION 'uploaded_at is immutable'
            USING HINT = 'The upload timestamp cannot be changed after upload.';
    END IF;

    IF NEW.uploaded_by IS DISTINCT FROM OLD.uploaded_by THEN
        RAISE EXCEPTION 'uploaded_by is immutable'
            USING HINT = 'The uploader cannot be changed after upload.';
    END IF;

    IF NEW.tenant_id IS DISTINCT FROM OLD.tenant_id THEN
        RAISE EXCEPTION 'tenant_id is immutable'
            USING HINT = 'The tenant_id cannot be changed (RLS isolation).';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_document_immutability ON documents;
CREATE TRIGGER trg_document_immutability
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION enforce_document_immutability();


-- ===========================================================================
-- Trigger 2: DocumentExtraction immutability
-- ===========================================================================
-- These columns are IMMUTABLE after insert:
--   document_id, version, ocr_provider, ocr_model_version,
--   extraction_model_version, extraction_result, ai_suggestion,
--   confidence_score, confidence_evidence, is_human_correction
--
-- Mutable columns:
--   status (forward-only state machine), human_correction, correction_note,
--   reviewed_by, reviewed_at, resulting_accounting_document_id

CREATE OR REPLACE FUNCTION enforce_extraction_immutability()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.document_id IS DISTINCT FROM OLD.document_id THEN
        RAISE EXCEPTION 'BR-DI-003: extraction document_id is immutable';
    END IF;

    IF NEW.version IS DISTINCT FROM OLD.version THEN
        RAISE EXCEPTION 'BR-DI-003: extraction version is immutable';
    END IF;

    IF NEW.ocr_provider IS DISTINCT FROM OLD.ocr_provider THEN
        RAISE EXCEPTION 'BR-DI-009: ocr_provider is immutable'
            USING HINT = 'Create a new extraction version instead of mutating.';
    END IF;

    IF NEW.ocr_model_version IS DISTINCT FROM OLD.ocr_model_version THEN
        RAISE EXCEPTION 'BR-DI-009: ocr_model_version is immutable';
    END IF;

    IF NEW.extraction_model_version IS DISTINCT FROM OLD.extraction_model_version THEN
        RAISE EXCEPTION 'BR-DI-009: extraction_model_version is immutable';
    END IF;

    IF NEW.extraction_result IS DISTINCT FROM OLD.extraction_result THEN
        RAISE EXCEPTION 'BR-DI-009: extraction_result is immutable'
            USING HINT = 'Human corrections must create a new extraction version.';
    END IF;

    IF NEW.ai_suggestion IS DISTINCT FROM OLD.ai_suggestion THEN
        RAISE EXCEPTION 'BR-DI-009: ai_suggestion is immutable';
    END IF;

    IF NEW.confidence_score IS DISTINCT FROM OLD.confidence_score THEN
        RAISE EXCEPTION 'BR-DI-009: confidence_score is immutable';
    END IF;

    IF NEW.confidence_evidence IS DISTINCT FROM OLD.confidence_evidence THEN
        RAISE EXCEPTION 'BR-DI-009: confidence_evidence is immutable';
    END IF;

    IF NEW.is_human_correction IS DISTINCT FROM OLD.is_human_correction THEN
        RAISE EXCEPTION 'BR-DI-003: is_human_correction is immutable';
    END IF;

    -- Validate status transition (forward-only state machine)
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        IF OLD.status = 'completed' AND NEW.status NOT IN ('completed', 'rejected') THEN
            RAISE EXCEPTION 'Invalid extraction status transition: % -> %',
                OLD.status, NEW.status;
        END IF;
        IF OLD.status = 'rejected' AND NEW.status != 'rejected' THEN
            RAISE EXCEPTION 'Invalid extraction status transition: % -> %',
                OLD.status, NEW.status;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_extraction_immutability ON document_extractions;
CREATE TRIGGER trg_extraction_immutability
    BEFORE UPDATE ON document_extractions
    FOR EACH ROW
    EXECUTE FUNCTION enforce_extraction_immutability();


-- ===========================================================================
-- Trigger 3: DocumentExtraction DELETE prevention
-- ===========================================================================
-- Extractions are append-only; DELETE is never allowed.

CREATE OR REPLACE FUNCTION prevent_extraction_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'BR-DI-003/BR-DI-009: DocumentExtraction rows cannot be deleted'
        USING HINT = 'Extraction history is append-only for audit trail.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_extraction_delete ON document_extractions;
CREATE TRIGGER trg_prevent_extraction_delete
    BEFORE DELETE ON document_extractions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_extraction_delete();


-- ===========================================================================
-- Trigger 4: Row Level Security (RLS) for tenant isolation (BR-DI-010)
-- ===========================================================================
-- All tables must have RLS enabled and policies referencing app.tenant_id

-- (Applied via Django migrations; this file documents the policy pattern)

-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE documents FORCE ROW LEVEL SECURITY;
--
-- CREATE POLICY tenant_isolation ON documents
--     USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ALTER TABLE document_extractions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE document_extractions FORCE ROW LEVEL SECURITY;
--
-- CREATE POLICY tenant_isolation ON document_extractions
--     USING (document_id IN (
--         SELECT guid FROM documents
--         WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
--     ));

-- Similar policies for document_matches, accounting_mappings, etc.
