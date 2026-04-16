from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from transactions.models import Split, Transaction
from transactions.serializers import SplitSerializer, TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(
            tenant=self.request.tenant
        ).select_related('currency', 'created_by').prefetch_related('splits', 'splits__account')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, created_by=self.request.user)


class SplitViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SplitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Split.objects.filter(tenant=self.request.tenant).select_related('account', 'transaction')
