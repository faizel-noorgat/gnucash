"""
DocumentLine views
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from business_documents.models import DocumentLine, AccountingDocument
from business_documents.serializers import DocumentLineSerializer
from business_documents.permissions import TenantScopedPermission


class DocumentLineViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DocumentLine management.

    Provides CRUD operations for line items within accounting documents.
    """
    serializer_class = DocumentLineSerializer
    permission_classes = [TenantScopedPermission]

    def get_queryset(self):
        """Filter lines by document and tenant"""
        document_guid = self.kwargs.get('document_guid')
        tenant_id = self.request.tenant_id

        return DocumentLine.objects.filter(
            document__guid=document_guid,
            document__tenant_id=tenant_id
        )

    def perform_create(self, serializer):
        """Set document on creation"""
        document_guid = self.kwargs.get('document_guid')
        tenant_id = self.request.tenant_id

        try:
            document = AccountingDocument.objects.get(
                guid=document_guid,
                tenant_id=tenant_id
            )
        except AccountingDocument.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Document not found")

        # Check if document can be modified
        if document.is_posted:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot modify lines on a posted document")

        # Auto-assign line number
        max_line_number = document.lines.aggregate(
            max_num=models.Max('line_number')
        )['max_num'] or 0

        serializer.save(document=document, line_number=max_line_number + 1)

        # Update document totals
        document.calculate_totals()

    def perform_update(self, serializer):
        """Update line and recalculate document totals"""
        line = self.get_object()

        # Check if document can be modified
        if line.document.is_posted:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot modify lines on a posted document")

        serializer.save()

        # Update document totals
        line.document.calculate_totals()

    def perform_destroy(self, instance):
        """Delete line and recalculate document totals"""
        document = instance.document

        # Check if document can be modified
        if document.is_posted:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot modify lines on a posted document")

        instance.delete()

        # Update document totals
        document.calculate_totals()
