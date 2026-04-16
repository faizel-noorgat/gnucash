from __future__ import annotations

from django.contrib import admin

from budgets.models import Budget, BudgetCategory


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'start_date', 'end_date', 'style', 'tenant', 'created_at')
    list_filter = ('style', 'rollover')
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'budget', 'account', 'amount')
    list_filter = ('budget',)
    search_fields = ('account__name', 'notes')
    readonly_fields = ('id',)
