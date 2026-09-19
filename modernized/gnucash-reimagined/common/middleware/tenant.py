"""
Centralized tenant context for RLS.

This is the single authoritative tenant-context implementation for the whole
modular monolith. Bounded-context apps must import from here rather than
reimplementing tenant context locally.

Context is pushed into the PostgreSQL session as a custom GUC, so that RLS
policies can read it via ``current_setting``. ``SET LOCAL`` / ``set_config(...,
true)`` makes the value transaction-scoped: it clears automatically on
COMMIT or ROLLBACK and cannot leak between requests that share a pool slot.

Three entry points, for the three call sites:

* ``TenantContextMiddleware`` - HTTP requests, extracts the tenant from the
  request and sets context for the duration of the request.
* ``TenantContext``            - application code holding model instances,
  e.g. ``with TenantContext(tenant, user):``
* ``TenantContextManager``     - background tasks, which have only ids.

Read-back helpers ``get_current_tenant_id`` / ``get_current_user_id`` return
what the database session currently holds.

NOTE: SET LOCAL only survives inside an open transaction. Under Django's
default autocommit, a statement issued outside an explicit transaction is
committed immediately and the setting is discarded. Callers setting context
for a unit of work must therefore be inside ``transaction.atomic()``.
"""

from contextlib import contextmanager

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

# Session variable names read by the RLS policies. These names are part of the
# database contract - common/rls/, and docker/init-db.sql's get_current_tenant_id()
# both read them - so they are not configurable.
TENANT_CONTEXT_VARIABLE = "app.current_tenant_id"
USER_CONTEXT_VARIABLE = "app.current_user_id"
ENTITY_CONTEXT_VARIABLE = "app.current_entity_id"


def _rls_enabled() -> bool:
    """Whether RLS context propagation is active in this environment."""
    return bool(getattr(settings, "RLS_ENABLED", False))


def _set_local(variable: str, value) -> None:
    """Set one transaction-local session variable."""
    with connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL {variable} = %s", [str(value)])


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
        if not _rls_enabled():
            # RLS disabled (e.g., in development/testing)
            return

        # Use SET LOCAL for transaction-local context
        # This automatically clears on COMMIT/ROLLBACK
        try:
            _set_local(TENANT_CONTEXT_VARIABLE, tenant_id)

            # Also set user_id if authenticated
            if hasattr(request, "user") and request.user.is_authenticated:
                _set_local(USER_CONTEXT_VARIABLE, request.user.id)

            # Set legal_entity_id if available (for entity-scoped queries)
            if hasattr(request, "legal_entity_id") and request.legal_entity_id:
                _set_local(ENTITY_CONTEXT_VARIABLE, request.legal_entity_id)
        except Exception as e:
            # Log error but don't fail the request
            # RLS policies will deny access if context is missing
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to set tenant context: {e}")


class TenantContext:
    """
    Context manager for establishing tenant context from model instances.

    Usage:
        with TenantContext(tenant, user):
            # All queries in this block will have tenant context set
            pass

    Accepts model instances rather than ids so callers do not have to reach
    into ``.guid`` themselves; ``Tenant`` and ``LegalEntity`` use a UUID
    primary key named ``guid``.
    """

    def __init__(self, tenant, user=None, entity=None):
        """
        Initialize tenant context.

        Args:
            tenant: Tenant instance (or a raw tenant id)
            user: Optional User instance (or a raw user id)
            entity: Optional LegalEntity instance (or a raw entity id)
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
        # Context is automatically cleared when the transaction ends,
        # because the variables were set with SET LOCAL.
        return False

    def _set_context(self) -> None:
        """Set tenant context in the PostgreSQL session."""
        if not _rls_enabled():
            return

        _set_local(TENANT_CONTEXT_VARIABLE, _as_id(self.tenant))

        if self.user is not None:
            _set_local(USER_CONTEXT_VARIABLE, _as_id(self.user))

        if self.entity is not None:
            _set_local(ENTITY_CONTEXT_VARIABLE, _as_id(self.entity))


@contextmanager
def tenant_context(tenant, user=None, entity=None):
    """
    Function-style tenant context, for callers that prefer it.

    Usage:
        with tenant_context(tenant, user):
            ...
    """
    with TenantContext(tenant, user, entity):
        yield


class TenantContextManager:
    """
    Context manager for setting tenant context from raw ids.

    Intended for background tasks (Celery, management commands), which hold
    ids rather than loaded model instances.

    Usage:
        with TenantContextManager(tenant_id):
            # All queries in this block will be tenant-scoped
            Account.objects.all()
    """

    def __init__(self, tenant_id, user_id=None, entity_id=None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.entity_id = entity_id

    def __enter__(self):
        """Set tenant context when entering the context."""
        if not _rls_enabled():
            return self

        _set_local(TENANT_CONTEXT_VARIABLE, self.tenant_id)
        if self.user_id:
            _set_local(USER_CONTEXT_VARIABLE, self.user_id)
        if self.entity_id:
            _set_local(ENTITY_CONTEXT_VARIABLE, self.entity_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clear tenant context when exiting the context."""
        # SET LOCAL automatically clears on transaction end
        # No explicit cleanup needed
        return False


def _as_id(value):
    """Return the UUID/id of a model instance, or the value unchanged."""
    return getattr(value, "guid", getattr(value, "pk", value))


def get_current_tenant_id():
    """
    Get the tenant id currently set on the PostgreSQL session.

    Returns:
        Tenant UUID as a string, or None if no context is set.
    """
    return _current_setting(TENANT_CONTEXT_VARIABLE)


def get_current_user_id():
    """
    Get the user id currently set on the PostgreSQL session.

    Returns:
        User id as a string, or None if no context is set.
    """
    return _current_setting(USER_CONTEXT_VARIABLE)


def get_current_entity_id():
    """
    Get the legal entity id currently set on the PostgreSQL session.

    Returns:
        Entity UUID as a string, or None if no context is set.
    """
    return _current_setting(ENTITY_CONTEXT_VARIABLE)


def _current_setting(variable: str):
    """Read a session variable, returning None when it is unset."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting(%s, true)", [variable])
        row = cursor.fetchone()
    if not row or row[0] in (None, ""):
        return None
    return row[0]


__all__ = [
    "TENANT_CONTEXT_VARIABLE",
    "USER_CONTEXT_VARIABLE",
    "ENTITY_CONTEXT_VARIABLE",
    "TenantContext",
    "TenantContextManager",
    "TenantContextMiddleware",
    "get_current_entity_id",
    "get_current_tenant_id",
    "get_current_user_id",
    "tenant_context",
]
