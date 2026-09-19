"""
Authorization Service

Handles permission checks and role-based access control:
- Permission resolution for users across tenants and entities
- Role assignment and revocation
- Advisor access grant evaluation
- Tenant-scoped authorization (defense-in-depth with RLS)
"""
from django.db.models import Q
from django.utils import timezone

from apps.identity.models import (
    AdvisorAccessGrant,
    Membership,
    Role,
    Tenant,
)

# Only an 'active' membership confers access. 'invited' has not been accepted,
# and 'suspended'/'deactivated' have been deliberately withdrawn - treating any
# of them as membership would mean a revoked user keeps their access.
_ACTIVE_MEMBERSHIP_STATUS = "active"

# Likewise for the engagement linking a practice to a client tenant.
_ACTIVE_ENGAGEMENT_STATUS = "active"


class AuthorizationService:
    """Service for evaluating permissions and managing access control."""

    @staticmethod
    def is_tenant_member(user, tenant) -> bool:
        """Check whether a user is an active member of a tenant.

        Args:
            user: The user to check.
            tenant: The tenant to check membership of.

        Returns:
            True if an active membership exists, False otherwise.
        """
        if user is None or tenant is None or not user.is_authenticated:
            return False

        return Membership.objects.filter(
            user=user,
            tenant=tenant,
            status=_ACTIVE_MEMBERSHIP_STATUS,
        ).exists()

    @staticmethod
    def get_accessible_tenants(user):
        """Return the tenants a user can currently access.

        Args:
            user: The user to resolve tenants for.

        Returns:
            A queryset of active Tenants in which the user holds an active
            membership. A queryset rather than a list so it composes with
            further filtering, and empty rather than None so callers can
            iterate it unconditionally.
        """
        if user is None or not user.is_authenticated:
            return Tenant.objects.none()

        return Tenant.objects.filter(
            memberships__user=user,
            memberships__status=_ACTIVE_MEMBERSHIP_STATUS,
            is_active=True,
        ).distinct()

    @staticmethod
    def has_permission(user, tenant, permission_codename: str) -> bool:
        """Check whether a user's role in a tenant grants a permission.

        Accounting Semantics:
            Permission is resolved through the user's *role*, never granted
            directly: a Membership names a role, and the role carries the
            permissions. That indirection is the point - revoking a permission
            from a role revokes it from everyone holding that role, and a
            membership with no role resolves to nothing.

        Args:
            user: The user to check.
            tenant: The tenant the permission is being exercised in.
            permission_codename: Codename of the permission
                (e.g. 'view_invoices').

        Returns:
            True only if the user is active, holds an active membership in the
            tenant, and one of that membership's roles carries the permission.
            False otherwise.
        """
        if user is None or tenant is None or not permission_codename:
            return False

        # An inactive user holds no permissions at all. This is checked before
        # the membership lookup because deactivation must revoke access
        # immediately, not merely at the next membership edit.
        if not user.is_authenticated or not user.is_active:
            return False

        role_names = list(
            Membership.objects.filter(
                user=user,
                tenant=tenant,
                status=_ACTIVE_MEMBERSHIP_STATUS,
            ).values_list("role", flat=True)
        )

        if not role_names:
            return False

        # Roles are matched by name because Membership.role is a string, not a
        # foreign key. A role is in scope if it belongs to this tenant or is a
        # system role (tenant is NULL) - system roles are shared across tenants.
        #
        # The permissions themselves come from Role.get_permissions(), so the
        # RolePermission join is written down in exactly one place. Resolving it
        # here independently is what let the model method rot into a reference
        # to a relation that was never declared.
        in_scope_roles = Role.objects.filter(name__in=role_names).filter(
            Q(tenant=tenant) | Q(tenant__isnull=True)
        )

        return any(
            role.get_permissions().filter(codename=permission_codename).exists()
            for role in in_scope_roles
        )

    @staticmethod
    def can_access_tenant(user, tenant) -> bool:
        """Check whether a user can access a tenant, directly or as an advisor.

        Accounting Semantics:
            There are exactly two ways in, and they are not interchangeable:

            1. Direct membership - the user belongs to the tenant.
            2. Advisor access - the user belongs to a *practice* that has an
               active engagement with the tenant, and the client has granted
               that specific user an active AdvisorAccessGrant.

            The engagement alone is not enough, and the practice membership
            alone is not enough. A practice has access to a client's books only
            because the client said so, per user, revocably - which is what
            BR-PRACTICE-004 exists to protect.

        Args:
            user: The user to check.
            tenant: The tenant being accessed.

        Returns:
            True if either route grants access, False otherwise.
        """
        if user is None or tenant is None:
            return False

        if not user.is_authenticated or not user.is_active:
            return False

        if AuthorizationService.is_tenant_member(user, tenant):
            return True

        return AdvisorAccessGrant.objects.filter(
            # The grant must name this user...
            Q(practice_user=user)
            # ...the user must still belong to the practice...
            & Q(engagement__practice__memberships__user=user)
            & Q(engagement__practice__memberships__status=_ACTIVE_MEMBERSHIP_STATUS)
            # ...the engagement with this client must still be live...
            & Q(engagement__tenant=tenant)
            & Q(engagement__status=_ACTIVE_ENGAGEMENT_STATUS)
            # ...and the client must not have revoked or outlived the grant.
            & Q(revoked_at__isnull=True)
            & (Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        ).exists()

    # --- Not yet implemented -------------------------------------------------
    # `user_has_permission` and `get_user_permissions` overlap heavily with
    # `has_permission` above and are left as stubs rather than guessed at: they
    # take an optional entity scope, and how a role's permissions narrow to a
    # legal entity is a design decision that has not been made.

    def user_has_permission(self, user, permission_codename: str, tenant=None, entity=None) -> bool:
        """Check whether a user has a specific permission.

        See `has_permission`, which is the implemented, tenant-scoped form.

        Args:
            user: The user to check.
            permission_codename: Codename of the permission (e.g. 'create_invoice').
            tenant: Optional tenant scope.
            entity: Optional legal entity scope.

        Returns:
            True if the user has the permission, False otherwise.
        """
        raise NotImplementedError("AuthorizationService.user_has_permission is not yet implemented")

    def get_user_permissions(self, user, tenant=None, entity=None) -> list:
        """Return all permission codenames for a user in a given scope."""
        raise NotImplementedError("AuthorizationService.get_user_permissions is not yet implemented")

    def assign_role(self, user, role, tenant, entity=None):
        """Assign a role to a user within a tenant (and optional entity scope)."""
        raise NotImplementedError("AuthorizationService.assign_role is not yet implemented")

    def revoke_role(self, membership):
        """Revoke a role (deactivate the membership)."""
        raise NotImplementedError("AuthorizationService.revoke_role is not yet implemented")

    def check_advisor_access(self, practice_user, tenant, entity=None):
        """Check whether a practice user has active access to a client tenant.

        See `can_access_tenant`, which is the implemented form.
        """
        raise NotImplementedError("AuthorizationService.check_advisor_access is not yet implemented")
