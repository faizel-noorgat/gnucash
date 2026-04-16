# backend/admin_api/views.py
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.models import AuditLog
from tenants.models import Tenant

from admin_api.permissions import IsPlatformAdmin
from admin_api.serializers import (
    AdminAuditLogSerializer,
    AdminTenantCreateSerializer,
    AdminTenantSerializer,
    AdminTenantUpdateSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    DashboardStatsSerializer,
)

User = get_user_model()


class AdminTenantViewSet(viewsets.ModelViewSet):
    """
    CRUD for all tenants — visible only to platform admins.
    Bypasses tenant scoping; operates across all tenants.
    """
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return Tenant.objects.all().prefetch_related('memberships')

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminTenantCreateSerializer
        if self.action in ('update', 'partial_update'):
            return AdminTenantUpdateSerializer
        return AdminTenantSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(slug__icontains=search)
            )

        status_filter = request.query_params.get('status')
        if status_filter == 'trial':
            queryset = queryset.filter(trial_ends_at__gte=timezone.now())
        elif status_filter == 'expired':
            queryset = queryset.filter(
                trial_ends_at__lt=timezone.now(),
                stripe_customer_id='',
            )
        elif status_filter == 'active':
            queryset = queryset.filter(
                Q(trial_ends_at__gte=timezone.now()) | ~Q(stripe_customer_id=''),
            )

        queryset = queryset.order_by('-created_at')

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer)

    @action(detail=True, methods=['post'], permission_classes=[IsPlatformAdmin])
    def extend_trial(self, request, pk=None):
        tenant = self.get_object()
        days = request.data.get('days', 14)
        current_end = tenant.trial_ends_at or timezone.now()
        tenant.trial_ends_at = current_end + timedelta(days=days)
        tenant.save(update_fields=['trial_ends_at'])
        return Response(
            {'id': tenant.id, 'trial_ends_at': tenant.trial_ends_at},
            status=status.HTTP_200_OK,
        )


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list of all users across all tenants.
    Platform admins can view users, filter, and search.
    User updates (is_active, is_staff) via dedicated action.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return User.objects.all().prefetch_related('memberships__tenant')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(email__icontains=search)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        queryset = queryset.order_by('-date_joined')

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer)

    @action(detail=True, methods=['patch'], permission_classes=[IsPlatformAdmin])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return Response({'id': user.id, 'is_active': user.is_active})

    @action(detail=True, methods=['patch'], permission_classes=[IsPlatformAdmin])
    def set_staff(self, request, pk=None):
        user = self.get_object()
        user.is_staff = request.data.get('is_staff', False)
        user.save(update_fields=['is_staff'])
        return Response({'id': user.id, 'is_staff': user.is_staff})


class AdminAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Cross-tenant audit log viewer for platform admins.
    Supports filtering by tenant, action, model, and date range.
    """
    serializer_class = AdminAuditLogSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return AuditLog.objects.select_related('tenant', 'user')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        tenant_id = request.query_params.get('tenant_id')
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        action = request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)

        model = request.query_params.get('model')
        if model:
            queryset = queryset.filter(model__icontains=model)

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)

        user_email = request.query_params.get('user_email')
        if user_email:
            queryset = queryset.filter(user__email__icontains=user_email)

        queryset = queryset.order_by('-timestamp')

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer)


class DashboardStatsView(viewsets.ViewSet):
    """
    Platform dashboard statistics — aggregated counts and trends.
    Read-only, superuser-only.
    """
    permission_classes = [IsPlatformAdmin]

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        total_tenants = Tenant.objects.count()
        total_users = User.objects.count()
        total_audit_events = AuditLog.objects.count()
        active_tenants_30d = Tenant.objects.filter(
            memberships__joined_at__gte=thirty_days_ago,
        ).distinct().count()
        recent_signups = User.objects.filter(
            date_joined__gte=seven_days_ago,
        ).count()

        serializer = DashboardStatsSerializer({
            'total_tenants': total_tenants,
            'total_users': total_users,
            'total_audit_events': total_audit_events,
            'active_tenants_30d': active_tenants_30d,
            'recent_signups': recent_signups,
        })

        return Response(serializer.data)


class CurrentUserView(generics.RetrieveAPIView):
    """
    GET /api/v1/admin/users/me/ — Returns the authenticated user's details.
    Used by the admin hub login flow to verify is_staff status.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        from admin_api.serializers import AdminUserSerializer
        return AdminUserSerializer
