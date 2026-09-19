"""
Permissions for the Identity & Access bounded context.

These are DRF permission classes. They are referenced from
config/settings/base.py's REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"], so they
apply to every API view unless a view overrides them.
"""

from rest_framework.permissions import BasePermission

__all__ = ["TenantScopedPermission"]


class TenantScopedPermission(BasePermission):
    """Require an established tenant context on the request.

    TenantContextMiddleware resolves the tenant from the X-Tenant-ID header, the
    session, or JWT claims, and records it as ``request.tenant_id``. This
    permission rejects any request for which no tenant could be resolved, so a
    request cannot fall through to an unscoped query.

    It is deliberately a coarse gate: it answers "is there a tenant context at
    all", not "is this user permitted in that tenant". Per-object and
    per-action authorization belongs to the domain services
    (apps.identity.services.authorization.AuthorizationService).
    """

    message = "A tenant context is required for this endpoint."

    def has_permission(self, request, view) -> bool:
        return bool(getattr(request, "tenant_id", None))
