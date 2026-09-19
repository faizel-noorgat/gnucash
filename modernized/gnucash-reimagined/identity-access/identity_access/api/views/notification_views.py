"""
Notification Views

API views for notification management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..domain.models import Notification, NotificationPreference
from ..domain.services.notification_service import NotificationService
from .serializers import NotificationSerializer, NotificationPreferenceSerializer


class NotificationViewSet(viewsets.ViewSet):
    """
    ViewSet for Notification management.

    GET /api/v1/notifications/ - List user's notifications
    POST /api/v1/notifications/{guid}/read/ - Mark as read
    POST /api/v1/notifications/read-all/ - Mark all as read
    GET /api/v1/notifications/unread-count/ - Get unread count
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List user's notifications."""
        notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[:50]

        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mark notification as read."""
        notification = Notification.objects.get(guid=pk, recipient=request.user)
        NotificationService.mark_as_read(notification)

        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        """Mark all notifications as read."""
        tenant_id = request.data.get('tenant_id')
        tenant = None

        if tenant_id:
            from ..domain.models import Tenant
            from django.shortcuts import get_object_or_404
            tenant = get_object_or_404(Tenant, guid=tenant_id)

        NotificationService.mark_all_as_read(request.user, tenant)

        return Response({'status': 'success'})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """Get unread notification count."""
        tenant_id = request.query_params.get('tenant_id')
        tenant = None

        if tenant_id:
            from ..domain.models import Tenant
            from django.shortcuts import get_object_or_404
            tenant = get_object_or_404(Tenant, guid=tenant_id)

        count = NotificationService.get_unread_count(request.user, tenant)

        return Response({'count': count})


class NotificationPreferenceViewSet(viewsets.ViewSet):
    """
    ViewSet for Notification Preference management.

    GET /api/v1/notification-preferences/ - Get preferences
    PUT /api/v1/notification-preferences/ - Update preferences
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get notification preferences."""
        tenant_id = request.query_params.get('tenant_id')
        tenant = None

        if tenant_id:
            from ..domain.models import Tenant
            from django.shortcuts import get_object_or_404
            tenant = get_object_or_404(Tenant, guid=tenant_id)

        prefs = NotificationService.get_preferences(request.user, tenant)

        if prefs:
            serializer = NotificationPreferenceSerializer(prefs)
            return Response(serializer.data)

        return Response({})

    def update(self, request):
        """Update notification preferences."""
        tenant_id = request.data.get('tenant_id')
        tenant = None

        if tenant_id:
            from ..domain.models import Tenant
            from django.shortcuts import get_object_or_404
            tenant = get_object_or_404(Tenant, guid=tenant_id)

        preferences = request.data.get('preferences', {})

        prefs = NotificationService.update_preferences(
            user=request.user,
            tenant=tenant,
            preferences=preferences
        )

        return Response(NotificationPreferenceSerializer(prefs).data)
