from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from receipts.models import Receipt
from receipts.serializers import ReceiptSerializer


class ReceiptViewSet(viewsets.ModelViewSet):
    serializer_class = ReceiptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Receipt.objects.filter(tenant=self.request.tenant).select_related(
            'transaction', 'auto_category', 'user_category'
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        receipt = self.get_object()
        from receipts.tasks import process_ocr
        process_ocr.delay(receipt.id)
        return Response({'status': 'processing started'})
