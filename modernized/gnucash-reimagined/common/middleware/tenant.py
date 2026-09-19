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

* ``TenantContextMiddleware`` - HTTP requests. Resolves the requested tenant,
  puts it to the authorization decision, and only then establishes context for
  the duration of the request. The only entry point that authorises.
* ``TenantContext``            - application code holding model instances,
  e.g. ``with TenantContext(tenant, user):``
* ``TenantContextManager``     - background tasks, which have only ids.

The last two establish context for a tenant the caller has already decided on
by other means. They perform no authorization check of their own, and must not
be reached from request handling with a caller-supplied tenant.

Read-back helpers ``get_current_tenant_id`` / ``get_current_user_id`` return
what the database session currently holds.

NOTE: SET LOCAL only survives inside an open transaction. Under Django's
default autocommit, a statement issued outside an explicit transaction is
committed immediately and the setting is discarded. Callers setting context
for a unit of work must therefore be inside ``transaction.atomic()``.
``TenantContextMiddleware`` opens that transaction itself - see below.

Establishing context is not the same as authorising it
------------------------------------------------------
Two different questions, answered in two different places, and conflating them
is how a tenant isolation boundary turns into decoration:

* *Which tenant may this caller assume?* -
  ``AuthorizationService.can_access_tenant()``. Business authorization, backed
  by memberships and advisor grants.
* *What does the database do with whatever tenant is in context?* - RLS. It
  confines the session to that one tenant and nothing more.

