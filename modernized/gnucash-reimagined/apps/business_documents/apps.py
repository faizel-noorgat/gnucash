"""
Business Documents bounded context.

Owns: Party, AccountingDocument, DocumentLine/InvoiceLine, approvals,
      commercial-document lifecycle
"""

from django.apps import AppConfig


class BusinessDocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.business_documents"
    label = "business_documents"
    verbose_name = "Business Documents"
