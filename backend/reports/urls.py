from __future__ import annotations

from django.urls import path

from reports.views import BalanceSheetView, CashFlowView, IncomeStatementView, NetWorthView

urlpatterns = [
    path('reports/balance-sheet', BalanceSheetView.as_view(), name='balance-sheet'),
    path('reports/income-statement', IncomeStatementView.as_view(), name='income-statement'),
    path('reports/cash-flow', CashFlowView.as_view(), name='cash-flow'),
    path('reports/net-worth', NetWorthView.as_view(), name='net-worth'),
]
