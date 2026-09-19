"""
Practice Service

Handles practice/advisor access management:
- Create and manage practices
- Manage practice memberships
- Create client engagements
- Grant and revoke advisor access to client tenants

Behaviour migrated from the round-one standalone Identity & Access service
(``identity-access/identity_access/domain/services/practice_service.py``),
retargeted at the unified ``apps.identity.models`` model layer.

Note on bounded contexts: practices, engagements and advisor access grants all
belong to the Identity & Access context, so this service stays entirely
in-process. Client tenant data that a practice user reaches through an
engagement is owned by the Accounting context and is reached via that
context's own application services, never from here.
"""

import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.identity.models import (
    AdvisorAccessGrant,
    ClientEngagement,
    Practice,
    PracticeMembership,
    User,
)

# Frontend base URL used to build invitation links. The round-one service read
# settings.FRONTEND_URL directly; the unified settings module does not define it
# yet, so fall back to the same default the round-one .env.example shipped.
_DEFAULT_FRONTEND_URL = "http://localhost:3000"


class PracticeService:
    """
    Service for practice/advisor access management.

    Responsibilities:
    - Create and manage practices
    - Manage practice memberships
    - Create client engagements
    - Grant and revoke advisor access
    """

    @staticmethod
    @transaction.atomic
    def create_practice(name, slug, created_by, **kwargs):
        """
        Create a new practice.

        Args:
            name: Practice name
            slug: Practice slug (unique identifier)
            created_by: User creating the practice
            **kwargs: Additional practice fields

        Returns:
            Created Practice object
        """
        practice = Practice.objects.create(
            name=name,
            slug=slug,
            created_by=created_by,
            **kwargs,
        )

        # Add creator as practice admin
        PracticeMembership.objects.create(
            user=created_by,
            practice=practice,
            role="admin",
            status="active",
        )

        return practice

    @staticmethod
    @transaction.atomic
    def invite_to_practice(practice, email, role, invited_by):
        """
        Invite user to practice.

        Args:
            practice: Practice object
            email: User email
            role: Practice role (partner, manager, senior, staff)
            invited_by: User sending invitation

        Returns:
            Created PracticeMembership object

        Raises:
            ValueError: If the user is already an active or invited member.
        """
        # Get or create user
        user, _created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "is_active": False,
            },
        )

        # Check if membership already exists
        existing = PracticeMembership.objects.filter(
            user=user,
            practice=practice,
        ).first()

        if existing:
            if existing.status == "active":
                raise ValueError(f"User is already an active member of {practice.name}")
            elif existing.status == "invited":
                raise ValueError(f"User has already been invited to {practice.name}")
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
            membership = PracticeMembership.objects.create(
                user=user,
                practice=practice,
                role=role,
                status="invited",
                invited_by=invited_by,
                invited_at=timezone.now(),
                invitation_token=secrets.token_urlsafe(32),
            )

        # Send invitation email
        PracticeService._send_practice_invitation_email(membership)

        return membership

    @staticmethod
    def _send_practice_invitation_email(membership):
        """
        Send practice invitation email to user.

        Args:
            membership: PracticeMembership object
        """
        frontend_url = getattr(settings, "FRONTEND_URL", _DEFAULT_FRONTEND_URL)

        subject = f"You've been invited to join {membership.practice.name}"
        message = f"""
        Hello,

        You've been invited to join {membership.practice.name} as a {membership.get_role_display()}.

        Click the link below to accept the invitation:
        {frontend_url}/accept-practice-invitation/{membership.invitation_token}

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
    def accept_practice_invitation(invitation_token):
        """
        Accept practice membership invitation.

        Args:
            invitation_token: Invitation token

        Returns:
            PracticeMembership object

        Raises:
            PracticeMembership.DoesNotExist: If no pending invitation matches the token.
        """
        membership = PracticeMembership.objects.get(
            invitation_token=invitation_token,
            status="invited",
        )

        membership.accept_invitation()

        # Activate user if not already active
        if not membership.user.is_active:
            membership.user.is_active = True
            membership.user.save()

        return membership

    @staticmethod
    @transaction.atomic
    def create_client_engagement(practice, tenant, engagement_type, created_by, **kwargs):
        """
        Create client engagement between practice and tenant.

        Args:
            practice: Practice object
            tenant: Tenant object
            engagement_type: Type of engagement
            created_by: User creating the engagement
            **kwargs: Additional engagement fields

        Returns:
            Created ClientEngagement object
        """
        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=tenant,
            engagement_type=engagement_type,
            status="pending",
            created_by=created_by,
            **kwargs,
        )

        return engagement

    @staticmethod
    @transaction.atomic
    def activate_engagement(engagement):
        """
        Activate client engagement.

        Args:
            engagement: ClientEngagement object
        """
        engagement.activate()

    @staticmethod
    @transaction.atomic
    def terminate_engagement(engagement):
        """
        Terminate client engagement.

        Args:
            engagement: ClientEngagement object
        """
        engagement.terminate()

        # Revoke all access grants for this engagement
        engagement.access_grants.filter(revoked_at__isnull=True).update(
            revoked_at=timezone.now(),
            revocation_reason="Engagement terminated",
        )

    @staticmethod
    @transaction.atomic
    def grant_advisor_access(
        engagement,
        practice_user,
        tenant_role,
        granted_by,
        scoped_entity=None,
        expires_at=None,
        reason="",
    ):
        """
        Grant advisor access to practice user for client tenant.

        Args:
            engagement: ClientEngagement object
            practice_user: User receiving access
            tenant_role: Role within client tenant (a ``Role`` instance —
                ``AdvisorAccessGrant.tenant_role`` is a FK to ``identity.Role``)
            granted_by: User granting access
            scoped_entity: Optional LegalEntity for entity-scoped access
            expires_at: Optional expiration datetime
            reason: Reason for granting access

        Returns:
            Created AdvisorAccessGrant object

        Raises:
            ValueError: If the practice user is not an active practice member.
        """
        # Verify practice user is member of practice
        if not PracticeMembership.objects.filter(
            user=practice_user,
            practice=engagement.practice,
            status="active",
        ).exists():
            raise ValueError("User is not an active member of the practice")

        grant = AdvisorAccessGrant.objects.create(
            engagement=engagement,
            practice_user=practice_user,
            tenant_role=tenant_role,
            scoped_entity=scoped_entity,
            expires_at=expires_at,
            granted_by=granted_by,
            reason=reason,
        )

        return grant

    @staticmethod
    @transaction.atomic
    def revoke_advisor_access(grant, revoked_by, reason=""):
        """
        Revoke advisor access grant.

        Args:
            grant: AdvisorAccessGrant object
            revoked_by: User revoking access
            reason: Reason for revocation
        """
        grant.revoke(revoked_by, reason)

    @staticmethod
    def get_practice_engagements(practice):
        """
        Get all engagements for practice.

        Args:
            practice: Practice object

        Returns:
            QuerySet of ClientEngagement objects
        """
        return ClientEngagement.objects.filter(practice=practice).select_related("tenant")

    @staticmethod
    def get_tenant_engagements(tenant):
        """
        Get all engagements for tenant.

        Args:
            tenant: Tenant object

        Returns:
            QuerySet of ClientEngagement objects
        """
        return ClientEngagement.objects.filter(tenant=tenant).select_related("practice")

    @staticmethod
    def get_user_practices(user):
        """
        Get all practices user is member of.

        Args:
            user: User object

        Returns:
            QuerySet of PracticeMembership objects
        """
        return PracticeMembership.objects.filter(
            user=user,
            status="active",
        ).select_related("practice")
