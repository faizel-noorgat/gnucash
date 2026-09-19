"""API views for Document Intelligence.

TODO: Implement views. Current structure is a stub for migration.

Views will handle:
- Document upload with provenance capture (BR-DI-001, BR-DI-002, BR-DI-008)
- Extraction triggering and status tracking (BR-DI-003)
- Match candidate management (accept/reject)
- Review queue workflow (BR-DI-006)
- Accounting mapping CRUD with retirement (BR-DI-007)

All views are tenant-scoped via X-Tenant-ID header.
"""

from __future__ import annotations

from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView


# Stub views — to be implemented


class DocumentUploadView(APIView):
    """Upload a document (multipart/form-data)."""

    parser_classes = [MultiPartParser]

    def post(self, request):
        return Response(
            {"status": "not_implemented", "message": "Document upload view stub"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class DocumentListView(generics.ListAPIView):
    """List documents (tenant-scoped)."""

    pass


class DocumentDetailView(generics.RetrieveAPIView):
    """Retrieve document details."""

    pass


class DocumentExtractionListView(generics.ListAPIView):
    """List extraction attempts for a document."""

    pass


class DocumentDownloadView(APIView):
    """Download original document file."""

    def get(self, request, pk):
        return Response(
            {"status": "not_implemented", "message": "Document download view stub"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class ExtractionTriggerView(APIView):
    """Trigger OCR/extraction on a document."""

    def post(self, request, document_id):
        return Response(
            {"status": "not_implemented", "message": "Extraction trigger view stub"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class ExtractionDetailView(generics.RetrieveAPIView):
    """Retrieve extraction details."""

    pass


class MatchTriggerView(APIView):
    """Trigger matching on a document."""

    def post(self, request, document_id):
        return Response(
            {"status": "not_implemented", "message": "Match trigger view stub"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class MatchListView(generics.ListAPIView):
    """List matches for a document."""

    pass


class MatchAcceptView(APIView):
    """Accept a match."""

    def post(self, request, document_id, pk):
        return Response(
            {"status": "not_implemented", "message": "Match accept view stub"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class MatchRejectView(APIView):
    """Reject a match."""

    def post(self, request, document_id, pk):
        return Response(
            {"status": "not_implemented", "message": "Match reject view stub"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class ReviewQueueListView(generics.ListAPIView):
    """List review queue items."""

    pass


class ReviewApproveView(APIView):
    """Approve a review item."""

    def post(self, request, pk):
        return Response(
            {"status": "not_implemented", "message": "Review approve view stub"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class ReviewCorrectView(APIView):
    """Submit a correction for a review item."""

    def post(self, request, pk):
        return Response(
            {"status": "not_implemented", "message": "Review correct view stub"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class AccountingMappingListView(generics.ListCreateAPIView):
    """List / create accounting mappings."""

    pass


class AccountingMappingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve / update / retire an accounting mapping."""

    pass
