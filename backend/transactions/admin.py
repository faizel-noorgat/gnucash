from __future__ import annotations

from django.contrib import admin

from transactions.models import Split, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'description', 'post_date', 'tenant', 'created_by', 'created_at')
    list_filter = ('post_date', 'created_at')
    search_fields = ('description', 'notes', 'num')
    readonly_fields = ('id', 'guid', 'enter_date', 'created_at', 'updated_at')
    ordering = ('-post_date',)


@admin.register(Split)
class SplitAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'value', 'transaction', 'reconcile_state', 'created_at')
    list_filter = ('reconcile_state', 'created_at')
    search_fields = ('memo', 'action')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)