RLS cannot answer the first question. A session whose context is set to tenant
B reads tenant B's data perfectly happily; the policies are doing their job.
So the HTTP path must run the authorization decision *before* the context is
established, and refuse the request if it fails. Only
``TenantContextMiddleware`` does that. ``TenantContext`` and
``TenantContextManager`` deliberately do not: they are the internal entry
points for code that has already established a tenant by business means, and
``TenantScopedTask`` is the trusted background equivalent.
"""

from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.http import HttpRequest, HttpResponse
from django.utils.module_loading import import_module

# Session variable names read by the RLS policies. These names are part of the
# database contract - common/rls/, and docker/init-db.sql's get_current_tenant_id()
# both read them - so they are not configurable.
TENANT_CONTEXT_VARIABLE = "app.current_tenant_id"
USER_CONTEXT_VARIABLE = "app.current_user_id"
ENTITY_CONTEXT_VARIABLE = "app.current_entity_id"


#: The one authoritative answer to "may this user assume this tenant?".
#: Configurable so `common` does not have to import a bounded context, and so
#: tests can substitute a decision without standing up the whole identity app -
#: but defaulted to the real service, because a security decision that silently
#: resolves to "no authorizer configured, allow" would be worse than useless.
DEFAULT_TENANT_AUTHORIZER = (
    "apps.identity.services.authorization.AuthorizationService.can_access_tenant"
)


def _rls_enabled() -> bool:
    """Whether RLS context propagation is active in this environment."""
    return bool(getattr(settings, "RLS_ENABLED", False))


def _tenant_authorizer():
    """Resolve the callable that decides tenant access.

    ``django.utils.module_loading.import_string`` cannot resolve a path whose
    attribute half is itself dotted - it splits at the last dot and tries to
    import ``...authorization.AuthorizationService`` as a module. The setting
    names a *method on a class*, so the split is walked from the right until a
    real module is found and the remaining attributes are fetched off it.
    """
    path = getattr(settings, "RLS_TENANT_AUTHORIZER", DEFAULT_TENANT_AUTHORIZER)
    parts = path.split(".")
    for split in range(len(parts) - 1, 0, -1):
        try:
            resolved = import_module(".".join(parts[:split]))
        except ImportError:
            continue
        for attribute in parts[split:]:
            resolved = getattr(resolved, attribute)
        return resolved

    raise ImportError(
        f"RLS_TENANT_AUTHORIZER={path!r} could not be resolved to a callable. "
        "Refusing to run without an authorization decision."
    )


def _set_local(variable: str, value) -> None:
    """Set one transaction-local session variable."""
    with connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL {variable} = %s", [str(value)])


class TenantContextMiddleware:
    """
    Resolve, authorise and establish tenant context for an HTTP request.

    Written as a new-style middleware rather than a ``MiddlewareMixin``
    subclass because it has to own a transaction, and ``process_request``
    cannot: Django runs ``process_request`` before the view, and under the
    default autocommit each statement commits on its own, so a ``SET LOCAL``
    issued there is discarded before the view runs a single query. That is a
    silent no-op - the request succeeds, the context is gone, and every policy
    sees ``NULL``. Verified directly against PostgreSQL::

        SET LOCAL app.current_tenant_id = 'abc';
        WARNING:  SET LOCAL can only be used in transaction blocks

    Wrapping ``get_response`` in ``transaction.atomic()`` is what makes the
    setting outlive the statement that made it. The cost is real and worth
    stating: every request now holds a transaction open for its whole
    duration, and a ``StreamingHttpResponse`` outlives the block that would
    have carried the context. There is no way to have transaction-local RLS
    context without a transaction spanning the work that uses it.

    The order below is the whole point of this class:

        1. authenticated user      - trusted, from the session
        2. requested tenant        - *untrusted*, straight from the client
        3. ``can_access_tenant()`` - the authorization decision
        4. establish context       - only if step 3 said yes
        5. run the view

    Step 4 is the only place in the request path that establishes tenant
    context, and it is unreachable without step 3. If the decision machinery
    is ever broken or forgotten, the request runs with no tenant context and
    RLS returns zero rows - an outage, not a leak.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        with transaction.atomic():
            self._establish_context(request)
            return self.get_response(request)

    # -- context establishment ----------------------------------------------

    def _establish_context(self, request: HttpRequest) -> None:
        request.tenant_id = None

        if _rls_enabled():
            # The user is set before the tenant because the authorizer queries
            # are policed by the pre-context read set, which keys on
            # `app.current_user_id`. It comes from the authenticated session,
            # not from the request body, so it is not caller-chosen.
            self._set_user_context(request)

        tenant_id = self._extract_tenant_id(request)
        if not tenant_id:
            # No tenant asked for. Endpoints that legitimately run without one
            # (login, register, /me/) work here; tenant-scoped data does not,
            # because with no context every policy denies.
            return

        tenant = self._resolve_authorized_tenant(request, tenant_id)
        if tenant is None:
            raise PermissionDenied(
                "You do not have access to the requested tenant."
            )

        request.tenant_id = tenant_id
        if _rls_enabled():
            _set_local(TENANT_CONTEXT_VARIABLE, tenant_id)
            entity_id = getattr(request, "legal_entity_id", None)
            if entity_id:
                _set_local(ENTITY_CONTEXT_VARIABLE, entity_id)

    def _resolve_authorized_tenant(self, request: HttpRequest, tenant_id: str):
        """Return the tenant if the caller may assume it, else ``None``.

        A caller-supplied tenant id is a *request*, not a grant. It is looked
        up and then put to the one authoritative decision, which covers both
        routes in: direct membership, and an active advisor access grant.
        Anything else - an unauthenticated caller, an unknown tenant, a tenant
        the caller merely knows the id of - is refused here, before any context
        is established.
        """
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return None

        authorize = _tenant_authorizer()

        # Imported here rather than at module scope so that `common` does not
        # hard-depend on a bounded context at import time.
        from apps.identity.models import Tenant

        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except (Tenant.DoesNotExist, ValidationError, ValueError, TypeError):
            # A header value that is not a uuid reaches the UUIDField lookup
            # and raises django.core.exceptions.ValidationError from
            # get_prep_value - which is not a ValueError subclass despite the
            # name. A malformed tenant id is a denied request, not a 500.
            return None

        return tenant if authorize(user, tenant) else None

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

    def _set_user_context(self, request: HttpRequest) -> None:
        """Put the authenticated user's id in the session, for RLS to read."""
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return
        _set_local(USER_CONTEXT_VARIABLE, user.pk)


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
    "DEFAULT_TENANT_AUTHORIZER",
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
