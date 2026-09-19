"""
Tenant Service

Handles tenant lifecycle and multi-tenancy operations:
- Tenant creation and onboarding
- Legal entity management within a tenant
- Tenant member invitation and deactivation
- Tenant context resolution for the current request
- Defense-in-depth enforcement (RLS + ORM default filters)
"""


class TenantService:
    """Service for managing tenants and tenant-scoped operations.

    Stub implementation — populate with tenant management logic as the
    bounded context is built out.
    """

    def create_tenant(self, name: str, slug: str, created_by, **kwargs):
        """Create a new tenant (SME customer organization).

        Args:
            name: Display name of the tenant.
            slug: URL-safe unique slug.
            created_by: User who creates the tenant.
            **kwargs: Additional fields (organization_name, contact_email, etc.).

        Returns:
            The newly created Tenant instance.
        """
        raise NotImplementedError("TenantService.create_tenant is not yet implemented")

    def invite_member(self, tenant, email: str, role: str, invited_by, entity=None):
        """Invite a user to become a member of a tenant.

        Args:
            tenant: The tenant to invite the user to.
            email: Email address of the invitee.
            role: Role to assign (e.g. 'owner', 'accountant', 'viewer').
            invited_by: User sending the invitation.
            entity: Optional legal entity scope.

        Returns:
            The newly created Membership in 'invited' status.
        """
        raise NotImplementedError("TenantService.invite_member is not yet implemented")

    def create_legal_entity(self, tenant, name: str, created_by, **kwargs):
        """Create a new legal entity within a tenant.

        Args:
            tenant: The parent tenant.
            name: Display name of the legal entity.
            created_by: User creating the entity.
            **kwargs: Additional fields (entity_type, base_currency, etc.).

        Returns:
            The newly created LegalEntity instance.
        """
        raise NotImplementedError("TenantService.create_legal_entity is not yet implemented")

    def get_user_tenants(self, user) -> list:
        """Return all tenants the user is an active member of."""
        raise NotImplementedError("TenantService.get_user_tenants is not yet implemented")

    def resolve_tenant_context(self, user, tenant_slug: str):
        """Resolve the tenant context for the current request.

        Used by middleware to set the active tenant on the request.
        """
        raise NotImplementedError("TenantService.resolve_tenant_context is not yet implemented")
