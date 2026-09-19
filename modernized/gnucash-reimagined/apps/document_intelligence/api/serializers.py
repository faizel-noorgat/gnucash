"""API serializers for Document Intelligence.

TODO: Implement serializers. Current structure is a stub for migration.

Serializers will handle:
- Document serialization with provenance fields (read-only for immutable fields)
- DocumentExtraction serialization with version history
- DocumentMatch serialization with polymorphic target handling
- AccountingMapping serialization with retirement support
- MappingSuggestion serialization with confidence and evidence
- ReviewQueue serialization with decision workflow

All serializers enforce tenant-scoping via context['tenant_id'].
"""

from __future__ import annotations

from rest_framework import serializers


# Stub serializers — to be implemented


class DocumentSerializer(serializers.Serializer):
    """Serialize Document with full provenance."""

    guid = serializers.UUIDField(read_only=True)
    tenant_id = serializers.UUIDField(read_only=True)
    legal_entity_id = serializers.UUIDField(read_only=True, allow_null=True)

    # Provenance (immutable)
    original_file_key = serializers.CharField(read_only=True)
    content_hash = serializers.CharField(read_only=True)
    mime_type = serializers.CharField(read_only=True)
    original_filename = serializers.CharField(read_only=True)
    size_bytes = serializers.IntegerField(read_only=True)

    # Ingest metadata
    source = serializers.CharField(read_only=True)
    uploaded_at = serializers.DateTimeField(read_only=True)
    uploaded_by = serializers.UUIDField(read_only=True, allow_null=True)

    # Lifecycle
    status = serializers.CharField(read_only=True)

    # Duplicate tracking
    is_duplicate = serializers.BooleanField(read_only=True)
    duplicate_of = serializers.UUIDField(read_only=True, allow_null=True)

    # Downstream linkage
    resulting_accounting_document_id = serializers.UUIDField(
        read_only=True, allow_null=True
    )

    # Audit
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class DocumentUploadSerializer(serializers.Serializer):
    """Deserialize document upload request."""

    file = serializers.FileField()
    source = serializers.CharField(required=False, default="web_upload")


