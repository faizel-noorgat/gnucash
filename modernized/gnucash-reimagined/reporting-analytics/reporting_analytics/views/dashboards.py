"""Dashboard API views."""

from __future__ import annotations

from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from ..middleware import get_current_tenant_id
from ..models import Dashboard
from ..serializers.dashboards import DashboardSerializer


class DashboardViewSet(viewsets.ModelViewSet):
    """CRUD for dashboards.

    Each dashboard belongs to a single tenant and has a single owner.
    """

    serializer_class = DashboardSerializer

    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        return Dashboard.objects.filter(tenant_id=tenant_id)

    def perform_create(self, serializer):
        tenant_id = get_current_tenant_id()
        serializer.save(
            tenant_id=tenant_id,
            owner=self.request.user,
        )
