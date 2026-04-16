from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import register

from reconciliation.models import ReconciliationSession


@register(ReconciliationSession)
class ReconciliationSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'end_date', 'completed', 'created_at')
    list_filter = ('completed',)
    search_fields = ('account__full_name',)
    readonly_fields = ('id', 'created_at')
