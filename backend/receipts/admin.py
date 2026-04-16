from __future__ import annotations

from django.contrib import admin

from receipts.models import Receipt


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'vendor', 'total_amount', 'status', 'receipt_date', 'tenant', 'created_at')
    list_filter = ('status', 'receipt_date')
    search_fields = ('vendor', 'ocr_text')
    readonly_fields = ('id', 'ocr_text', 'created_at', 'updated_at')
    ordering = ('-created_at',)
