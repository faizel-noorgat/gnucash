"""
API Permissions

Custom permission classes for API access control.
"""
from rest_framework import permissions
from ..domain.services.authorization_service import AuthorizationService


class TenantMemberPermission(permissions.BasePermission):
    """
    Permission class that checks if user is a member of the tenant.
    """

    def has_object_permission(self, request, view, obj):
        """Check if user is member of object's tenant."""
        # Get tenant from object
        tenant = getattr(obj, 'tenant', None)
        if not tenant:
            return True

        return AuthorizationService.is_tenant_member(request.user, tenant)


class TenantPermission(permissions.BasePermission):
    """
    Permission class that checks if user has specific permission in tenant.
    """

    def __init__(self, permission_codename):
        self.permission_codename = permission_codename

    def has_object_permission(self, request, view, obj):
        """Check if user has permission in object's tenant."""
        # Get tenant from object
        tenant = getattr(obj, 'tenant', None)
        if not tenant:
            return True

        return AuthorizationService.has_permission(
            request.user,
            tenant,
            self.permission_codename
        )


class PracticeMemberPermission(permissions.BasePermission):
    """
    Permission class that checks if user is a member of the practice.
    """

    def has_object_permission(self, request, view, obj):
        """Check if user is member of object's practice."""
        # Get practice from object
        practice = getattr(obj, 'practice', None)
        if not practice:
            return True

        return AuthorizationService.is_practice_member(request.user, practice)


class CanAccessTenantPermission(permissions.BasePermission):
    """
    Permission class that checks if user can access tenant (member or advisor).
    """

    def has_object_permission(self, request, view, obj):
        """Check if user can access object's tenant."""
        # Get tenant from object
        tenant = getattr(obj, 'tenant', None)
        if not tenant:
            return True

        return AuthorizationService.can_access_tenant(request.user, tenant)
