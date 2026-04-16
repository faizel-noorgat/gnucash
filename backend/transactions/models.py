from __future__ import annotations

import uuid

from django.db import models

from accounts.models import Account
from tenants.models import Tenant, User


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='transactions')
    guid = models.UUIDField(default=uuid.uuid4, editable=False)
    currency = models.ForeignKey('accounts.Commodity', on_delete=models.PROTECT, related_name='transactions')
    num = models.CharField(max_length=255, blank=True)
    post_date = models.DateField()
    enter_date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=2048)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-post_date']
        indexes = [
            models.Index(fields=['tenant', 'post_date']),
        ]

    def __str__(self):
        return f'{self.description} ({self.post_date})'


class Split(models.Model):
    class ReconcileState(models.TextChoices):
        NONE = 'n', 'Not Reconciled'
        CLEARED = 'c', 'Cleared'
        RECONCILED = 'y', 'Reconciled'
        FROZEN = 'f', 'Frozen'
        VOID = 'v', 'Void'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='splits')
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='splits')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='splits')
    memo = models.CharField(max_length=2048, blank=True)
    action = models.CharField(max_length=255, blank=True)
    reconcile_state = models.CharField(max_length=1, choices=ReconcileState.choices, default=ReconcileState.NONE)
    reconcile_date = models.DateTimeField(null=True, blank=True)
    value = models.DecimalField(max_digits=20, decimal_places=10, default=0)
    quantity = models.DecimalField(max_digits=20, decimal_places=10, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['transaction', 'account']
        indexes = [
            models.Index(fields=['tenant', 'account']),
            models.Index(fields=['tenant', 'reconcile_state']),
        ]

    def __str__(self):
        return f'{self.account} split: {self.value}'
