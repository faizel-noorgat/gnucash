from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from billing.views import StripeWebhookView, SubscriptionViewSet

router = DefaultRouter()
router.register('billing/subscription', SubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('billing/webhook/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('', include(router.urls)),
]
