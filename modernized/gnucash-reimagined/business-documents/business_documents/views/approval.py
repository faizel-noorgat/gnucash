"""
Approval workflow views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from business_documents.models import ApprovalWorkflow
from business_documents.serializers import ApprovalWorkflowSerializer
from business_documents.permissions import TenantScopedPermission


class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ApprovalWorkflow management.

    Provides CRUD operations for approval workflows.
    """
    serializer_class = ApprovalWorkflowSerializer
    permission_classes = [TenantScopedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']

    def get_queryset(self):
        """Filter workflows by tenant"""
        tenant_id = self.request.tenant_id
        return ApprovalWorkflow.objects.filter(tenant_id=tenant_id).prefetch_related('steps')

    def perform_create(self, serializer):
        """Set tenant and created_by on creation"""
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user
        )
