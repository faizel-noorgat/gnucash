"""Middleware for the reporting-analytics bounded context.

The single cross-cutting concern here is tenant context propagation. Every
report query must be scoped to a single tenant — we accomplish this by
setting a PostgreSQL session variable at the start of each request, and
relying on Row Level Security policies in the Accounting Engine's tables to
filter rows. Defense-in-depth: the ORM querysets used by this context also
apply an explicit `.filter(tenant_id=...)` clause; the RLS variable is the
backstop in case a query is ever written without the filter.

See ADR-008 (Multi-Tenancy — Shared-Schema with RLS).
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Iterator

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

_local = threading.local()


def get_current_tenant_id() -> str | None:
    """Return the tenant id active on the current thread, if any."""
    return getattr(_local, "tenant_id", None)


def set_current_tenant_id(tenant_id: str | None) -> None:
    """Set the tenant id active on the current thread."""
    _local.tenant_id = tenant_id


@contextmanager
def tenant_scope(tenant_id: str) -> Iterator[None]:
    """Bind ``tenant_id`` as the active tenant for the duration of the block.

    The context manager always clears the thread-local on exit, even if the
    block raises. It also issues ``SET LOCAL`` against the current database
    connection, so RLS policies see the correct ``app.current_tenant``.
    """
    previous = get_current_tenant_id()
    set_current_tenant_id(tenant_id)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_tenant', %s, TRUE)",
                [str(tenant_id)],
            )
        yield
    finally:
        set_current_tenant_id(previous)


class TenantContextMiddleware(MiddlewareMixin):
    """Establish the tenant context for every inbound request.

    The tenant id is read from the request (set by an upstream auth
    middleware / JWT decoder). If no tenant is resolvable, the request is
    rejected — fail closed, never fail open (ADR-008 safeguard #4).
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        tenant_id = self._resolve_tenant(request)
        if tenant_id is None:
            from rest_framework.response import Response
            from rest_framework import status

            logger.warning(
                "request rejected: no tenant context",
                extra={"path": request.path},
            )
            return Response(
                {"detail": "Tenant context is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        set_current_tenant_id(tenant_id)
        request.tenant_id = tenant_id  # type: ignore[attr-defined]

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_tenant', %s, TRUE)",
                    [str(tenant_id)],
                )
                cursor.execute(
                    "SELECT set_config('app.current_user', %s, TRUE)",
                    [str(getattr(request, "user_id", ""))],
                )
        except Exception:
            # If the DB is not available yet (e.g. during tests on sqlite),
            # swallow — the ORM filter is the primary defense.
            logger.debug("could not set RLS session variable", exc_info=True)

        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        # Clear the thread-local so a pooled worker cannot leak context.
        set_current_tenant_id(None)
        return response

    # ------------------------------------------------------------------
    # Tenant resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_tenant(request: HttpRequest) -> str | None:
        """Derive the tenant id from the request.

        Resolution order:

        1. ``request.auth_tenant_id`` — set by the auth layer after
           validating a JWT ``tenant`` claim.
        2. ``X-Tenant-Slug`` header — used by internal service calls.
        3. ``settings.DEFAULT_TENANT_SLUG`` — development fallback only.
        """
        explicit = getattr(request, "auth_tenant_id", None)
        if explicit:
            return str(explicit)

        header = request.META.get("HTTP_X_TENANT_SLUG")
        if header:
            return str(header)

        if settings.DEBUG:
            return settings.DEFAULT_TENANT_SLUG
        return None
