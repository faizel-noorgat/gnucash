from __future__ import annotations

from rest_framework import serializers

from recurring.models import RecurringTransaction


class RecurringTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringTransaction
        fields = (
            'id', 'tenant', 'name', 'template', 'frequency', 'start_date',
            'end_date', 'last_run', 'next_run', 'enabled', 'advance_notice_days',
            'auto_create', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'last_run', 'created_at', 'updated_at')