class DocumentExtractionSerializer(serializers.Serializer):
    """Serialize DocumentExtraction with version history."""

    guid = serializers.UUIDField(read_only=True)
    document = serializers.UUIDField(read_only=True)
    version = serializers.IntegerField(read_only=True)

    # OCR provenance
    ocr_provider = serializers.CharField(read_only=True)
    ocr_model_version = serializers.CharField(read_only=True)
    extraction_model_version = serializers.CharField(read_only=True)

    # Structured result
    extraction_result = serializers.JSONField(read_only=True)

    # AI suggestion
    accounting_mapping_used = serializers.UUIDField(read_only=True, allow_null=True)
    ai_suggestion = serializers.JSONField(read_only=True, allow_null=True)
    confidence_score = serializers.DecimalField(
        read_only=True, max_digits=5, decimal_places=4, allow_null=True
    )
    confidence_evidence = serializers.JSONField(read_only=True, allow_null=True)

    # Human review
    is_human_correction = serializers.BooleanField(read_only=True)
    human_correction = serializers.JSONField(read_only=True, allow_null=True)
    correction_note = serializers.CharField(read_only=True)
    reviewed_by = serializers.UUIDField(read_only=True, allow_null=True)
    reviewed_at = serializers.DateTimeField(read_only=True, allow_null=True)

    # Status
    status = serializers.CharField(read_only=True)

    # Downstream
    resulting_accounting_document_id = serializers.UUIDField(
        read_only=True, allow_null=True
    )

    # Timestamps
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class DocumentMatchSerializer(serializers.Serializer):
    """Serialize DocumentMatch with polymorphic target."""

    guid = serializers.UUIDField(read_only=True)
    document = serializers.UUIDField(read_only=True)
    extraction = serializers.UUIDField(read_only=True, allow_null=True)

    kind = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)

    # Polymorphic target (only one populated per kind)
    target_party_id = serializers.UUIDField(read_only=True, allow_null=True)
    target_accounting_document_id = serializers.UUIDField(
        read_only=True, allow_null=True
    )
    target_bank_transaction_id = serializers.UUIDField(read_only=True, allow_null=True)
    target_document_id = serializers.UUIDField(read_only=True, allow_null=True)

    # Provenance
    confidence = serializers.DecimalField(
        read_only=True, max_digits=5, decimal_places=4, allow_null=True
    )
    evidence = serializers.JSONField(read_only=True)

    # Actor
    decided_by = serializers.UUIDField(read_only=True, allow_null=True)
    decided_at = serializers.DateTimeField(read_only=True, allow_null=True)

    # Timestamps
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AccountingMappingSerializer(serializers.Serializer):
    """Serialize AccountingMapping with retirement support."""

    guid = serializers.UUIDField(read_only=True)
    tenant_id = serializers.UUIDField(read_only=True)
    legal_entity_id = serializers.UUIDField(read_only=True, allow_null=True)

    # Trigger conditions
    supplier_party_id = serializers.UUIDField(read_only=True, allow_null=True)
    description_pattern = serializers.CharField(read_only=True)
    amount_range_min = serializers.DecimalField(
        read_only=True, max_digits=20, decimal_places=4, allow_null=True
    )
    amount_range_max = serializers.DecimalField(
        read_only=True, max_digits=20, decimal_places=4, allow_null=True
    )

    # Target
    target_account_id = serializers.UUIDField(read_only=True)
    target_tax_rule_id = serializers.UUIDField(read_only=True, allow_null=True)
    target_dimension_id = serializers.UUIDField(read_only=True, allow_null=True)

    # Governance
    confidence = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    created_by = serializers.UUIDField(read_only=True, allow_null=True)
    approved_by = serializers.UUIDField(read_only=True, allow_null=True)
    approved_at = serializers.DateTimeField(read_only=True, allow_null=True)
    retired_at = serializers.DateTimeField(read_only=True, allow_null=True)
    retired_by = serializers.UUIDField(read_only=True, allow_null=True)
    retirement_reason = serializers.CharField(read_only=True)

    # Timestamps
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class MappingSuggestionSerializer(serializers.Serializer):
    """Serialize MappingSuggestion with confidence and evidence."""

    guid = serializers.UUIDField(read_only=True)
    tenant_id = serializers.UUIDField(read_only=True)
    extraction = serializers.UUIDField(read_only=True)

    # What was suggested
    suggested_account_id = serializers.UUIDField(read_only=True, allow_null=True)
    suggested_tax_rule_id = serializers.UUIDField(read_only=True, allow_null=True)
    suggested_dimension_id = serializers.UUIDField(read_only=True, allow_null=True)
    suggested_party_id = serializers.UUIDField(read_only=True, allow_null=True)

    # Provenance
    source_mapping_ids = serializers.JSONField(read_only=True)
    confidence_score = serializers.DecimalField(
        read_only=True, max_digits=5, decimal_places=4, allow_null=True
    )
    evidence = serializers.JSONField(read_only=True)

    # AI/LLM provenance
    llm_provider = serializers.CharField(read_only=True)
    llm_model_version = serializers.CharField(read_only=True)

    # Lifecycle
    accepted = serializers.BooleanField(read_only=True)
    rejected = serializers.BooleanField(read_only=True)
    decided_by = serializers.UUIDField(read_only=True, allow_null=True)
    decided_at = serializers.DateTimeField(read_only=True, allow_null=True)

    # Timestamp
    created_at = serializers.DateTimeField(read_only=True)


class ReviewQueueSerializer(serializers.Serializer):
    """Serialize ReviewQueue item."""

    guid = serializers.UUIDField(read_only=True)
    tenant_id = serializers.UUIDField(read_only=True)
    document = serializers.UUIDField(read_only=True)
    extraction = serializers.UUIDField(read_only=True)
    suggestion = serializers.UUIDField(read_only=True, allow_null=True)

    status = serializers.CharField(read_only=True)
    priority = serializers.IntegerField(read_only=True)
    reason = serializers.CharField(read_only=True)

    assigned_to = serializers.UUIDField(read_only=True, allow_null=True)
    assigned_at = serializers.DateTimeField(read_only=True, allow_null=True)
    decided_by = serializers.UUIDField(read_only=True, allow_null=True)
    decided_at = serializers.DateTimeField(read_only=True, allow_null=True)

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ReviewDecisionLogSerializer(serializers.Serializer):
    """Serialize ReviewDecisionLog (audit trail)."""

    guid = serializers.UUIDField(read_only=True)
    tenant_id = serializers.UUIDField(read_only=True)
    review_item = serializers.UUIDField(read_only=True)

    decision = serializers.CharField(read_only=True)
    decision_note = serializers.CharField(read_only=True)
    correction_data = serializers.JSONField(read_only=True, allow_null=True)

    decided_by = serializers.UUIDField(read_only=True)
    decided_at = serializers.DateTimeField(read_only=True)

    created_at = serializers.DateTimeField(read_only=True)
