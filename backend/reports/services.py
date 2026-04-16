from __future__ import annotations

from decimal import Decimal
from django.db.models import Sum

from transactions.models import Split


class ReportService:
    FUNDAMENTAL_TYPES = {
        'ASSET': ['ASSET', 'BANK', 'CASH', 'STOCK', 'MUTUAL', 'RECEIVABLE'],
        'LIABILITY': ['LIABILITY', 'CREDIT', 'PAYABLE'],
        'EQUITY': ['EQUITY'],
        'INCOME': ['INCOME'],
        'EXPENSE': ['EXPENSE'],
    }

    @staticmethod
    def balance_sheet(tenant, as_of_date):
        splits = Split.objects.filter(
            tenant=tenant, transaction__post_date__lte=as_of_date
        ).select_related('account')

        def by_types(types):
            return splits.filter(account__account_type__in=types).aggregate(
                total=Sum('value')
            )['total'] or Decimal('0')

        assets = by_types(ReportService.FUNDAMENTAL_TYPES['ASSET'])
        liabilities = by_types(ReportService.FUNDAMENTAL_TYPES['LIABILITY'])
        equity = by_types(ReportService.FUNDAMENTAL_TYPES['EQUITY'])
        retained_earnings = ReportService._retained_earnings(tenant, as_of_date)

        return {
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
            'retained_earnings': retained_earnings,
            'balanced': assets == liabilities + equity + retained_earnings,
        }

    @staticmethod
    def income_statement(tenant, start_date, end_date):
        splits = Split.objects.filter(
            tenant=tenant, transaction__post_date__range=(start_date, end_date)
        ).select_related('account')

        revenue = splits.filter(account__account_type='INCOME').aggregate(
            total=Sum('value')
        )['total'] or Decimal('0')
        expenses = splits.filter(account__account_type='EXPENSE').aggregate(
            total=Sum('value')
        )['total'] or Decimal('0')

        return {
            'revenue': revenue,
            'expenses': expenses,
            'net_income': revenue - expenses,
        }

    @staticmethod
    def cash_flow(tenant, start_date, end_date):
        splits = Split.objects.filter(
            tenant=tenant,
            transaction__post_date__range=(start_date, end_date),
            account__account_type__in=['BANK', 'CASH'],
        ).select_related('account')

        money_in = splits.filter(value__lt=0).aggregate(total=Sum('value'))['total'] or Decimal('0')
        money_out = splits.filter(value__gt=0).aggregate(total=Sum('value'))['total'] or Decimal('0')

        return {
            'money_in': abs(money_in),
            'money_out': money_out,
            'net_cash_flow': abs(money_in) - money_out,
        }

    @staticmethod
    def net_worth(tenant, as_of_date):
        splits = Split.objects.filter(
            tenant=tenant, transaction__post_date__lte=as_of_date
        ).select_related('account')

        assets = splits.filter(account__account_type__in=['ASSET', 'BANK', 'CASH', 'STOCK', 'MUTUAL', 'RECEIVABLE']).aggregate(
            total=Sum('value')
        )['total'] or Decimal('0')
        liabilities = splits.filter(account__account_type__in=['LIABILITY', 'CREDIT', 'PAYABLE']).aggregate(
            total=Sum('value')
        )['total'] or Decimal('0')

        return {'assets': assets, 'liabilities': liabilities, 'net_worth': assets - liabilities}

    @staticmethod
    def _retained_earnings(tenant, as_of_date):
        splits = Split.objects.filter(
            tenant=tenant, transaction__post_date__lte=as_of_date
        ).select_related('account')

        income = splits.filter(account__account_type='INCOME').aggregate(total=Sum('value'))['total'] or Decimal('0')
        expenses = splits.filter(account__account_type='EXPENSE').aggregate(total=Sum('value'))['total'] or Decimal('0')
        return income - expenses
