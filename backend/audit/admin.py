from __future__ import annotations

from django.contrib import admin

from audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'model', 'user', 'timestamp')
    list_filter = ('action', 'model', 'tenant')
    search_fields = ('model', 'ip_address')
    readonly_fields = (
        'id', 'tenant', 'user', 'action', 'model', 'object_id',
        'old_values', 'new_values', 'ip_address', 'user_agent', 'timestamp',
    )
    ordering = ('-timestamp',)
