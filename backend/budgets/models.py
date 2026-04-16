from __future__ import annotations

import uuid

from django.db import models

from accounts.models import Account
from tenants.models import Tenant


class Budget(models.Model):
    class Style(models.TextChoices):
        TRADITIONAL = 'TRADITIONAL', 'Traditional'
        ENVELOPE = 'ENVELOPE', 'Envelope'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='budgets')
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    style = models.CharField(max_length=20, choices=Style.choices, default=Style.TRADITIONAL)
    rollover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.name} ({self.start_date} - {self.end_date})'


class BudgetCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='categories')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='budget_categories')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['budget', 'account__full_name']
        constraints = [
            models.UniqueConstraint(fields=['budget', 'account'], name='unique_budget_category'),
        ]

    def __str__(self):
        return f'{self.account.full_name}: {self.amount}'
