"""Serializers for Document Intelligence API."""

from __future__ import annotations

from rest_framework import serializers

from ..models import (
    AccountingMapping,
    Document,
    DocumentExtraction,
    DocumentMatch,
    MappingSuggestion,
    ReviewQueue,
)


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "guid",
            "tenant_id",
            "legal_entity_id",
            "original_file_key",
            "content_hash",
            "mime_type",
            "original_filename",
            "size_bytes",
            "source",
            "uploaded_at",
            "uploaded_by",
            "status",
            "is_duplicate",
            "duplicate_of",
            "resulting_accounting_document_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "guid",
            "original_file_key",
            "content_hash",
            "uploaded_at",
            "created_at",
            "updated_at",
        ]


class DocumentExtractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentExtraction
        fields = [
            "guid",
            "document",
            "version",
            "ocr_provider",
            "ocr_model_version",
            "extraction_model_version",
            "extraction_result",
            "accounting_mapping_used",
            "ai_suggestion",
            "confidence_score",
            "confidence_evidence",
            "is_human_correction",
            "human_correction",
            "correction_note",
            "reviewed_by",
            "reviewed_at",
            "status",
            "resulting_accounting_document_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "guid",
            "document",
            "version",
            "created_at",
            "updated_at",
        ]


class DocumentMatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentMatch
        fields = [
            "guid",
            "document",
            "extraction",
            "kind",
            "status",
            "target_party_id",
            "target_accounting_document_id",
            "target_bank_transaction_id",
            "target_document_id",
            "confidence",
            "evidence",
            "decided_by",
            "decided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "guid",
            "document",
            "extraction",
            "created_at",
            "updated_at",
        ]


class AccountingMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountingMapping
        fields = [
            "guid",
            "tenant_id",
            "legal_entity_id",
            "supplier_party_id",
            "description_pattern",
            "amount_range_min",
            "amount_range_max",
            "target_account_id",
            "target_tax_rule_id",
            "target_dimension_id",
            "confidence",
            "is_active",
            "created_by",
            "approved_by",
            "approved_at",
            "retired_at",
            "retired_by",
            "retirement_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "guid",
            "created_at",
            "updated_at",
        ]


class MappingSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MappingSuggestion
        fields = [
            "guid",
            "tenant_id",
            "extraction",
            "suggested_account_id",
            "suggested_tax_rule_id",
            "suggested_dimension_id",
            "suggested_party_id",
            "source_mapping_ids",
            "confidence_score",
            "evidence",
            "llm_provider",
            "llm_model_version",
            "accepted",
            "rejected",
            "decided_by",
            "decided_at",
            "created_at",
        ]
        read_only_fields = [
            "guid",
            "created_at",
        ]


class ReviewQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewQueue
        fields = [
            "guid",
            "tenant_id",
            "document",
            "extraction",
            "suggestion",
            "status",
            "priority",
            "reason",
            "assigned_to",
            "assigned_at",
            "decided_by",
            "decided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "guid",
            "created_at",
            "updated_at",
        ]
