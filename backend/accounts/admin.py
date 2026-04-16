from __future__ import annotations

from django.contrib import admin

from accounts.models import Account, Commodity


@admin.register(Commodity)
class CommodityAdmin(admin.ModelAdmin):
    list_display = ('id', 'mnemonic', 'fullname', 'namespace', 'fraction')
    list_filter = ('namespace',)
    search_fields = ('mnemonic', 'fullname')
    readonly_fields = ('id',)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'full_name', 'account_type', 'tenant', 'created_at')
    list_filter = ('account_type', 'hidden', 'placeholder')
    search_fields = ('name', 'full_name', 'code')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('full_name',)
