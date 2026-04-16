from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import AccountViewSet, CommodityViewSet

router = DefaultRouter()
router.register('accounts', AccountViewSet, basename='account')
router.register('commodities', CommodityViewSet, basename='commodity')

urlpatterns = [
    path('', include(router.urls)),
]
