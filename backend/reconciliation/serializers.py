from __future__ import annotations

from rest_framework import serializers

from reconciliation.models import ReconciliationSession


class ReconciliationSessionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.full_name', read_only=True)
    difference = serializers.DecimalField(max_digits=20, decimal_places=10, read_only=True)

    class Meta:
        model = ReconciliationSession
        fields = (
            'id', 'tenant', 'account', 'account_name', 'end_date',
            'ending_balance', 'starting_balance', 'completed', 'completed_at',
            'difference', 'created_at',
        )
        read_only_fields = ('id', 'difference', 'completed', 'completed_at', 'created_at')
