"""
Tenant Context Management

Utilities for managing tenant context in application code.
"""
from django.db import connection
from django.conf import settings
from contextlib import contextmanager
from ..domain.models import Tenant


class TenantContext:
    """
    Context manager for establishing tenant context.

    Usage:
        with TenantContext(tenant, user):
            # All queries in this block will have tenant context set
            pass
    """

    def __init__(self, tenant, user, entity=None):
        """
        Initialize tenant context.

        Args:
            tenant: Tenant object
            user: User object
            entity: Optional LegalEntity object
        """
        self.tenant = tenant
        self.user = user
        self.entity = entity

    def __enter__(self):
        """Enter tenant context."""
        self._set_context()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit tenant context."""
        # Context is automatically cleared when transaction ends
        # due to SET LOCAL usage
        pass

    def _set_context(self):
        """Set tenant context in PostgreSQL session."""
        if not settings.MULTI_TENANCY.get('RLS_ENABLED', True):
            return

        with connection.cursor() as cursor:
            # Set tenant ID
            cursor.execute(
                "SELECT set_config(%s, %s, true)",
                [settings.MULTI_TENANCY['TENANT_CONTEXT_VARIABLE'], str(self.tenant.guid)]
            )

            # Set user ID
            cursor.execute(
                "SELECT set_config(%s, %s, true)",
                [settings.MULTI_TENANCY['USER_CONTEXT_VARIABLE'], str(self.user.guid)]
            )

            # Set entity ID if provided
            if self.entity:
                cursor.execute(
                    "SELECT set_config(%s, %s, true)",
                    [settings.MULTI_TENANCY['ENTITY_CONTEXT_VARIABLE'], str(self.entity.guid)]
                )


@contextmanager
def tenant_context(tenant, user, entity=None):
    """
    Context manager for tenant context.

    Usage:
        with tenant_context(tenant, user):
            # All queries in this block will have tenant context set
            pass
    """
    with TenantContext(tenant, user, entity):
        yield


def get_current_tenant_id():
    """
    Get current tenant ID from PostgreSQL session.

    Returns:
        Tenant UUID string or None
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_setting(%s, true)",
            [settings.MULTI_TENANCY['TENANT_CONTEXT_VARIABLE']]
        )
        result = cursor.fetchone()
        return result[0] if result else None


def get_current_user_id():
    """
    Get current user ID from PostgreSQL session.

    Returns:
        User UUID string or None
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_setting(%s, true)",
            [settings.MULTI_TENANCY['USER_CONTEXT_VARIABLE']]
        )
        result = cursor.fetchone()
        return result[0] if result else None
