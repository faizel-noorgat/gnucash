from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from reconciliation.views import ReconciliationViewSet

router = DefaultRouter()
router.register('reconciliation', ReconciliationViewSet, basename='reconciliation')

urlpatterns = [path('', include(router.urls))]
