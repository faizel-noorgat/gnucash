from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from receipts.views import ReceiptViewSet

router = DefaultRouter()
router.register('receipts', ReceiptViewSet, basename='receipt')

urlpatterns = [
    path('', include(router.urls)),
]
