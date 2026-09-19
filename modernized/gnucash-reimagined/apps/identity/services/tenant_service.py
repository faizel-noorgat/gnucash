"""
Tenant Service

Handles tenant lifecycle and multi-tenancy operations:
- Tenant creation and onboarding
- Legal entity management within a tenant
- Tenant member invitation and deactivation
- Tenant context resolution for the current request
- Defense-in-depth enforcement (RLS + ORM default filters)
"""
from django.db import transaction

from apps.identity.models import LegalEntity, Membership, Tenant

# The user who creates a tenant owns it. 'admin' would be wrong here: an admin
# administers a tenant someone else owns, and the creator is the only principal
# who can be assumed to have authority over it at creation time.
_OWNER_ROLE = "owner"

# A creator is a member from the moment the tenant exists - they are not an
# invitee, so there is no invitation to accept and no 'invited' interval during
# which the tenant would have no one who can administer it.
_ACTIVE_MEMBERSHIP_STATUS = "active"


class TenantService:
    """Service for managing tenants and tenant-scoped operations."""

    @staticmethod
    @transaction.atomic
    def create_tenant(name: str, slug: str, created_by, **kwargs):
        """Create a new tenant (SME customer organization).

        Accounting Semantics:
            A tenant with no legal entity has nowhere to keep a ledger and no
            base currency, so the default entity is created here rather than
            left to the caller. The whole thing is one transaction: a tenant
            that exists without its owner, or without an entity to post into,
            is not a state any caller should ever observe.

        Args:
            name: Display name of the tenant.
            slug: URL-safe unique slug.
            created_by: User who creates the tenant, and who becomes its owner.
            **kwargs: Additional Tenant fields (organization_name,
                contact_email, default_currency, ...).

        Returns:
            The newly created Tenant instance.
        """
        tenant = Tenant.objects.create(
            name=name,
            slug=slug,
            created_by=created_by,
            **kwargs,
        )

        # Named after the tenant: the common case is a single-entity SME, and a
        # clearer name can be set as soon as a second entity makes it ambiguous.
        LegalEntity.objects.create(
            tenant=tenant,
            name=name,
            created_by=created_by,
        )

        Membership.objects.create(
            user=created_by,
            tenant=tenant,
            role=_OWNER_ROLE,
            status=_ACTIVE_MEMBERSHIP_STATUS,
        )

        return tenant

    @staticmethod
    def get_tenant(slug: str):
        """Get a tenant by its slug.

        Args:
            slug: The tenant's unique slug.

        Returns:
            The Tenant, or None if no tenant has that slug. None rather than a
            Tenant.DoesNotExist so callers resolving a slug from a URL can turn
            it into a 404 without catching a model exception.
        """
        if not slug:
            return None

        return Tenant.objects.filter(slug=slug).first()

    # --- Not yet implemented -------------------------------------------------
    # Separate features rather than gaps in the methods above; invitation needs
    # outbound email, and tenant context resolution needs the request/middleware
    # contract settled.

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
