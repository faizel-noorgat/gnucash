from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from budgets.models import Budget, BudgetCategory
from budgets.serializers import BudgetSerializer, BudgetCategorySerializer


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(tenant=self.request.tenant).prefetch_related('categories')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class BudgetCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BudgetCategory.objects.filter(budget__tenant=self.request.tenant)
