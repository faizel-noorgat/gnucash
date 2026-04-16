from __future__ import annotations

import uuid

from django.db import models

from tenants.models import Tenant


class ImportTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='import_templates')
    name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255, blank=True)
    column_mapping = models.JSONField()
    delimiter = models.CharField(max_length=10, default=',')
    encoding = models.CharField(max_length=50, default='utf-8')
    has_header = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.bank_name or "custom"})'
