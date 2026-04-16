from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from recurring.models import RecurringTransaction
from recurring.serializers import RecurringTransactionSerializer


class RecurringTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RecurringTransaction.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)
