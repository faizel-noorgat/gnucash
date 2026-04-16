from __future__ import annotations

import uuid

from django.db import models

from tenants.models import Tenant


class RecurringTransaction(models.Model):
    class Frequency(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'
        QUARTERLY = 'QUARTERLY', 'Quarterly'
        YEARLY = 'YEARLY', 'Yearly'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='recurring_transactions')
    name = models.CharField(max_length=255)
    template = models.JSONField()
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateField()
    enabled = models.BooleanField(default=True)
    advance_notice_days = models.IntegerField(default=0)
    auto_create = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_run']

    def __str__(self):
        return f'{self.name} ({self.frequency} - next: {self.next_run})'
