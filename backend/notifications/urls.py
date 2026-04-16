from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from notifications.views import NotificationPreferenceViewSet, NotificationViewSet

router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notification')
router.register('notifications/preferences', NotificationPreferenceViewSet, basename='notificationpreference')

urlpatterns = [
    path('', include(router.urls)),
]
