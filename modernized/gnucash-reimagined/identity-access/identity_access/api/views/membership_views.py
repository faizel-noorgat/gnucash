"""
Membership Views

API views for membership and invitation management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from ..domain.models import Tenant, Membership
from ..domain.services.membership_service import MembershipService
from ..domain.services.authorization_service import AuthorizationService
from .serializers import MembershipSerializer, MembershipInviteSerializer


class MembershipViewSet(viewsets.ViewSet):
    """
    ViewSet for Membership management.

    GET /api/v1/tenants/{tenant_slug}/members/ - List members
    POST /api/v1/tenants/{tenant_slug}/members/invite/ - Invite user
    POST /api/v1/invitations/{token}/accept/ - Accept invitation
    """
    permission_classes = [IsAuthenticated]

    def list(self, request, tenant_slug=None):
        """List members of tenant."""
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

        if not AuthorizationService.can_access_tenant(request.user, tenant):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        members = MembershipService.get_tenant_members(tenant)
        serializer = MembershipSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='invite')
    def invite(self, request, tenant_slug=None):
        """Invite user to tenant."""
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

        if not AuthorizationService.has_permission(
            request.user,
            tenant,
            'invite_member'
        ):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = MembershipInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            membership = MembershipService.invite_user(
                tenant=tenant,
                email=serializer.validated_data['email'],
                role=serializer.validated_data['role'],
                invited_by=request.user,
                scoped_entity=serializer.validated_data.get('scoped_entity')
            )

            return Response(
                MembershipSerializer(membership).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='accept')
    def accept_invitation(self, request, token=None):
        """Accept membership invitation."""
        try:
            membership = MembershipService.accept_invitation(
                invitation_token=token,
                user=request.user
            )

            return Response(MembershipSerializer(membership).data)
        except Membership.DoesNotExist:
            return Response(
                {'error': 'Invalid invitation token'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['patch'], url_path='update-role')
    def update_role(self, request, tenant_slug=None, pk=None):
        """Update member role."""
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

        if not AuthorizationService.has_permission(
            request.user,
            tenant,
            'manage_member'
        ):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        membership = get_object_or_404(Membership, guid=pk, tenant=tenant)
        new_role = request.data.get('role')

        if not new_role:
            return Response(
                {'error': 'Role is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        MembershipService.update_membership_role(
            membership=membership,
            new_role=new_role,
            updated_by=request.user
        )

        return Response(MembershipSerializer(membership).data)

    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_member(self, request, tenant_slug=None, pk=None):
        """Remove member from tenant."""
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

        if not AuthorizationService.has_permission(
            request.user,
            tenant,
            'manage_member'
        ):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        membership = get_object_or_404(Membership, guid=pk, tenant=tenant)
        MembershipService.remove_member(membership, request.user)

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserMembershipsViewSet(viewsets.ViewSet):
    """
    ViewSet for user's own memberships.

    GET /api/v1/memberships/ - List user's memberships
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List user's memberships."""
        memberships = MembershipService.get_user_memberships(request.user)
        serializer = MembershipSerializer(memberships, many=True)
        return Response(serializer.data)
