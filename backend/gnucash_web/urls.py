from __future__ import annotations

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from billing.views import StripeWebhookView

# Tenant API routes
tenant_router = DefaultRouter()
# Register viewsets here as apps are built:
# tenant_router.register('accounts', AccountViewSet, basename='account')
# tenant_router.register('transactions', TransactionViewSet, basename='transaction')
# tenant_router.register('budgets', BudgetViewSet, basename='budget')
# tenant_router.register('receipts', ReceiptViewSet, basename='receipt')
# tenant_router.register('recurring', RecurringTransactionViewSet, basename='recurring')
# tenant_router.register('notifications', NotificationViewSet, basename='notification')
# tenant_router.register('audit-log', AuditLogViewSet, basename='auditlog')
# tenant_router.register('investments', InvestmentAccountViewSet, basename='investmentaccount')

# Admin API routes
admin_api_router = DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('tenants.urls')),
    path('api/v1/', include(tenant_router.urls)),
    path('api/v1/', include('billing.urls')),
    path('api/v1/admin/', include(admin_api_router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
