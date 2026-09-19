"""
DocumentAttachment views
"""
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import FileResponse
from business_documents.models import DocumentAttachment, AccountingDocument
from business_documents.serializers import DocumentAttachmentSerializer, DocumentAttachmentUploadSerializer
from business_documents.services.storage import StorageService
from business_documents.permissions import TenantScopedPermission
import hashlib


class DocumentAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DocumentAttachment management.

    Provides upload and download operations for document attachments.
    """
    serializer_class = DocumentAttachmentSerializer
    permission_classes = [TenantScopedPermission]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        """Filter attachments by document and tenant"""
        document_guid = self.kwargs.get('document_guid')
        tenant_id = self.request.tenant_id

        return DocumentAttachment.objects.filter(
            document__guid=document_guid,
            document__tenant_id=tenant_id
        )

    def create(self, request, *args, **kwargs):
        """Upload attachment"""
        document_guid = self.kwargs.get('document_guid')
        tenant_id = request.tenant_id

        try:
            document = AccountingDocument.objects.get(
                guid=document_guid,
                tenant_id=tenant_id
            )
        except AccountingDocument.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate file
        serializer = DocumentAttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data['file']
        description = serializer.validated_data.get('description', '')

        # Calculate content hash
        content_hash = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            content_hash.update(chunk)
        content_hash = content_hash.hexdigest()

        # Upload to storage
        storage_service = StorageService()
        storage_key = storage_service.upload_file(
            file=uploaded_file,
            tenant_id=tenant_id,
            document_guid=document_guid
        )

        # Create attachment record
        attachment = DocumentAttachment.objects.create(
            document=document,
            filename=uploaded_file.name,
            content_type=uploaded_file.content_type,
            size=uploaded_file.size,
            storage_key=storage_key,
            content_hash=content_hash,
            description=description,
            uploaded_by=request.user
        )

        # Return attachment details
        output_serializer = DocumentAttachmentSerializer(attachment)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None, document_guid=None):
        """Download attachment"""
        attachment = self.get_object()

        # Get file from storage
        storage_service = StorageService()
        file_stream = storage_service.download_file(attachment.storage_key)

        response = FileResponse(
            file_stream,
            content_type=attachment.content_type,
            as_attachment=True,
            filename=attachment.filename
        )

        return response
