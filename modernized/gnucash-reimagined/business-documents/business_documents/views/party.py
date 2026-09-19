"""
Party views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from business_documents.models import Party
from business_documents.serializers import PartySerializer, PartyListSerializer
from business_documents.permissions import TenantScopedPermission


class PartyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Party management.

    Provides CRUD operations for parties (customers, vendors, employees).
    """
    permission_classes = [TenantScopedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'roles']
    search_fields = ['name', 'display_name', 'email']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        """Filter parties by tenant"""
        tenant_id = self.request.tenant_id
        return Party.objects.filter(tenant_id=tenant_id)

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return PartyListSerializer
        return PartySerializer

    def perform_create(self, serializer):
        """Set tenant and created_by on creation"""
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user
        )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a party"""
        party = self.get_object()
        party.is_active = False
        party.save()
        return Response({'status': 'party deactivated'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a party"""
        party = self.get_object()
        party.is_active = True
        party.save()
        return Response({'status': 'party activated'})
