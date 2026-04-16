from __future__ import annotations

from rest_framework import serializers

from receipts.models import Receipt


class ReceiptSerializer(serializers.ModelSerializer):
    auto_category_name = serializers.CharField(source='auto_category.full_name', read_only=True, allow_null=True)
    user_category_name = serializers.CharField(source='user_category.full_name', read_only=True, allow_null=True)

    class Meta:
        model = Receipt
        fields = (
            'id', 'tenant', 'transaction', 'file_url', 'ocr_text', 'vendor',
            'total_amount', 'receipt_date', 'status', 'auto_category', 'auto_category_name',
            'user_category', 'user_category_name', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'ocr_text', 'created_at', 'updated_at')
