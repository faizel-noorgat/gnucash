"""API views for Document Intelligence."""

from __future__ import annotations

import uuid

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    AccountingMapping,
    Document,
    DocumentExtraction,
    DocumentMatch,
    DocumentSource,
    ReviewQueue,
)
from ..providers.storage import get_storage_client
from .serializers import (
    AccountingMappingSerializer,
    DocumentExtractionSerializer,
    DocumentMatchSerializer,
    DocumentSerializer,
    ReviewQueueSerializer,
)


class DocumentUploadView(APIView):
    """Upload a document (multipart/form-data)."""

    parser_classes = [MultiPartParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract metadata
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Response(
                {"error": "X-Tenant-ID header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tenant_uuid = uuid.UUID(tenant_id)
        except ValueError:
            return Response(
                {"error": "Invalid X-Tenant-ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Read file bytes
        file_bytes = file_obj.read()

        # Upload via service
        from ..services.upload import UploadService

        storage_client = get_storage_client()
        service = UploadService(storage_client=storage_client)

        document = service.upload_document(
            tenant_id=tenant_uuid,
            legal_entity_id=None,
            file_bytes=file_bytes,
            filename=file_obj.name,
            mime_type=file_obj.content_type or "application/octet-stream",
            source=DocumentSource.WEB_UPLOAD,
            uploaded_by=request.user.pk if request.user.is_authenticated else None,
        )

        serializer = DocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DocumentListView(generics.ListAPIView):
    """List documents (tenant-scoped)."""

    serializer_class = DocumentSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Document.objects.none()
        return Document.objects.filter(tenant_id=tenant_id)


class DocumentDetailView(generics.RetrieveAPIView):
    """Retrieve document details."""

    serializer_class = DocumentSerializer
    lookup_field = "pk"

    def get_queryset(self):
        tenant_id = self.request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Document.objects.none()
        return Document.objects.filter(tenant_id=tenant_id)


class DocumentExtractionListView(generics.ListAPIView):
    """List extraction attempts for a document."""

    serializer_class = DocumentExtractionSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get("X-Tenant-ID")
        document_id = self.kwargs["document_id"]
        if not tenant_id:
            return DocumentExtraction.objects.none()
        return DocumentExtraction.objects.filter(
            document__tenant_id=tenant_id,
            document_id=document_id,
        )


class DocumentDownloadView(APIView):
    """Download original document file."""

    def get(self, request, pk):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Response(
                {"error": "X-Tenant-ID header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            document = Document.objects.get(pk=pk, tenant_id=tenant_id)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate presigned URL
        storage_client = get_storage_client()
        from django.conf import settings

        url = storage_client.get_presigned_url(
            bucket=settings.DOCUMENT_INTELLIGENCE["S3_BUCKET"],
            key=document.original_file_key,
            expires_seconds=3600,
        )

        return Response({"download_url": url})


class ExtractionTriggerView(APIView):
    """Trigger OCR/extraction on a document."""

    def post(self, request, document_id):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Response(
                {"error": "X-Tenant-ID header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            document = Document.objects.get(pk=document_id, tenant_id=tenant_id)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Queue OCR task
        from ..tasks.ocr import run_ocr_task

        run_ocr_task.delay(str(document.guid))

        return Response(
            {"status": "queued", "document_id": str(document.guid)},
            status=status.HTTP_202_ACCEPTED,
        )


class ExtractionDetailView(generics.RetrieveAPIView):
    """Retrieve extraction details."""

    serializer_class = DocumentExtractionSerializer
    lookup_field = "pk"

    def get_queryset(self):
        tenant_id = self.request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return DocumentExtraction.objects.none()
        return DocumentExtraction.objects.filter(document__tenant_id=tenant_id)


class MatchTriggerView(APIView):
    """Trigger matching on a document."""

    def post(self, request, document_id):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Response(
                {"error": "X-Tenant-ID header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            document = Document.objects.get(pk=document_id, tenant_id=tenant_id)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get latest extraction
        extraction = document.extractions.order_by("-version").first()
        if not extraction:
            return Response(
                {"error": "No extraction found. Run extraction first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Queue matching task
        from ..tasks.matching import run_matching_task

        run_matching_task.delay(str(document.guid), str(extraction.guid))

        return Response(
            {"status": "queued", "document_id": str(document.guid)},
            status=status.HTTP_202_ACCEPTED,
        )


class MatchListView(generics.ListAPIView):
    """List matches for a document."""

    serializer_class = DocumentMatchSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get("X-Tenant-ID")
        document_id = self.kwargs["document_id"]
        if not tenant_id:
            return DocumentMatch.objects.none()
        return DocumentMatch.objects.filter(
            document__tenant_id=tenant_id,
            document_id=document_id,
        )


class MatchAcceptView(APIView):
    """Accept a match."""

    def post(self, request, document_id, pk):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Response(
                {"error": "X-Tenant-ID header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            match = DocumentMatch.objects.get(
                pk=pk,
                document_id=document_id,
                document__tenant_id=tenant_id,
            )
        except DocumentMatch.DoesNotExist:
            return Response(
                {"error": "Match not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_id = request.user.pk if request.user.is_authenticated else None
        match.accept(user_id)

        return Response({"status": "accepted"})


class MatchRejectView(APIView):
    """Reject a match."""

    def post(self, request, document_id, pk):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Response(
                {"error": "X-Tenant-ID header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            match = DocumentMatch.objects.get(
                pk=pk,
                document_id=document_id,
                document__tenant_id=tenant_id,
            )
        except DocumentMatch.DoesNotExist:
            return Response(
                {"error": "Match not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_id = request.user.pk if request.user.is_authenticated else None
        match.reject(user_id)

        return Response({"status": "rejected"})


class ReviewQueueListView(generics.ListAPIView):
    """List review queue items."""

    serializer_class = ReviewQueueSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return ReviewQueue.objects.none()
        return ReviewQueue.objects.filter(tenant_id=tenant_id, status="open")


class ReviewApproveView(APIView):
    """Approve a review item."""

    def post(self, request, pk):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Response(
                {"error": "X-Tenant-ID header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            review_item = ReviewQueue.objects.get(pk=pk, tenant_id=tenant_id)
        except ReviewQueue.DoesNotExist:
            return Response(
                {"error": "Review item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        from django.utils import timezone

        user_id = request.user.pk if request.user.is_authenticated else None
        review_item.status = "approved"
        review_item.decided_by = user_id
        review_item.decided_at = timezone.now()
        review_item.save()

        return Response({"status": "approved"})


class ReviewCorrectView(APIView):
    """Submit a correction for a review item."""

    def post(self, request, pk):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return Response(
                {"error": "X-Tenant-ID header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            review_item = ReviewQueue.objects.get(pk=pk, tenant_id=tenant_id)
        except ReviewQueue.DoesNotExist:
            return Response(
                {"error": "Review item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        correction = request.data.get("correction")
        if not correction:
            return Response(
                {"error": "correction field required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = request.user.pk if request.user.is_authenticated else None

        # Apply correction (creates new extraction version)
        from ..services.extraction import ExtractionService
        from ..providers.ocr import get_ocr_provider
        from ..providers.extraction import get_extraction_engine
        from ..providers.ai import get_ai_suggester

        service = ExtractionService(
            ocr_provider=get_ocr_provider(),
            extraction_engine=get_extraction_engine(),
            ai_suggester=get_ai_suggester(),
        )

        new_extraction = service.apply_human_correction(
            extraction=review_item.extraction,
            correction=correction,
            reviewer_id=user_id,
            note=request.data.get("note", ""),
        )

        return Response(
            {
                "status": "corrected",
                "new_extraction_id": str(new_extraction.guid),
                "version": new_extraction.version,
            }
        )


class AccountingMappingListView(generics.ListCreateAPIView):
    """List / create accounting mappings."""

    serializer_class = AccountingMappingSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return AccountingMapping.objects.none()
        return AccountingMapping.objects.filter(tenant_id=tenant_id, is_active=True)

    def perform_create(self, serializer):
        tenant_id = self.request.headers.get("X-Tenant-ID")
        user_id = self.request.user.pk if self.request.user.is_authenticated else None
        serializer.save(tenant_id=tenant_id, created_by=user_id)


class AccountingMappingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve / update / retire an accounting mapping."""

    serializer_class = AccountingMappingSerializer
    lookup_field = "pk"

    def get_queryset(self):
        tenant_id = self.request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return AccountingMapping.objects.none()
        return AccountingMapping.objects.filter(tenant_id=tenant_id)

    def perform_destroy(self, instance):
        # Retire instead of delete
        user_id = self.request.user.pk if self.request.user.is_authenticated else None
        instance.retire(user_id, reason="API delete")
