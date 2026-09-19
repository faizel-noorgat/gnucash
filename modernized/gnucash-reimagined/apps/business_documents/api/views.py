"""
API views for business_documents
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.business_documents.models import (
    Party,
    AccountingDocument,
    DocumentLine,
    DocumentAttachment,
    ApprovalWorkflow,
)


class PartyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing parties (customers, vendors, employees).
    """
    # TODO: Implement queryset, serializer_class, permissions
    pass


class AccountingDocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing accounting documents (invoices, bills, credit notes).
    """
    # TODO: Implement queryset, serializer_class, permissions

    @action(detail=True, methods=['post'])
    def post_document(self, request, pk=None):
        """
        Post an accounting document to the accounting engine.
        Creates a journal entry and marks document as posted (immutable).
        """
        # TODO: Implement posting logic using DocumentPostingService
        return Response({'status': 'not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED)


class DocumentLineViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing document line items.
    """
    # TODO: Implement queryset, serializer_class, permissions
    pass


class DocumentAttachmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing document attachments.
    """
    # TODO: Implement queryset, serializer_class, permissions
    pass


class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing approval workflows.
    """
    # TODO: Implement queryset, serializer_class, permissions
    pass
