from __future__ import annotations

from rest_framework import serializers

from budgets.models import Budget, BudgetCategory


class BudgetCategorySerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.full_name', read_only=True)

    class Meta:
        model = BudgetCategory
        fields = ('id', 'budget', 'account', 'account_name', 'amount', 'notes')
        read_only_fields = ('id',)


class BudgetSerializer(serializers.ModelSerializer):
    categories = BudgetCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Budget
        fields = ('id', 'tenant', 'name', 'start_date', 'end_date', 'style', 'rollover', 'created_at', 'updated_at', 'categories')
        read_only_fields = ('id', 'created_at', 'updated_at')
