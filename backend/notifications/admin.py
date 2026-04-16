from __future__ import annotations

from django.contrib import admin

from notifications.models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'title', 'user', 'read', 'created_at')
    list_filter = ('type', 'read', 'tenant')
    search_fields = ('title', 'body')
    readonly_fields = ('id', 'tenant', 'user', 'type', 'title', 'body', 'read', 'created_at')
    ordering = ('-created_at',)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification_type', 'channel_in_app', 'channel_email', 'channel_push')
    list_filter = ('notification_type', 'channel_in_app', 'channel_email', 'channel_push')
    search_fields = ('user__email',)
    readonly_fields = ('id',)
    ordering = ('user', 'notification_type')
