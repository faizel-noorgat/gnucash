from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from tenants.models import Tenant


class NotificationType(models.TextChoices):
    SYSTEM = 'SYSTEM', 'System'
    TRANSACTION = 'TRANSACTION', 'Transaction'
    BUDGET = 'BUDGET', 'Budget'
    RECEIPT = 'RECEIPT', 'Receipt'
    RECURRING = 'RECURRING', 'Recurring'
    BILLING = 'BILLING', 'Billing'
    SECURITY = 'SECURITY', 'Security'


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'user', 'read']),
            models.Index(fields=['tenant', 'created_at']),
        ]

    def __str__(self):
        return f'[{self.type}] {self.title}'


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
    )
    channel_in_app = models.BooleanField(default=True)
    channel_email = models.BooleanField(default=False)
    channel_push = models.BooleanField(default=False)

    class Meta:
        ordering = ['notification_type']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'notification_type'],
                name='unique_user_notification_type_preference',
            ),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.notification_type}'
