from __future__ import annotations

from django.contrib import admin

from investments.models import InvestmentAccount, InvestmentLot, Price


@admin.register(InvestmentAccount)
class InvestmentAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'institution', 'tenant')
    search_fields = ('institution', 'account__name')


@admin.register(InvestmentLot)
class InvestmentLotAdmin(admin.ModelAdmin):
    list_display = ('id', 'security_id', 'quantity', 'purchase_price', 'is_closed', 'purchase_date')
    list_filter = ('is_closed', 'purchase_date')


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('id', 'commodity', 'currency', 'value', 'price_type', 'date')
    list_filter = ('price_type', 'date')
