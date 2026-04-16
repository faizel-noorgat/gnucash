from __future__ import annotations

import uuid

from django.db import models

from accounts.models import Account
from tenants.models import Tenant


class ReconciliationSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='reconciliation_sessions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='reconciliation_sessions')
    end_date = models.DateField()
    ending_balance = models.DecimalField(max_digits=20, decimal_places=10)
    starting_balance = models.DecimalField(max_digits=20, decimal_places=10)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.account.full_name} reconciliation ({self.end_date})'

    @property
    def difference(self):
        from decimal import Decimal
        from django.db.models import Sum
        from transactions.models import Split

        cleared = Split.objects.filter(
            tenant=self.tenant,
            account=self.account,
            reconcile_state__in=['c', 'y'],
            transaction__post_date__lte=self.end_date,
        ).aggregate(total=Sum('value'))['total'] or Decimal('0')
        return self.ending_balance - (self.starting_balance + cleared)
