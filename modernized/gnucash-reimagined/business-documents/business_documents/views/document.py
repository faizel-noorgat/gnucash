"""
AccountingDocument views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from business_documents.models import AccountingDocument, DocumentStatus
from business_documents.serializers import (
    AccountingDocumentSerializer,
    AccountingDocumentListSerializer,
    DocumentPostSerializer
)
from business_documents.services.document_posting import DocumentPostingService
from business_documents.permissions import TenantScopedPermission


class AccountingDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AccountingDocument management.

    Provides CRUD operations and posting workflow for invoices, bills, credit notes.
    """
    permission_classes = [TenantScopedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'document_type', 'direction', 'party']
    search_fields = ['document_number', 'reference_number', 'description']
    ordering_fields = ['document_date', 'created_at', 'total']

    def get_queryset(self):
        """Filter documents by tenant"""
        tenant_id = self.request.tenant_id
        return AccountingDocument.objects.filter(tenant_id=tenant_id).select_related('party', 'currency')

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return AccountingDocumentListSerializer
        if self.action == 'post_document':
            return DocumentPostSerializer
        return AccountingDocumentSerializer

    def perform_create(self, serializer):
        """Set tenant and created_by on creation"""
        serializer.save(
            tenant_id=self.request.tenant_id,
            legal_entity_id=self.request.legal_entity_id,
            created_by=self.request.user
        )

    @action(detail=True, methods=['post'])
    def submit_for_approval(self, request, pk=None):
        """Submit document for approval"""
        document = self.get_object()

        if document.status != DocumentStatus.DRAFT:
            return Response(
                {'error': 'Only draft documents can be submitted for approval'},
                status=status.HTTP_400_BAD_REQUEST
            )

        document.status = DocumentStatus.PENDING_APPROVAL
        document.save()

        return Response({'status': 'document submitted for approval'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve document"""
        document = self.get_object()

        if document.status != DocumentStatus.PENDING_APPROVAL:
            return Response(
                {'error': 'Only documents pending approval can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        document.status = DocumentStatus.APPROVED
        document.save()

        return Response({'status': 'document approved'})

    @action(detail=True, methods=['post'])
    def post_document(self, request, pk=None):
        """
        Post document to accounting engine.

        BR-BUS-001: Invoice posting is one-way - once posted, cannot post again.
        """
        document = self.get_object()

        # Validate document can be posted
        if document.is_posted:
            return Response(
                {'error': 'Document has already been posted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not document.can_post():
            return Response(
                {'error': f'Document in {document.status} status cannot be posted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Post document using service
        try:
            with transaction.atomic():
                posting_service = DocumentPostingService()
                journal_entry = posting_service.post_document(document, request.user)

                # Update document status
                document.mark_posted(request.user, journal_entry)

            return Response({
                'status': 'document posted successfully',
                'journal_entry_id': str(journal_entry.guid)
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to post document: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel document"""
        document = self.get_object()

        if not document.can_cancel():
            return Response(
                {'error': f'Document in {document.status} status cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        document.status = DocumentStatus.CANCELLED
        document.save()

        return Response({'status': 'document cancelled'})
