from __future__ import annotations

import uuid

from django.db import models

from accounts.models import Account
from tenants.models import Tenant
from transactions.models import Transaction


class Receipt(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSED = 'PROCESSED', 'Processed'
        MANUAL_REVIEW = 'MANUAL_REVIEW', 'Manual Review'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='receipts')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, related_name='receipt')
    file_url = models.URLField(max_length=500)
    ocr_text = models.TextField(blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    receipt_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    auto_category = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='auto_categorized_receipts')
    user_category = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name='user_categorized_receipts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Receipt {self.vendor or "unknown"} - {self.total_amount}'
