from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from recurring.views import RecurringTransactionViewSet

router = DefaultRouter()
router.register('recurring', RecurringTransactionViewSet, basename='recurring')

urlpatterns = [
    path('', include(router.urls)),
]
