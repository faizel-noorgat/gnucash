from __future__ import annotations

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import AccountViewSet, CommodityViewSet
from audit.views import AuditLogViewSet
from budgets.views import BudgetCategoryViewSet, BudgetViewSet
from investments.views import InvestmentAccountViewSet, InvestmentLotViewSet, PriceViewSet
from notifications.views import NotificationPreferenceViewSet, NotificationViewSet
from receipts.views import ReceiptViewSet
from recurring.views import RecurringTransactionViewSet
from reports.views import BalanceSheetView, CashFlowView, IncomeStatementView, NetWorthView
from transactions.views import SplitViewSet, TransactionViewSet

# Tenant API routes
tenant_router = DefaultRouter()
tenant_router.register('accounts', AccountViewSet, basename='account')
tenant_router.register('commodities', CommodityViewSet, basename='commodity')
tenant_router.register('transactions', TransactionViewSet, basename='transaction')
tenant_router.register('splits', SplitViewSet, basename='split')
tenant_router.register('budgets', BudgetViewSet, basename='budget')
tenant_router.register('budget-categories', BudgetCategoryViewSet, basename='budgetcategory')
tenant_router.register('receipts', ReceiptViewSet, basename='receipt')
tenant_router.register('recurring', RecurringTransactionViewSet, basename='recurring')
tenant_router.register('investments', InvestmentAccountViewSet, basename='investmentaccount')
tenant_router.register('investment-lots', InvestmentLotViewSet, basename='investmentlot')
tenant_router.register('prices', PriceViewSet, basename='price')
tenant_router.register('audit-log', AuditLogViewSet, basename='auditlog')
tenant_router.register('notifications', NotificationViewSet, basename='notification')
tenant_router.register('notifications/preferences', NotificationPreferenceViewSet, basename='notification-preference')

from admin_api.urls import urlpatterns as admin_api_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('tenants.urls')),
    path('api/v1/', include(tenant_router.urls)),
    path('api/v1/reports/', include([
        path('balance-sheet', BalanceSheetView.as_view(), name='balance-sheet'),
        path('income-statement', IncomeStatementView.as_view(), name='income-statement'),
        path('cash-flow', CashFlowView.as_view(), name='cash-flow'),
        path('net-worth', NetWorthView.as_view(), name='net-worth'),
    ])),
    path('api/v1/', include('billing.urls')),
    path('api/v1/', include('imports.urls')),
    path('api/v1/', include('reconciliation.urls')),
    path('api/v1/admin/', include(admin_api_urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
