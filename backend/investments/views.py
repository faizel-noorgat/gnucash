from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from investments.models import InvestmentAccount, InvestmentLot, Price
from investments.serializers import InvestmentAccountSerializer, InvestmentLotSerializer, PriceSerializer


class InvestmentAccountViewSet(viewsets.ModelViewSet):
    serializer_class = InvestmentAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InvestmentAccount.objects.filter(tenant=self.request.tenant).select_related('account')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class InvestmentLotViewSet(viewsets.ModelViewSet):
    serializer_class = InvestmentLotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InvestmentLot.objects.filter(tenant=self.request.tenant).select_related('account')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class PriceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PriceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Price.objects.all()
