from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from investments.views import InvestmentAccountViewSet, InvestmentLotViewSet, PriceViewSet

router = DefaultRouter()
router.register('investment-accounts', InvestmentAccountViewSet, basename='investmentaccount')
router.register('investment-lots', InvestmentLotViewSet, basename='investmentlot')
router.register('prices', PriceViewSet, basename='price')

urlpatterns = [
    path('', include(router.urls)),
]
