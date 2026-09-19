"""
Tenant Views

API views for tenant management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..domain.models import Tenant, LegalEntity
from ..domain.services.tenant_service import TenantService
from ..domain.services.authorization_service import AuthorizationService
from .serializers import TenantSerializer, LegalEntitySerializer


class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Tenant management.

    GET /api/v1/tenants/ - List accessible tenants
    GET /api/v1/tenants/{slug}/ - Get tenant details
    POST /api/v1/tenants/ - Create new tenant
    PUT /api/v1/tenants/{slug}/ - Update tenant
    DELETE /api/v1/tenants/{slug}/ - Deactivate tenant
    """
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        """Get tenants user can access."""
        return AuthorizationService.get_accessible_tenants(self.request.user)

    def perform_create(self, serializer):
        """Create new tenant."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def entities(self, request, slug=None):
        """Get legal entities for tenant."""
        tenant = self.get_object()

        if not AuthorizationService.is_tenant_member(request.user, tenant):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        entities = TenantService.get_tenant_entities(tenant)
        serializer = LegalEntitySerializer(entities, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def entities_create(self, request, slug=None):
        """Create legal entity in tenant."""
        tenant = self.get_object()

        if not AuthorizationService.has_permission(
            request.user,
            tenant,
            'create_legal_entity'
        ):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = LegalEntitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entity = TenantService.create_legal_entity(
            tenant=tenant,
            name=serializer.validated_data['name'],
            created_by=request.user,
            **{k: v for k, v in serializer.validated_data.items() if k != 'name'}
        )

        return Response(
            LegalEntitySerializer(entity).data,
            status=status.HTTP_201_CREATED
        )
