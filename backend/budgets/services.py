from __future__ import annotations

from decimal import Decimal
from django.db.models import Sum

from accounts.models import Account
from transactions.models import Split


class BudgetService:
    @staticmethod
    def actual_spending(account, start_date, end_date):
        return Split.objects.filter(
            account=account,
            transaction__post_date__range=(start_date, end_date),
            account__account_type='EXPENSE',
        ).aggregate(total=Sum('value'))['total'] or Decimal('0')

    @staticmethod
    def budget_vs_actual(budget):
        results = []
        for category in budget.categories.all():
            actual = BudgetService.actual_spending(
                category.account, budget.start_date, budget.end_date
            )
            results.append({
                'account': category.account.full_name,
                'budgeted': category.amount,
                'actual': actual,
                'variance': category.amount - actual,
            })
        return results
