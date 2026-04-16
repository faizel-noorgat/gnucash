# backend/admin_api/urls.py
from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from admin_api.views import (
    AdminAuditLogViewSet,
    AdminTenantViewSet,
    AdminUserViewSet,
    CurrentUserView,
    DashboardStatsView,
)

router = DefaultRouter()
router.register('tenants', AdminTenantViewSet, basename='admin-tenant')
router.register('users', AdminUserViewSet, basename='admin-user')
router.register('audit-log', AdminAuditLogViewSet, basename='admin-audit-log')

urlpatterns = [
    path('users/me/', CurrentUserView.as_view(), name='admin-current-user'),
    path('dashboard/', DashboardStatsView.as_view({'get': 'stats'}), name='admin-dashboard-stats'),
] + router.urls
