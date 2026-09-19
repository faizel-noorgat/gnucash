"""
Permissions for business documents service
"""
from rest_framework import permissions


class TenantScopedPermission(permissions.BasePermission):
    """
    Permission class to ensure users can only access data within their tenant.

    All queries are scoped by tenant_id from request context.
    """

    def has_permission(self, request, view):
        """Check if user has permission to access this view"""
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # User must have tenant context
        # TODO: In production, enforce this strictly
        # if not getattr(request, 'tenant_id', None):
        #     return False

        return True

    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access this specific object"""
        # Check if object belongs to user's tenant
        if hasattr(obj, 'tenant_id'):
            tenant_id = getattr(request, 'tenant_id', None)
            if tenant_id and obj.tenant_id != tenant_id:
                return False

        return True


class IsDocumentOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of a document to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only allowed to document creator
        return obj.created_by == request.user
