from __future__ import annotations

import uuid

from django.db import models

from tenants.models import Tenant


class Commodity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    namespace = models.CharField(max_length=255)
    mnemonic = models.CharField(max_length=32)
    fullname = models.CharField(max_length=255, blank=True)
    cusip = models.CharField(max_length=32, blank=True)
    fraction = models.IntegerField(default=100)
    quote_source = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['namespace', 'mnemonic']
        constraints = [
            models.UniqueConstraint(fields=['namespace', 'mnemonic'], name='unique_commodity'),
        ]

    def __str__(self):
        return f'{self.mnemonic} ({self.fullname})'


class AccountType(models.TextChoices):
    ASSET = 'ASSET', 'Asset'
    LIABILITY = 'LIABILITY', 'Liability'
    EQUITY = 'EQUITY', 'Equity'
    INCOME = 'INCOME', 'Income'
    EXPENSE = 'EXPENSE', 'Expense'


class AccountDetailType(models.TextChoices):
    BANK = 'BANK', 'Bank'
    CASH = 'CASH', 'Cash'
    CREDIT = 'CREDIT', 'Credit Card'
    STOCK = 'STOCK', 'Stock'
    MUTUAL = 'MUTUAL', 'Mutual Fund'
    RECEIVABLE = 'RECEIVABLE', 'Accounts Receivable'
    PAYABLE = 'PAYABLE', 'Accounts Payable'
    TRADING = 'TRADING', 'Trading'


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='accounts')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=1024, blank=True)
    code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    account_type = models.CharField(max_length=20, choices=AccountType.choices + AccountDetailType.choices)
    commodity = models.ForeignKey(Commodity, on_delete=models.PROTECT, related_name='accounts')
    commodity_scu = models.IntegerField(default=100)
    hidden = models.BooleanField(default=False)
    placeholder = models.BooleanField(default=False)
    color = models.CharField(max_length=7, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['tenant', 'account_type']),
            models.Index(fields=['tenant', 'parent']),
        ]

    def __str__(self):
        return f'{self.full_name or self.name} ({self.account_type})'
