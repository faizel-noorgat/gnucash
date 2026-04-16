from __future__ import annotations

from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.models import Account, Commodity
from accounts.serializers import AccountSerializer, CommoditySerializer


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'full_name', 'code']
    ordering_fields = ['name', 'full_name', 'created_at']
    ordering = ['full_name']

    def get_queryset(self):
        return Account.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class CommodityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommoditySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Commodity.objects.all()
