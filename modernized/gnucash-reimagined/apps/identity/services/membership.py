"""
Membership Service

Handles user membership and invitation management for tenant workspaces:
- Invite users to a tenant
- Accept/decline invitations
- Update membership roles
- Remove members from a tenant

Behaviour migrated from the round-one standalone Identity & Access service
(``identity-access/identity_access/domain/services/membership_service.py``),
retargeted at the unified ``apps.identity.models`` model layer.
"""

import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.identity.models import Membership, User

# Frontend base URL used to build invitation links. The round-one service read
# settings.FRONTEND_URL directly; the unified settings module does not define it
# yet, so fall back to the same default the round-one .env.example shipped.
_DEFAULT_FRONTEND_URL = "http://localhost:3000"


class MembershipService:
    """
    Service for membership management operations.

    Responsibilities:
    - Invite users to tenant
    - Accept/decline invitations
    - Update membership roles
    - Remove members from tenant
    """

    @staticmethod
    @transaction.atomic
    def invite_user(tenant, email, role, invited_by, scoped_entity=None):
        """
        Invite user to tenant.

        Args:
            tenant: Tenant object
            email: User email
            role: Role name
            invited_by: User sending invitation
            scoped_entity: Optional LegalEntity for entity-scoped membership

        Returns:
            Created Membership object

        Raises:
            ValueError: If the user is already an active or invited member.
        """
        # Get or create user
        user, _created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "is_active": False,  # Will be activated when invitation accepted
            },
        )

        # Check if membership already exists
        existing = Membership.objects.filter(
            user=user,
            tenant=tenant,
            scoped_entity=scoped_entity,
        ).first()

        if existing:
            if existing.status == "active":
                raise ValueError(f"User is already an active member of {tenant.name}")
            elif existing.status == "invited":
                raise ValueError(f"User has already been invited to {tenant.name}")
            else:
                # Re-activate previous membership
                existing.status = "invited"
                existing.role = role
                existing.invited_by = invited_by
                existing.invited_at = timezone.now()
                existing.invitation_token = secrets.token_urlsafe(32)
                existing.save()
                membership = existing
        else:
            # Create new membership
            membership = Membership.objects.create(
                user=user,
                tenant=tenant,
                role=role,
                status="invited",
                invited_by=invited_by,
                invited_at=timezone.now(),
                invitation_token=secrets.token_urlsafe(32),
                scoped_entity=scoped_entity,
            )

        # Send invitation email
        MembershipService._send_invitation_email(membership)

        return membership

    @staticmethod
    def _send_invitation_email(membership):
        """
        Send invitation email to user.

        Args:
            membership: Membership object
        """
        frontend_url = getattr(settings, "FRONTEND_URL", _DEFAULT_FRONTEND_URL)

        subject = f"You've been invited to join {membership.tenant.name}"
        message = f"""
        Hello,

        You've been invited to join {membership.tenant.name} as a {membership.get_role_display()}.

        Click the link below to accept the invitation:
        {frontend_url}/accept-invitation/{membership.invitation_token}

        This invitation was sent by {membership.invited_by.email}.

        If you did not expect this invitation, you can safely ignore this email.
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [membership.user.email],
            fail_silently=False,
        )

    @staticmethod
    @transaction.atomic
    def accept_invitation(invitation_token, user=None):
        """
        Accept membership invitation.

        Args:
            invitation_token: Invitation token
            user: User accepting invitation (optional - will use token to find user)

        Returns:
            Membership object

        Raises:
            Membership.DoesNotExist: If no pending invitation matches the token.
            ValueError: If the invitation belongs to a different user.
        """
        membership = Membership.objects.get(
            invitation_token=invitation_token,
            status="invited",
        )

        # If user provided, verify it matches
        if user and user != membership.user:
            raise ValueError("Invitation is for a different user")

        # Activate membership
        membership.accept_invitation()

        # Activate user if not already active
        if not membership.user.is_active:
            membership.user.is_active = True
            membership.user.save()

        return membership

    @staticmethod
    @transaction.atomic
    def update_membership_role(membership, new_role, updated_by):
        """
        Update membership role.

        Args:
            membership: Membership object
            new_role: New role name
            updated_by: User updating the role
        """
        membership.role = new_role
        membership.save()

    @staticmethod
    @transaction.atomic
    def remove_member(membership, removed_by):
        """
        Remove member from tenant.

        Args:
            membership: Membership object
            removed_by: User removing the member
        """
        membership.status = "deactivated"
        membership.save()

    @staticmethod
    def get_tenant_members(tenant):
        """
        Get all active members of tenant.

        Args:
            tenant: Tenant object

        Returns:
            QuerySet of Membership objects
        """
        return Membership.objects.filter(
            tenant=tenant,
            status="active",
        ).select_related("user")

    @staticmethod
    def get_user_memberships(user):
        """
        Get all memberships for user.

        Args:
            user: User object

        Returns:
            QuerySet of Membership objects
        """
        return Membership.objects.filter(
            user=user,
            status="active",
        ).select_related("tenant")

    @staticmethod
    def get_invitation_by_token(token):
        """
        Get membership invitation by token.

        Args:
            token: Invitation token

        Returns:
            Membership object or None
        """
        try:
            return Membership.objects.get(
                invitation_token=token,
                status="invited",
            )
        except Membership.DoesNotExist:
            return None
