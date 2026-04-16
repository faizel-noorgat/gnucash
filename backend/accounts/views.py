from __future__ import annotations

from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Account, Commodity
from accounts.serializers import (
    AccountRegisterResponseSerializer,
    AccountSerializer,
    CommoditySerializer,
)
from accounts.services import get_account_register


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

    @action(detail=True, methods=['get'], url_path='register')
    def register(self, request, pk=None):
        """Return all transactions touching this account with running balance."""
        account = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        data = get_account_register(account, start_date=start_date, end_date=end_date)
        serializer = AccountRegisterResponseSerializer(data)
        return Response(serializer.data)


class CommodityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommoditySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Commodity.objects.all()
