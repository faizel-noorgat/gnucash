from __future__ import annotations

from rest_framework import serializers

from notifications.models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            'id', 'tenant', 'user', 'type', 'title', 'body',
            'read', 'created_at',
        )
        read_only_fields = ('id', 'tenant', 'user', 'created_at')


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            'id', 'user', 'notification_type', 'channel_in_app',
            'channel_email', 'channel_push',
        )
        read_only_fields = ('id', 'user')
