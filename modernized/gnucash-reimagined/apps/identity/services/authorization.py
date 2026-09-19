"""
Authorization Service

Handles permission checks and role-based access control:
- Permission resolution for users across tenants and entities
- Role assignment and revocation
- Advisor access grant evaluation
- Tenant-scoped authorization (defense-in-depth with RLS)
"""


class AuthorizationService:
    """Service for evaluating permissions and managing access control.

    Stub implementation — populate with authorization logic as the
    bounded context is built out.
    """

    def user_has_permission(self, user, permission_codename: str, tenant=None, entity=None) -> bool:
        """Check whether a user has a specific permission.

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
        """Check whether a practice user has active access to a client tenant."""
        raise NotImplementedError("AuthorizationService.check_advisor_access is not yet implemented")
