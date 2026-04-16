from __future__ import annotations

from django.contrib import admin

from recurring.models import RecurringTransaction


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'frequency', 'next_run', 'enabled', 'tenant', 'start_date')
    list_filter = ('frequency', 'enabled', 'next_run')
    search_fields = ('name',)
    readonly_fields = ('id', 'last_run', 'created_at', 'updated_at')
    ordering = ('next_run',)
