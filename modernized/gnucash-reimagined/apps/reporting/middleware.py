"""Tenant-context entry point for the Reporting & Analytics context.

This module is a **re-export shim and contains no tenancy implementation**.
The single authoritative tenant-context implementation for the modular
monolith lives in ``common.middleware.tenant`` (see ADR-008, Multi-Tenancy —
Shared-Schema with RLS). Anything defined here would be a second
implementation of a cross-cutting concern and would drift from the RLS
session-variable contract that ``common/rls/`` and ``docker/init-db.sql``
read.

It exists so that code and tests inside the reporting context can express
their tenancy dependency through the context's own namespace without
reaching past it:

    from apps.reporting.middleware import tenant_scope

    with tenant_scope(tenant_id):
        ...

``tenant_scope`` is an alias for
``common.middleware.tenant.TenantContextManager``, the raw-ids form of the
context manager. It is the direct equivalent of the standalone service's
``tenant_scope(tenant_id)`` helper — background tasks and report runners
hold tenant ids, not loaded ``Tenant`` instances — and it sets the same
``app.current_tenant_id`` session variable that RLS policies read.
"""

from __future__ import annotations

from common.middleware.tenant import (
    ENTITY_CONTEXT_VARIABLE,
    TENANT_CONTEXT_VARIABLE,
    USER_CONTEXT_VARIABLE,
    TenantContext,
    TenantContextManager,
    TenantContextMiddleware,
    get_current_entity_id,
    get_current_tenant_id,
    get_current_user_id,
    tenant_context,
)

# The id-based context manager is the reporting context's `tenant_scope`.
# Alias only — the behaviour lives in common.
tenant_scope = TenantContextManager

__all__ = [
    "ENTITY_CONTEXT_VARIABLE",
    "TENANT_CONTEXT_VARIABLE",
    "USER_CONTEXT_VARIABLE",
    "TenantContext",
    "TenantContextManager",
    "TenantContextMiddleware",
    "get_current_entity_id",
    "get_current_tenant_id",
    "get_current_user_id",
    "tenant_context",
    "tenant_scope",
]
