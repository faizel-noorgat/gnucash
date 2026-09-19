"""
Tenant Service

Handles tenant/workspace management operations.
"""
from django.db import transaction
from django.utils import timezone
from ..models import Tenant, LegalEntity, Membership


class TenantService:
    """
    Service for tenant management operations.

    Responsibilities:
    - Create tenant with initial setup
    - Manage tenant lifecycle
    - Create legal entities within tenant
    - Tenant settings management
    """

    @staticmethod
    @transaction.atomic
    def create_tenant(name, slug, created_by, **kwargs):
        """
        Create a new tenant with initial setup.

        Args:
            name: Tenant name
            slug: Tenant slug (unique identifier)
            created_by: User creating the tenant
            **kwargs: Additional tenant fields

        Returns:
            Created Tenant object
        """
        # Create tenant
        tenant = Tenant.objects.create(
            name=name,
            slug=slug,
            created_by=created_by,
            **kwargs
        )

        # Create default legal entity
        LegalEntity.objects.create(
            tenant=tenant,
            name=f'{name} - Default Entity',
            created_by=created_by
        )

        # Add creator as owner
        Membership.objects.create(
            user=created_by,
            tenant=tenant,
            role='owner',
            status='active'
        )

        return tenant

    @staticmethod
    def get_tenant(slug):
        """
        Get tenant by slug.

        Args:
            slug: Tenant slug

        Returns:
            Tenant object or None
        """
        try:
            return Tenant.objects.get(slug=slug, is_active=True)
        except Tenant.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def create_legal_entity(tenant, name, created_by, **kwargs):
        """
        Create a new legal entity within tenant.

        Args:
            tenant: Tenant object
            name: Legal entity name
            created_by: User creating the entity
            **kwargs: Additional legal entity fields

        Returns:
            Created LegalEntity object
        """
        return LegalEntity.objects.create(
            tenant=tenant,
            name=name,
            created_by=created_by,
            **kwargs
        )

    @staticmethod
    def get_tenant_entities(tenant):
        """
        Get all legal entities for tenant.

        Args:
            tenant: Tenant object

        Returns:
            QuerySet of LegalEntity objects
        """
        return LegalEntity.objects.filter(tenant=tenant, is_active=True)

    @staticmethod
    @transaction.atomic
    def deactivate_tenant(tenant, deactivated_by):
        """
        Deactivate tenant.

        Args:
            tenant: Tenant object
            deactivated_by: User deactivating the tenant
        """
        tenant.is_active = False
        tenant.save()

        # Deactivate all memberships
        tenant.memberships.update(
            status='deactivated',
            updated_at=timezone.now()
        )

    @staticmethod
    @transaction.atomic
    def update_tenant_settings(tenant, **settings):
        """
        Update tenant settings.

        Args:
            tenant: Tenant object
            **settings: Settings to update
        """
        for key, value in settings.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)

        tenant.save()

    @staticmethod
    def get_tenant_by_id(tenant_id):
        """
        Get tenant by ID.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Tenant object or None
        """
        try:
            return Tenant.objects.get(guid=tenant_id, is_active=True)
        except Tenant.DoesNotExist:
            return None
