"""
Authorization Service

Handles permission checking and access control.
"""
from django.db.models import Q
from ..models import User, Tenant, Membership, Role, Permission, AdvisorAccessGrant, PracticeMembership


class AuthorizationService:
    """
    Service for authorization operations.

    Responsibilities:
    - Check if user has permission for resource
    - Check tenant membership
    - Check practice/advisor access
    - Entity-scoped permission checking
    """

    @staticmethod
    def has_permission(user, tenant, permission_codename, entity=None):
        """
        Check if user has specific permission in tenant.

        Args:
            user: User object
            tenant: Tenant object
            permission_codename: Permission codename string
            entity: Optional LegalEntity for entity-scoped permissions

        Returns:
            True if user has permission, False otherwise
        """
        if not user.is_active:
            return False

        # Check direct membership
        membership = Membership.objects.filter(
            user=user,
            tenant=tenant,
            status='active'
        ).first()

        if membership:
            # Check if membership has entity scope
            if entity and membership.scoped_entity and membership.scoped_entity != entity:
                pass  # Membership is scoped to different entity
            else:
                # Check if role has permission
                if AuthorizationService._role_has_permission(membership.role, permission_codename):
                    return True

        # Check advisor access grant
        if AuthorizationService._has_advisor_access(user, tenant, permission_codename, entity):
            return True

        return False

    @staticmethod
    def _role_has_permission(role, permission_codename):
        """
        Check if role has specific permission.

        Args:
            role: Role name string
            permission_codename: Permission codename string

        Returns:
            True if role has permission, False otherwise
        """
        # Get role object
        try:
            role_obj = Role.objects.get(name=role, is_active=True)
        except Role.DoesNotExist:
            return False

        # Check if role has permission
        return role_obj.role_permissions.filter(
            permission__codename=permission_codename,
            permission__is_active=True
        ).exists()

    @staticmethod
    def _has_advisor_access(user, tenant, permission_codename, entity=None):
        """
        Check if user has advisor access to tenant with specific permission.

        Args:
            user: User object
            tenant: Tenant object
            permission_codename: Permission codename string
            entity: Optional LegalEntity for entity-scoped permissions

        Returns:
            True if user has advisor access with permission, False otherwise
        """
        # Check if user is practice member
        practice_membership = PracticeMembership.objects.filter(
            user=user,
            status='active'
        ).first()

        if not practice_membership:
            return False

        # Check for active advisor access grant
        grants = AdvisorAccessGrant.objects.filter(
            practice_user=user,
            engagement__tenant=tenant,
            engagement__status='active',
            revoked_at__isnull=True
        )

        # Filter by entity scope if specified
        if entity:
            grants = grants.filter(
                Q(scoped_entity__isnull=True) | Q(scoped_entity=entity)
            )

        # Check if any grant has the required permission
        for grant in grants:
            if grant.is_active and AuthorizationService._role_has_permission(
                grant.tenant_role.name,
                permission_codename
            ):
                return True

        return False

    @staticmethod
    def is_tenant_member(user, tenant):
        """
        Check if user is a member of tenant.

        Args:
            user: User object
            tenant: Tenant object

        Returns:
            True if user is tenant member, False otherwise
        """
        return Membership.objects.filter(
            user=user,
            tenant=tenant,
            status='active'
        ).exists()

    @staticmethod
    def is_practice_member(user, practice):
        """
        Check if user is a member of practice.

        Args:
            user: User object
            practice: Practice object

        Returns:
            True if user is practice member, False otherwise
        """
        return PracticeMembership.objects.filter(
            user=user,
            practice=practice,
            status='active'
        ).exists()

    @staticmethod
    def can_access_tenant(user, tenant):
        """
        Check if user can access tenant (as member or advisor).

        Args:
            user: User object
            tenant: Tenant object

        Returns:
            True if user can access tenant, False otherwise
        """
        # Check direct membership
        if AuthorizationService.is_tenant_member(user, tenant):
            return True

        # Check advisor access
        return AdvisorAccessGrant.objects.filter(
            practice_user=user,
            engagement__tenant=tenant,
            engagement__status='active',
            revoked_at__isnull=True
        ).exists()

    @staticmethod
    def get_user_permissions(user, tenant, entity=None):
        """
        Get all permissions for user in tenant.

        Args:
            user: User object
            tenant: Tenant object
            entity: Optional LegalEntity for entity-scoped permissions

        Returns:
            Set of permission codenames
        """
        permissions = set()

        # Get permissions from direct membership
        membership = Membership.objects.filter(
            user=user,
            tenant=tenant,
            status='active'
        ).first()

        if membership:
            if not entity or not membership.scoped_entity or membership.scoped_entity == entity:
                role_perms = Permission.objects.filter(
                    role_permissions__role__name=membership.role,
                    role_permissions__role__is_active=True,
                    is_active=True
                ).values_list('codename', flat=True)
                permissions.update(role_perms)

        # Get permissions from advisor access grants
        grants = AdvisorAccessGrant.objects.filter(
            practice_user=user,
            engagement__tenant=tenant,
            engagement__status='active',
            revoked_at__isnull=True
        )

        if entity:
            grants = grants.filter(
                Q(scoped_entity__isnull=True) | Q(scoped_entity=entity)
            )

        for grant in grants:
            if grant.is_active:
                grant_perms = Permission.objects.filter(
                    role_permissions__role=grant.tenant_role,
                    role_permissions__role__is_active=True,
                    is_active=True
                ).values_list('codename', flat=True)
                permissions.update(grant_perms)

        return permissions

    @staticmethod
    def get_accessible_tenants(user):
        """
        Get all tenants user can access.

        Args:
            user: User object

        Returns:
            QuerySet of Tenant objects
        """
        # Tenants from direct membership
        member_tenants = Tenant.objects.filter(
            memberships__user=user,
            memberships__status='active',
            is_active=True
        )

        # Tenants from advisor access
        advisor_tenants = Tenant.objects.filter(
            practice_engagements__access_grants__practice_user=user,
            practice_engagements__status='active',
            practice_engagements__access_grants__revoked_at__isnull=True,
            is_active=True
        )

        return (member_tenants | advisor_tenants).distinct()
