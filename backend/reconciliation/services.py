from __future__ import annotations

import time
from decimal import Decimal
from django.db import models
from django.db.models import Sum

from transactions.models import Split


class ReconciliationService:
    @staticmethod
    def calculate_account_balance(account, end_date):
        splits = Split.objects.filter(
            account=account,
            transaction__post_date__lte=end_date,
        )
        total = splits.aggregate(total=Sum('value'))['total'] or Decimal('0')
        return total

    @staticmethod
    def get_unreconciled_splits(account, end_date):
        return Split.objects.filter(
            account=account,
            transaction__post_date__lte=end_date,
            reconcile_state='n',
        ).select_related('transaction').order_by('transaction__post_date')

    @staticmethod
    def auto_suggest_splits(splits, target_balance, max_seconds=30, tolerance=Decimal('0.01')):
        start_time = time.time()
        values = [(s.id, s.value) for s in splits]
        solution = []
        ReconciliationService._subset_sum(values, 0, target_balance, [], solution, max_seconds, tolerance, start_time)
        return [s_id for s_id, _ in solution]

    @staticmethod
    def _subset_sum(values, index, target, path, solution, max_seconds, tolerance, start_time):
        if time.time() - start_time > max_seconds:
            return
        if solution:
            return
        current_sum = sum(v for _, v in path)
        if abs(current_sum - target) <= tolerance:
            solution.extend(path)
            return
        if index >= len(values):
            return
        remaining_sum = sum(v for _, v in values[index:])
        if current_sum + remaining_sum < target - tolerance:
            return
        s_id, value = values[index]
        path.append((s_id, value))
        ReconciliationService._subset_sum(values, index + 1, target, path, solution, max_seconds, tolerance, start_time)
        path.pop()
        if solution:
            return
        ReconciliationService._subset_sum(values, index + 1, target, path, solution, max_seconds, tolerance, start_time)

    @staticmethod
    def complete_reconciliation(session):
        from django.db import transaction
        from django.utils import timezone
        with transaction.atomic():
            Split.objects.filter(
                tenant=session.tenant,
                account=session.account,
                reconcile_state='n',
                transaction__post_date__lte=session.end_date,
            ).update(reconcile_state='c')
            session.completed = True
            session.completed_at = timezone.now()
            session.save()
