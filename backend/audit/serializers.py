from __future__ import annotations

from rest_framework import serializers

from audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            'id', 'tenant', 'user', 'user_email', 'action', 'model',
            'object_id', 'old_values', 'new_values', 'ip_address',
            'user_agent', 'timestamp',
        )
        read_only_fields = (
            'id', 'tenant', 'user', 'user_email', 'action', 'model',
            'object_id', 'old_values', 'new_values', 'ip_address',
            'user_agent', 'timestamp',
        )

    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        return None
