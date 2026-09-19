"""
Tenant context middleware for RLS.

This middleware extracts the tenant context from the request and sets it
in the database session for RLS policy evaluation.

Uses PostgreSQL SET LOCAL for transaction-local context that automatically
clears on COMMIT/ROLLBACK.
"""

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin


class TenantContextMiddleware(MiddlewareMixin):
    """
    Middleware that extracts tenant context and sets it for RLS.

    Tenant context is extracted from:
    1. HTTP header (X-Tenant-ID) for API requests
    2. Session for web requests
    3. JWT token claims (if using JWT authentication)

    The context is set using PostgreSQL SET LOCAL, which is transaction-local
    and automatically clears on COMMIT/ROLLBACK.
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """Extract tenant context from request and set in database session."""
        tenant_id = self._extract_tenant_id(request)

        if tenant_id:
            self._set_tenant_context(tenant_id, request)
            request.tenant_id = tenant_id
        else:
            # No tenant context - will be handled by RLS policies
            request.tenant_id = None

        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Clean up tenant context after request."""
        # SET LOCAL automatically clears on transaction end, so no explicit cleanup needed
        # But we clear the request attribute for safety
        if hasattr(request, "tenant_id"):
            delattr(request, "tenant_id")
        return response

    def _extract_tenant_id(self, request: HttpRequest) -> str | None:
        """Extract tenant ID from request using multiple strategies."""
        # Strategy 1: HTTP header (API requests)
        tenant_header = getattr(settings, "TENANT_HEADER", "HTTP_X_TENANT_ID")
        tenant_id = request.META.get(tenant_header)
        if tenant_id:
            return tenant_id

        # Strategy 2: Session (web requests)
        session_key = getattr(settings, "TENANT_SESSION_KEY", "tenant_id")
        if hasattr(request, "session") and session_key in request.session:
            return request.session[session_key]

        # Strategy 3: JWT token claims (if using JWT authentication)
        if hasattr(request, "auth") and hasattr(request.auth, "get"):
            return request.auth.get("tenant_id")

        return None

    def _set_tenant_context(self, tenant_id: str, request: HttpRequest) -> None:
        """Set tenant context in PostgreSQL session using SET LOCAL."""
        if not getattr(settings, "RLS_ENABLED", False):
            # RLS disabled (e.g., in development/testing)
            return

        # Use SET LOCAL for transaction-local context
        # This automatically clears on COMMIT/ROLLBACK
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_tenant_id = %s", [tenant_id])

                # Also set user_id if authenticated
                if hasattr(request, "user") and request.user.is_authenticated:
                    cursor.execute("SET LOCAL app.current_user_id = %s", [request.user.id])

                # Set legal_entity_id if available (for entity-scoped queries)
                if hasattr(request, "legal_entity_id") and request.legal_entity_id:
                    cursor.execute("SET LOCAL app.current_entity_id = %s", [request.legal_entity_id])
        except Exception as e:
            # Log error but don't fail the request
            # RLS policies will deny access if context is missing
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to set tenant context: {e}")


class TenantContextManager:
    """
    Context manager for setting tenant context in background tasks.

    Usage:
        with TenantContextManager(tenant_id):
            # All queries in this block will be tenant-scoped
            Account.objects.all()
    """

    def __init__(self, tenant_id: str, user_id: int | None = None, entity_id: int | None = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.entity_id = entity_id

    def __enter__(self):
        """Set tenant context when entering the context."""
        if not getattr(settings, "RLS_ENABLED", False):
            return self

        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL app.current_tenant_id = %s", [self.tenant_id])
            if self.user_id:
                cursor.execute("SET LOCAL app.current_user_id = %s", [self.user_id])
            if self.entity_id:
                cursor.execute("SET LOCAL app.current_entity_id = %s", [self.entity_id])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clear tenant context when exiting the context."""
        # SET LOCAL automatically clears on transaction end
        # No explicit cleanup needed
        pass
