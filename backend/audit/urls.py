from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from audit.views import AuditLogViewSet

router = DefaultRouter()
router.register('audit-log', AuditLogViewSet, basename='auditlog')

urlpatterns = [
    path('', include(router.urls)),
]
