from __future__ import annotations

import uuid

from django.db import models

from accounts.models import Account, Commodity
from tenants.models import Tenant


class InvestmentAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='investment_accounts')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='investment_details')
    institution = models.CharField(max_length=255, blank=True)
    account_number = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['account__full_name']

    def __str__(self):
        return f'{self.account.full_name} - {self.institution}'


class InvestmentLot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='investment_lots')
    account = models.ForeignKey(InvestmentAccount, on_delete=models.PROTECT, related_name='lots')
    security_id = models.CharField(max_length=32)
    quantity = models.DecimalField(max_digits=20, decimal_places=10)
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=20, decimal_places=10)
    cost_basis = models.DecimalField(max_digits=20, decimal_places=10)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-purchase_date']

    def __str__(self):
        return f'{self.security_id} x{self.quantity} ({self.purchase_date})'


class Price(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, related_name='prices')
    currency = models.ForeignKey(Commodity, on_delete=models.PROTECT, related_name='quote_prices')
    date = models.DateTimeField()
    source = models.CharField(max_length=50, blank=True)
    price_type = models.CharField(max_length=20, default='last')
    value = models.DecimalField(max_digits=20, decimal_places=10)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['commodity', 'currency', 'date', 'price_type'], name='unique_price'),
        ]

    def __str__(self):
        return f'{self.commodity.mnemonic} = {self.value} {self.currency.mnemonic} ({self.date})'
