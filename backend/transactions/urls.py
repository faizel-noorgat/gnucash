from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from transactions.views import SplitViewSet, TransactionViewSet

router = DefaultRouter()
router.register('transactions', TransactionViewSet, basename='transaction')
router.register('splits', SplitViewSet, basename='split')

urlpatterns = [
    path('', include(router.urls)),
]
