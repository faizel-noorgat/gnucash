"""
Practice Views

API views for practice/advisor access management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from ..domain.models import Practice, ClientEngagement, AdvisorAccessGrant
from ..domain.services.practice_service import PracticeService
from ..domain.services.authorization_service import AuthorizationService
from .serializers import (
    PracticeSerializer, PracticeMembershipSerializer,
    ClientEngagementSerializer, AdvisorAccessGrantSerializer
)


class PracticeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Practice management.

    GET /api/v1/practices/ - List user's practices
    POST /api/v1/practices/ - Create new practice
    GET /api/v1/practices/{slug}/ - Get practice details
    """
    serializer_class = PracticeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        """Get practices user is member of."""
        practice_memberships = self.request.user.practice_memberships.filter(status='active')
        practice_ids = practice_memberships.values_list('practice_id', flat=True)
        return Practice.objects.filter(guid__in=practice_ids, is_active=True)

    def perform_create(self, serializer):
        """Create new practice."""
        PracticeService.create_practice(
            name=serializer.validated_data['name'],
            slug=serializer.validated_data['slug'],
            created_by=self.request.user,
            **{k: v for k, v in serializer.validated_data.items()
               if k not in ['name', 'slug']}
        )

    @action(detail=True, methods=['get'])
    def engagements(self, request, slug=None):
        """Get client engagements for practice."""
        practice = self.get_object()

        if not AuthorizationService.is_practice_member(request.user, practice):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        engagements = PracticeService.get_practice_engagements(practice)
        serializer = ClientEngagementSerializer(engagements, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='engagements/create')
    def create_engagement(self, request, slug=None):
        """Create client engagement."""
        practice = self.get_object()

        if not AuthorizationService.has_permission(
            request.user,
            practice,
            'create_engagement'
        ):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        from ..domain.models import Tenant
        tenant = get_object_or_404(Tenant, guid=request.data.get('tenant_id'))

        engagement = PracticeService.create_client_engagement(
            practice=practice,
            tenant=tenant,
            engagement_type=request.data.get('engagement_type', 'bookkeeping'),
            created_by=request.user,
            **{k: v for k, v in request.data.items()
               if k not in ['tenant_id', 'engagement_type']}
        )

        return Response(
            ClientEngagementSerializer(engagement).data,
            status=status.HTTP_201_CREATED
        )


class ClientEngagementViewSet(viewsets.ViewSet):
    """
    ViewSet for Client Engagement management.

    POST /api/v1/engagements/{guid}/activate/ - Activate engagement
    POST /api/v1/engagements/{guid}/terminate/ - Terminate engagement
    GET /api/v1/engagements/{guid}/access-grants/ - List access grants
    POST /api/v1/engagements/{guid}/access-grants/grant/ - Grant access
    POST /api/v1/engagements/{guid}/access-grants/{grant_guid}/revoke/ - Revoke access
    """
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate client engagement."""
        engagement = get_object_or_404(ClientEngagement, guid=pk)

        if not AuthorizationService.is_practice_member(request.user, engagement.practice):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        PracticeService.activate_engagement(engagement)

        return Response(ClientEngagementSerializer(engagement).data)

    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        """Terminate client engagement."""
        engagement = get_object_or_404(ClientEngagement, guid=pk)

        if not AuthorizationService.is_practice_member(request.user, engagement.practice):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        PracticeService.terminate_engagement(engagement)

        return Response(ClientEngagementSerializer(engagement).data)

    @action(detail=True, methods=['get'], url_path='access-grants')
    def list_access_grants(self, request, pk=None):
        """List access grants for engagement."""
        engagement = get_object_or_404(ClientEngagement, guid=pk)

        if not AuthorizationService.is_practice_member(request.user, engagement.practice):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        grants = engagement.access_grants.all()
        serializer = AdvisorAccessGrantSerializer(grants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='access-grants/grant')
    def grant_access(self, request, pk=None):
        """Grant advisor access."""
        engagement = get_object_or_404(ClientEngagement, guid=pk)

        if not AuthorizationService.has_permission(
            request.user,
            engagement.practice,
            'grant_access'
        ):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        from ..domain.models import User, Role
        practice_user = get_object_or_404(User, guid=request.data.get('practice_user_id'))
        tenant_role = get_object_or_404(Role, guid=request.data.get('tenant_role_id'))

        try:
            grant = PracticeService.grant_advisor_access(
                engagement=engagement,
                practice_user=practice_user,
                tenant_role=tenant_role,
                granted_by=request.user,
                scoped_entity=request.data.get('scoped_entity'),
                expires_at=request.data.get('expires_at'),
                reason=request.data.get('reason', '')
            )

            return Response(
                AdvisorAccessGrantSerializer(grant).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='access-grants/(?P<grant_guid>[^/.]+)/revoke')
    def revoke_access(self, request, pk=None, grant_guid=None):
        """Revoke advisor access."""
        engagement = get_object_or_404(ClientEngagement, guid=pk)
        grant = get_object_or_404(AdvisorAccessGrant, guid=grant_guid, engagement=engagement)

        if not AuthorizationService.has_permission(
            request.user,
            engagement.practice,
            'revoke_access'
        ):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        PracticeService.revoke_advisor_access(
            grant=grant,
            revoked_by=request.user,
            reason=request.data.get('reason', '')
        )

        return Response(AdvisorAccessGrantSerializer(grant).data)
