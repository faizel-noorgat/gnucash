from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from tenants.models import Tenant


class AuditAction(models.TextChoices):
    CREATE = 'CREATE', 'Create'
    UPDATE = 'UPDATE', 'Update'
    DELETE = 'DELETE', 'Delete'
    LOGIN = 'LOGIN', 'Login'
    LOGOUT = 'LOGOUT', 'Logout'
    EXPORT = 'EXPORT', 'Export'


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='audit_logs',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(
        max_length=10,
        choices=AuditAction.choices,
    )
    model = models.CharField(max_length=255)
    object_id = models.UUIDField()
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'timestamp']),
            models.Index(fields=['tenant', 'action']),
            models.Index(fields=['model', 'object_id']),
        ]

    def __str__(self):
        user_email = self.user.email if self.user else 'system'
        return f'{self.action} {self.model}#{self.object_id} by {user_email}'

    def delete(self, *args, **kwargs):
        raise NotImplementedError('AuditLog entries are immutable and cannot be deleted individually.')
