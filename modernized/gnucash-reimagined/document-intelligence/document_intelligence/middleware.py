"""Tenant context middleware.

Establishes the tenant context for each request using PostgreSQL session
variables. This is used by Row Level Security (RLS) policies to enforce
tenant isolation at the database layer (BR-DI-010).

Defense-in-depth: ORM default filters also enforce tenant scoping at the
application layer.
"""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from django.db import connection
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class TenantContextMiddleware:
    """Establishes tenant context for RLS enforcement.

    Extracts tenant_id from the request (e.g., subdomain, header, session)
    and sets PostgreSQL session variables that RLS policies reference.

    Uses transaction-local context (SET LOCAL) so that the context is
    automatically cleared on COMMIT/ROLLBACK.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Extract tenant_id from request
        # In production, this would come from:
        # - Subdomain (tenant.fva.sg)
        # - Header (X-Tenant-ID)
        # - Session (after login)
        tenant_id = self._extract_tenant_id(request)
        user_id = self._extract_user_id(request)
        legal_entity_id = self._extract_legal_entity_id(request)

        # Set session variables for RLS
        try:
            with connection.cursor() as cursor:
                if tenant_id:
                    cursor.execute(
                        "SELECT set_config('app.tenant_id', %s, TRUE)",
                        [str(tenant_id)],
                    )
                if user_id:
                    cursor.execute(
                        "SELECT set_config('app.user_id', %s, TRUE)",
                        [str(user_id)],
                    )
                if legal_entity_id:
                    cursor.execute(
                        "SELECT set_config('app.legal_entity_id', %s, TRUE)",
                        [str(legal_entity_id)],
                    )
        except Exception:
            logger.exception("Failed to set RLS context")
            # Fail closed: if we can't set context, reject the request
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden("Tenant context not established")

        response = self.get_response(request)
        return response

    def _extract_tenant_id(self, request: HttpRequest) -> uuid.UUID | None:
        """Extract tenant_id from request."""
        # Try header first
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            try:
                return uuid.UUID(tenant_header)
            except ValueError:
                pass

        # Try session
        tenant_id_str = request.session.get("tenant_id")
        if tenant_id_str:
            try:
                return uuid.UUID(tenant_id_str)
            except ValueError:
                pass

        return None

    def _extract_user_id(self, request: HttpRequest) -> uuid.UUID | None:
        """Extract user_id from authenticated request."""
        if hasattr(request, "user") and request.user.is_authenticated:
            # Assuming user.pk is UUID
            return request.user.pk
        return None

    def _extract_legal_entity_id(self, request: HttpRequest) -> uuid.UUID | None:
        """Extract legal_entity_id from request (optional)."""
        entity_header = request.headers.get("X-Legal-Entity-ID")
        if entity_header:
            try:
                return uuid.UUID(entity_header)
            except ValueError:
                pass
        return None
