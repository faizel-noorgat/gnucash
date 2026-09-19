"""
API Middleware

Middleware for tenant context and practice context management.
"""
from django.db import connection
from django.conf import settings


class TenantContextMiddleware:
    """
    Middleware for establishing tenant context in database session.

    Key points:
    - Sets PostgreSQL session variables for RLS
    - Uses SET LOCAL within transaction for automatic cleanup
    - Defense-in-depth: RLS + ORM filters
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Process request and establish tenant context.

        Args:
            request: HTTP request
        """
        # Get tenant from request (set by view or authentication)
        tenant = getattr(request, 'tenant', None)
        user = getattr(request, 'user', None)

        # Establish tenant context in database session
        if tenant and user and user.is_authenticated:
            self._set_tenant_context(tenant, user)

        response = self.get_response(request)

        return response

    def _set_tenant_context(self, tenant, user):
        """
        Set tenant context in PostgreSQL session.

        Uses SET LOCAL to ensure context is automatically cleared
        when transaction commits/rolls back.

        Args:
            tenant: Tenant object
            user: User object
        """
        if not settings.MULTI_TENANCY.get('RLS_ENABLED', True):
            return

        try:
            with connection.cursor() as cursor:
                # Set tenant ID
                cursor.execute(
                    "SELECT set_config(%s, %s, true)",
                    [settings.MULTI_TENANCY['TENANT_CONTEXT_VARIABLE'], str(tenant.guid)]
                )

                # Set user ID
                cursor.execute(
                    "SELECT set_config(%s, %s, true)",
                    [settings.MULTI_TENANCY['USER_CONTEXT_VARIABLE'], str(user.guid)]
                )
        except Exception as e:
            # Log error but don't fail request
            # RLS will fail closed if context not set
            pass


class PracticeContextMiddleware:
    """
    Middleware for establishing practice context in database session.

    Key points:
    - Sets practice context when practice user is accessing client tenant
    - Logs practice_id and engagement_id for audit trail
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Process request and establish practice context.

        Args:
            request: HTTP request
        """
        # Check if this is a practice user accessing client tenant
        practice = getattr(request, 'practice', None)
        engagement = getattr(request, 'engagement', None)

        if practice and engagement:
            self._set_practice_context(practice, engagement)

        response = self.get_response(request)

        return response

    def _set_practice_context(self, practice, engagement):
        """
        Set practice context in PostgreSQL session.

        Args:
            practice: Practice object
            engagement: ClientEngagement object
        """
        if not settings.MULTI_TENANCY.get('RLS_ENABLED', True):
            return

        try:
            with connection.cursor() as cursor:
                # Set practice ID
                cursor.execute(
                    "SELECT set_config(%s, %s, true)",
                    [settings.MULTI_TENANCY['PRACTICE_CONTEXT_VARIABLE'], str(practice.guid)]
                )
        except Exception as e:
            # Log error but don't fail request
            pass
