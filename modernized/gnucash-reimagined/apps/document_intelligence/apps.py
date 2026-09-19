"""
Document Intelligence bounded context.

Owns: uploaded Document, DocumentExtraction, DocumentMatch,
      AccountingMapping, MappingSuggestion, review workflow, OCR/AI provenance
"""

from django.apps import AppConfig


class DocumentIntelligenceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.document_intelligence"
    label = "document_intelligence"
    verbose_name = "Document Intelligence"
