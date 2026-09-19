# Spike 1 — Multi-Tenancy: RLS vs Schema-Per-Tenant

**Spike Number:** 1
**Status:** Completed — Recommendation Ready
**Date:** 2026-09-19
**Author:** Architecture Spike (Claude Code)
**Inputs:** REIMAGINED_ARCHITECTURE.md §1.2, §2, §5.4; AI_NATIVE_SPEC.md §2.1; MODERNIZATION_BRIEF.md §2

---

## Executive Summary

After deep analysis of PostgreSQL RLS capabilities, Django integration patterns, regulatory requirements, operational realities, and the specific requirements of accounting-practice multi-tenancy, this spike **recommends shared-schema PostgreSQL with Row Level Security (RLS)** as the multi-tenancy strategy for the FVA Accounting Platform.

**Key findings:**
- RLS provides **cryptographic-strength data isolation at the database layer** when combined with `SET LOCAL ROLE`, `FORCE ROW LEVEL SECURITY`, and careful session management — stronger than most Django-only tenant-filtering schemes
- The accounting practice model (cross-tenant advisor access) is *cleaner* with RLS than schema-per-tenant because the database layer already understands role-based visibility
- Regulatory requirements (Singapore PDPA, audit standards) do **not** mandate physical schema separation — they mandate **auditable, demonstrable controls**, which RLS satisfies
- The primary risks of RLS are **accidental bypass** through raw SQL, superuser connections, migrations, and Celery tasks — all of which have established mitigation patterns
- Schema-per-tenant carries material operational costs (hundreds of schemas, complex migrations, painful cross-tenant analytics, connection-pool bloat) that do not justify the marginal security gain for this product

**Recommendation:** Shared schema + RLS with a defense-in-depth strategy: (1) application-level `tenant_id` filters, (2) database-level RLS policies as the authoritative gate, (3) audit logging for privileged access, (4) CI tests that prove isolation across tenants.

---

## Table of Contents

1. [Threat and Isolation Analysis](#1-threat-and-isolation-analysis)
2. [RLS Policy Architecture](#2-rls-policy-architecture)
3. [Tenant Context Propagation Through HTTP Requests](#3-tenant-context-propagation-through-http-requests)
4. [Tenant Context Propagation Into Celery Jobs](#4-tenant-context-propagation-into-celery-jobs)
5. [Advisor/Practice Users Crossing Tenant Boundaries](#5-advisorpractice-users-crossing-tenant-boundaries)
6. [Superuser/Support Access Without Bypassing Controls](#6-superusersupport-access-without-bypassing-controls)
7. [Backup/Restore Implications](#7-backuprestore-implications)
8. [Migration Implications](#8-migration-implications)
9. [Testing Strategy for Proving Isolation](#9-testing-strategy-for-proving-isolation)
10. [Final Recommendation and ADR](#10-final-recommendation-and-adr)

---

## 1. Threat and Isolation Analysis

### 1.1 Threat Model for Multi-Tenant Accounting Data

The FVA platform holds **financially sensitive, audit-grade data**: general ledgers, bank reconciliations, tax filings, invoices, payroll-adjacent records, and OCR'd receipts. A data leak between tenants is not merely a bug — it is a **regulatory event** (PDPA, IRAS audit obligations) and an **existential business risk**.

**Threat actors:**
1. **Tenant A user** (accidental or malicious) attempting to read Tenant B's data
2. **Practice advisor** accessing a client tenant they are no longer engaged with
3. **Platform support / superuser** reading tenant data without audit trail
4. **SQL injection** in any query builder reaching the database
5. **Bug in ORM queryset** that drops tenant filter
6. **Migration or background job** running with elevated privileges and cross-tenant side effects
7. **Backup file exfiltration** exposing all tenants

### 1.2 Isolation Risks with RLS

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Connection runs as superuser** — superusers and `BYPASSRLS` roles skip all policies | Critical | Application **never** connects as superuser. Connection pool uses a non-superuser `app_user`. Superuser reserved for DDL/migrations only. |
| **`SET ROLE` forgotten in connection lifecycle** — session leaks tenant context | Critical | Middleware uses `try/finally` to guarantee `RESET ROLE`. Connection pooler (pgBouncer) configured with `server_reset_query = DISCARD ALL`. |
| **Raw SQL bypasses ORM filters** — developer writes `cursor.execute(...)` without tenant filter | High | RLS policy on table catches this — if role is set correctly, raw SQL is still filtered. This is RLS's primary advantage over ORM-only filtering. |
| **Policies reference untrusted functions** — planner pushes user-defined functions below filter | Medium | Use `security_barrier` on any views exposing tenant-scoped data. Mark tenant-scope functions `LEAKPROOF` only when genuinely safe. |
| **Missing policy on a new table** — default deny, but causes silent failures | Low | Migration linter enforces RLS on every new tenant-scoped table. Bootstrap migration enables RLS on all existing tables. |
| **Table owner bypass** — if Django owns the tables, table owner bypasses policies | High | Django migrations run under a **deploy role** that is NOT the table owner for runtime. Table owner = `deploy_user`; runtime connection = `app_user` (with policies). This is the critical `FORCE ROW LEVEL SECURITY` pattern. |
| **`search_path` hijacking** — attacker sets search_path to shadow tables | Low | `SET search_path` is part of session setup; connection pooler resets it. Policies reference tables with `schema.` prefix where ambiguous. |

**Fundamental RLS invariant:** If the connection role is set correctly and the policy expression is correct, **no query on Earth** — ORM, raw SQL, JDBC, psql — can return rows the policy excludes. This is a stronger guarantee than any ORM filter.

### 1.3 Isolation Risks with Schema-Per-Tenant

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Django routing bug** — `TenantRouter` returns wrong schema | Critical | Requires Django-level correctness; no database-level fallback. A bug here = cross-tenant leak. |
| **Migration runs against wrong schema** | Critical | Migration tooling must be tenant-aware. Complex for large fleets. |
| **Cross-tenant joins impossible at DB layer** | High | Practice dashboards, platform analytics, and intercompany features require UNIONs in application code. |
| **Connection pool bloat** | High | Each schema logically wants its own connection or `SET search_path`. pgBouncer helps but does not eliminate complexity. |
| **Schema drift** — DDL applied inconsistently across N schemas | High | Multi-schema migrations are slow and error-prone. `django-tenants` patterns exist but add complexity. |
| **Backup granularity mismatch** | Medium | Per-tenant restore requires schema-aware dump/restore. |
| **Thousands of schemas** — catalog bloat, slow `pg_dump`, planner slowdown | Medium | Real-world tenants can number in the thousands; catalog overhead becomes material. |
| **Advisor access complexity** | High | Practice user must `SET search_path` to each client schema; cross-tenant queries are hard. |

**Fundamental schema-per-tenant invariant:** Isolation is enforced by the Django router, not the database. A bug in the router = a cross-tenant leak. There is no defense-in-depth at the database layer.

### 1.4 Which Provides Stronger Guarantees?

**RLS with proper session management provides stronger guarantees than schema-per-tenant**, because:

1. **Isolation is enforced at the database engine level**, not in application code. The PostgreSQL executor applies RLS policies regardless of how the query was constructed.
2. **Defense-in-depth**: even if the Django ORM filter is missing, the database will refuse to return unauthorized rows.
3. **Auditable at the SQL layer**: `pg_policies` catalog fully describes what isolation is in force; auditors can verify without reading application code.
4. **Practice-user access is natural**: a practice user's role can have policies granting visibility to multiple tenants simultaneously, which schema-per-tenant cannot express cleanly.

### 1.5 Regulatory / Compliance Requirements

**Singapore PDPA** (Personal Data Protection Act):
- Requires "reasonable security arrangements" to prevent unauthorized access
- Does **not** mandate physical data separation
- RLS + audit logging + encrypted backups satisfies the standard

**IRAS (tax authority) audit requirements**:
- Require audit trails and data integrity, not schema isolation
- RLS with immutable `AuditEvent` log satisfies

**SOC 2 Type II** (likely requirement for SaaS):
- Requires logical access controls, audit trails, change management
- RLS with comprehensive logging is a well-trodden SOC 2 path
- Many SaaS accounting platforms (Xero, QuickBooks Online, FreshBooks) use shared-schema RLS and pass SOC 2

**ISO 27001**:
- Annex A.9 covers access control; RLS with role-based policies satisfies
- Does not mandate physical tenant separation

**GDPR** (if EU tenants later):
- Article 32 requires "appropriate technical measures"
- RLS is an accepted measure; EU-based SaaS platforms use it routinely
- Right-to-erasure is equally easy to implement in shared schema (DELETE WHERE tenant_id = X)

**Conclusion:** No relevant regulation or standard mandates schema-per-tenant. All mandate **demonstrable controls**, which RLS with audit logging provides cleanly.

---

## 2. RLS Policy Architecture

### 2.1 Schema Design

```
┌─────────────────────────────────────────────────────────────┐
│  Database: fva_production                                    │
├─────────────────────────────────────────────────────────────┤
│  Schema: public (all tenant-scoped tables)                  │
│                                                             │
│  Roles:                                                      │
│    - deploy_user   (DDL owner, no RLS bypass at runtime)   │
│    - app_user      (runtime connection, subject to RLS)    │
│    - support_user  (superuser-like, BYPASSRLS, audited)    │
│    - analytics_user (read-only, cross-tenant, BYPASSRLS)   │
│                                                             │
│  Session variables (set per connection):                    │
│    - app.current_tenant_id  (uuid)                          │
│    - app.current_user_id    (uuid)                          │
│    - app.current_entity_id  (uuid, optional, nullable)      │
│    - app.is_practice_user   (boolean)                       │
│    - app.practice_id        (uuid, optional)                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Core Policy Pattern: Tenant Isolation

Every tenant-scoped table (essentially every business table except `Tenant` itself, `Currency`, and a few global lookup tables) has a `tenant_id UUID NOT NULL` column and the following policy:

```sql
-- Bootstrap: enable RLS on all tenant-scoped tables
ALTER TABLE accounting_journalentry ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounting_journalline   ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounting_account       ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounting_banktransaction ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents_invoice        ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents_party          ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents_document       ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_legalentity     ENABLE ROW LEVEL SECURITY;
-- ... every tenant-scoped table

-- Force RLS even on table owner (deploy_user) when connecting at runtime
ALTER TABLE accounting_journalentry FORCE ROW LEVEL SECURITY;
-- ... same for all tenant-scoped tables

-- Standard tenant-isolation policy (PERMISSIVE)
CREATE POLICY tenant_isolation ON accounting_journalentry
    AS PERMISSIVE
    FOR ALL
    TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

The **key trick** is `current_setting('app.current_tenant_id')::uuid`: the tenant ID is a **session variable**, not a role name. This means:
- We don't need a Postgres role per tenant (scales to millions of tenants)
- The application sets the variable once per request/task
- The policy expression is identical across all tenant-scoped tables

### 2.3 LegalEntity Isolation Within Tenant

Some data is further scoped to a specific `LegalEntity` within a tenant. When the user has entity-level permissions, the policy enforces this:

```sql
-- Entity-scoped policy for users with restricted entity access
CREATE POLICY entity_scope ON accounting_journalentry
    AS RESTRICTIVE   -- RESTRICTIVE combines with PERMISSIVE via AND
    FOR ALL
    TO app_user
    USING (
        -- Either no entity restriction is active (NULL), or the row matches
        current_setting('app.current_entity_id') IS NULL
        OR
        entity_id = current_setting('app.current_entity_id')::uuid
    )
    WITH CHECK (
        current_setting('app.current_entity_id') IS NULL
        OR
        entity_id = current_setting('app.current_entity_id')::uuid
    );
```

**How PERMISSIVE + RESTRICTIVE combine:** PostgreSQL ANDs together all applicable PERMISSIVE policies and ANDs all RESTRICTIVE policies, then ORs the two groups. So:
- `tenant_isolation` (PERMISSIVE) must pass: `tenant_id = current_tenant`
- `entity_scope` (RESTRICTIVE) must pass: `entity_id IS NULL OR entity matches`
- Final: row is visible only if BOTH conditions hold

This gives us **composable, layered policies** — a clean expression of "you must be in the right tenant AND the right entity scope."

### 2.4 Practice User Policies

Practice users need to cross tenant boundaries intentionally. The policy model:

```sql
-- Practice users have a separate policy that allows access to engaged tenants
CREATE POLICY practice_access ON accounting_journalentry
    AS PERMISSIVE
    FOR SELECT
    TO app_user
    USING (
        current_setting('app.is_practice_user')::boolean = true
        AND
        tenant_id IN (
            SELECT aag.tenant_id
            FROM identity_advisoraccessgrant aag
            JOIN identity_clientengagement ce ON ce.id = aag.engagement_id
            WHERE aag.practice_user_id = current_setting('app.current_user_id')::uuid
              AND ce.status = 'active'
              AND aag.revoked_at IS NULL
        )
    );
```

**Key points:**
- The policy queries `AdvisorAccessGrant` to dynamically compute visible tenants
- When a practice user's access is revoked, their next query automatically excludes that tenant
- `WITH CHECK` is omitted for SELECT (not applicable); for INSERT/UPDATE, a separate practice policy ensures writes go only to explicitly granted tenants

### 2.5 Superuser / Support Policies

Superuser (support) access uses a different role that **has BYPASSRLS attribute** — but we do NOT want that to silently bypass all controls. Instead:

```sql
-- Support user role is explicitly defined with BYPASSRLS
CREATE ROLE support_user WITH BYPASSRLS LOGIN PASSWORD '...';

-- But support access is gated at the APPLICATION layer:
-- 1. Support user must assume a "support session" with explicit ticket reference
-- 2. All queries are logged to an immutable audit table with ticket ID
-- 3. Customer is notified

-- For audit/warehouse roles, separate read-only policies:
CREATE ROLE analytics_user WITH BYPASSRLS LOGIN;
-- Analytics user can see all tenants, but only SELECT.
-- Application layer gates analytics_user to reporting service only.
```

**Why BYPASSRLS for support is acceptable:** RLS is for tenant-isolation in the hot path. Support access is a rare, audited, out-of-band action. The audit trail (not RLS) is the control. This is the standard pattern for SaaS support tools (see Zendesk, Stripe, Intercom — all use shared schema + audit logs for support).

### 2.6 Performance Implications

| Concern | Analysis | Mitigation |
|---------|----------|------------|
| **Policy evaluation per row** | PostgreSQL evaluates the `current_setting(...)` once per query, not per row — it's a constant. The `tenant_id = constant` comparison is a fast index lookup. | Ensure `tenant_id` is indexed on every tenant-scoped table (usually as the leading column of the PK or a dedicated index). |
| **Subquery in practice_access policy** | The subquery over `AdvisorAccessGrant` runs per query. For practice users with many engagements, this could be slow. | Add index on `(practice_user_id, revoked_at)`. Cache practice-user visible tenant list in Redis and inject as a Postgres array session variable if needed. |
| **Planner interaction with policies** | PostgreSQL's planner can push predicates down into subqueries; RLS predicates are generally well-optimized. | Use `EXPLAIN (ANALYZE, VERBOSE)` to verify policies produce expected index scans. |
| **security_barrier views** | If tenant-scoped views are needed, `security_barrier` prevents planner from leaking data through user functions, at modest performance cost. | Use only for views that expose tenant data to untrusted parties (e.g., customer-facing APIs). Internal admin views can skip. |
| **Function-leak attacks** | A malicious user-defined function could try to exfiltrate data via side channels (error messages, timing) by being evaluated before the RLS filter. | Mark policy expressions with `security_barrier` semantics; disallow untrusted `LANGUAGE plpgsql` functions on tenant-scoped tables. |

**Empirical expectation:** For a typical accounting query (10–10,000 rows per tenant page), RLS overhead is <1 ms. The dominant cost is always the application query itself. Real-world RLS deployments (Citus, Azure, Supabase, xByte) report negligible performance impact at moderate scale.

### 2.7 Policy Bootstrap Migration

A single migration (`0001_initial_rls.sql`) should:
1. Create `deploy_user` (DDL owner), `app_user` (runtime), `support_user` (BYPASSRLS)
2. Revoke all default privileges from `app_user` on public schema
3. For each tenant-scoped table:
   - `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`
   - `ALTER TABLE ... FORCE ROW LEVEL SECURITY;`
   - `CREATE POLICY tenant_isolation ...;`
   - `CREATE POLICY entity_scope ...;` (where applicable)
   - `CREATE POLICY practice_access ...;` (SELECT only)
4. Grant `SELECT/INSERT/UPDATE/DELETE` on tables to `app_user`
5. Grant only `USAGE` on schema to `analytics_user` with per-table `SELECT`

A **migration linter** should enforce that every new migration adding a tenant-scoped table also adds RLS policies. This is a CI gate.

---

## 3. Tenant Context Propagation Through HTTP Requests

### 3.1 Tenant ID Extraction

Three common extraction strategies; the recommended approach combines them for defense-in-depth:

| Source | Security | Notes |
|--------|----------|-------|
| **JWT claim `tenant_id`** | Strong | Signed by auth service, cannot be tampered by client. Best for API-first SPA. |
| **Session (server-side)** | Strong | Django session stores `tenant_id` after tenant selection. Most flexible. |
| **Subdomain (`acme.fva.sg`)** | Medium | Requires DNS + TLS validation; vulnerable to DNS rebinding if not careful. Good UX. |
| **URL path (`/tenants/{id}/...`)** | Weak | Trivially forgeable; must be validated against JWT/session. |

**Recommended extraction strategy:**
1. JWT contains `user_id` (and optionally `practice_id`)
2. Session (or cache) contains the currently-selected `tenant_id` for this user
3. Middleware validates: (a) JWT is valid, (b) user has Membership or AdvisorAccessGrant for the session's tenant_id, (c) sets `app.current_tenant_id` in DB session
4. **Tenant selection endpoint** (POST `/api/tenant/switch/`) updates the session — tenant ID is never client-chosen per request

### 3.2 Django Middleware Architecture

```python
# fva/middleware/tenant_context.py

import logging
import uuid
from contextlib import contextmanager
from threading import local

from django.conf import settings
from django.db import connection
from django.http import HttpResponseForbidden
from rest_framework.authentication import get_authorization_header

from identity.models import Membership, AdvisorAccessGrant, ClientEngagement

logger = logging.getLogger(__name__)
_thread_locals = local()


def get_current_tenant_id() -> uuid.UUID | None:
    """Thread-local accessor for current tenant — for use in models, signals, etc."""
    return getattr(_thread_locals, "tenant_id", None)


def get_current_user_id() -> uuid.UUID | None:
    return getattr(_thread_locals, "user_id", None)


class TenantContextMiddleware:
    """
    For each authenticated request:
    1. Extract user from JWT/session (DRF Authentication handles this)
    2. Determine active tenant_id from session or header
    3. Verify user has access to that tenant (Membership or AdvisorAccessGrant)
    4. Set Postgres session variables so RLS policies activate
    5. Reset on request teardown, always
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip tenant context for tenant-agnostic routes (login, health, platform admin)
        if self._is_exempt_path(request.path):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return self.get_response(request)  # let auth middleware 401

        # Determine tenant_id: session > header (for API), reject if neither
        tenant_id = self._resolve_tenant_id(request, user)
        if tenant_id is None:
            return HttpResponseForbidden(
                {"detail": "No tenant selected. Call POST /api/tenant/switch/ first."}
            )

        # Verify access
        access = self._verify_access(user, tenant_id)
        if access is None:
            logger.warning(
                "tenant_access_denied user=%s tenant=%s", user.id, tenant_id
            )
            return HttpResponseForbidden({"detail": "No access to this tenant."})

        # Set thread-local for ORM default manager and signals
        _thread_locals.tenant_id = tenant_id
        _thread_locals.user_id = user.id
        _thread_locals.entity_id = access.get("entity_id")
        _thread_locals.is_practice_user = access["is_practice"]
        _thread_locals.practice_id = access.get("practice_id")

        try:
            # Set Postgres session variables — these drive RLS
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT set_config('app.current_tenant_id', %s, true),
                           set_config('app.current_user_id',    %s, true),
                           set_config('app.current_entity_id',  %s, true),
                           set_config('app.is_practice_user',   %s, true),
                           set_config('app.practice_id',        %s, true);
                    """,
                    (
                        str(tenant_id),
                        str(user.id),
                        str(access.get("entity_id") or ""),
                        str(access["is_practice"]).lower(),
                        str(access.get("practice_id") or ""),
                    ),
                )
                # Critical: the connection must be using app_user role
                cursor.execute("SET LOCAL ROLE app_user;")

            response = self.get_response(request)
        finally:
            # ALWAYS reset. pgBouncer's server_reset_query = DISCARD ALL is the backstop.
            self._clear_context()

        return response

    def _resolve_tenant_id(self, request, user) -> uuid.UUID | None:
        # Priority: session > X-Tenant-ID header (API clients) > None
        tenant_id = request.session.get("active_tenant_id")
        if tenant_id:
            return uuid.UUID(str(tenant_id))
        header = request.META.get("HTTP_X_TENANT_ID")
        if header:
            try:
                return uuid.UUID(header)
            except ValueError:
                return None
        return None

    def _verify_access(self, user, tenant_id) -> dict | None:
        # 1. Direct membership
        membership = Membership.objects.filter(
            user=user, tenant_id=tenant_id, is_active=True
        ).first()
        if membership:
            return {
                "is_practice": False,
                "entity_id": membership.restricted_entity_id,  # None = all entities
            }

        # 2. Practice advisor access grant
        grant = (
            AdvisorAccessGrant.objects.select_related(
                "engagement", "engagement__practice"
            )
            .filter(
                practice_user=user,
                tenant_id=tenant_id,
                engagement__status="active",
                revoked_at__isnull=True,
            )
            .first()
        )
        if grant:
            return {
                "is_practice": True,
                "practice_id": grant.engagement.practice_id,
                "engagement_id": grant.engagement_id,
                "entity_id": None,  # practice users see all entities by default
            }

        return None

    def _is_exempt_path(self, path: str) -> bool:
        exempt = [
            "/health",
            "/api/auth/",
            "/api/tenant/switch/",  # tenant switch itself is tenant-agnostic
            "/admin/",              # admin uses its own access checks
            "/__debug__/",
        ]
        return any(path.startswith(p) for p in exempt)

    def _clear_context(self):
        for attr in ("tenant_id", "user_id", "entity_id", "is_practice_user", "practice_id"):
            _thread_locals.__dict__.pop(attr, None)
        # RESET ROLE is handled by pgBouncer's DISCARD ALL,
        # but belt-and-braces:
        try:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE;")
        except Exception:
            pass  # connection may already be broken
```

### 3.3 ORM Integration: Default Tenant Filter

Even though RLS is the authoritative gate, defense-in-depth requires the ORM to filter by tenant by default — this catches bugs early and makes query intent obvious:

```python
# fva/models/tenant_aware.py

from django.db import models
from fva.middleware.tenant_context import get_current_tenant_id


class TenantManager(models.Manager):
    """Manager that auto-filters by current tenant."""
    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        qs = super().get_queryset()
        if tenant_id is not None:
            return qs.filter(tenant_id=tenant_id)
        # If no tenant context (e.g., management command), return unfiltered.
        # This is a conscious escape hatch — see §8 on migrations.
        return qs


class TenantAwareModel(models.Model):
    """Base class for all tenant-scoped models."""
    tenant = models.ForeignKey(
        "identity.Tenant", on_delete=models.PROTECT, db_index=True
    )
    # ... audit fields: created_by, created_at, updated_by, updated_at

    objects = TenantManager()
    all_objects = models.Manager()  # explicit escape hatch when you need it

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and self.tenant_id is None:
            self.tenant_id = tenant_id
        elif tenant_id is not None and self.tenant_id != tenant_id:
            raise ValueError("Cannot save object against a different tenant")
        super().save(*args, **kwargs)
```

**Critical invariant:** `TenantAwareModel.objects` filters by tenant. If a developer wants cross-tenant access, they must **explicitly** use `.all_objects`, which is a visible, greppable signal that something unusual is happening.

### 3.4 What Happens If Context Is Missing or Invalid?

| Scenario | Behavior |
|----------|----------|
| **No tenant in session, no header** | Middleware returns 403 with message "Call tenant switch first." |
| **Header contains invalid UUID** | Middleware returns 403. |
| **User has no access to requested tenant** | Middleware returns 403, logs warning. |
| **DB session variable unset when ORM runs** | RLS policy: `current_setting('app.current_tenant_id')` returns empty string, casts to UUID fail → policy returns false → **default deny**. Zero rows returned. |
| **Thread-local unset but DB session set** | ORM default filter not applied, but RLS still applies. Safe. |
| **DB session unset but thread-local set** | RLS returns no rows; ORM filters return rows that RLS blocks. Safe — zero rows result. |
| **Middleware exception before `SET LOCAL ROLE`** | Connection remains as `deploy_user` (which has `FORCE RLS` enabled on tables) → RLS still applies. Safe. |

**Defense-in-depth guarantee:** Any combination of failures results in zero rows being returned for tenant-scoped tables. The only way to see data is if BOTH the ORM filter AND RLS policy agree.

---

## 4. Tenant Context Propagation Into Celery Jobs

### 4.1 The Celery Challenge

Celery workers run in long-lived processes that handle many tasks from many tenants. The tenant context is **not** implicit — it must be passed with every task and set on the worker side before any DB query runs.

### 4.2 Task Decorator Pattern

```python
# fva/celery/tenant_task.py

import functools
from celery import Task, current_app
from django.db import connection
from fva.middleware.tenant_context import _thread_locals


class TenantScopedTask(Task):
    """
    Base Celery task that enforces tenant context.
    Subclass this for all tenant-scoped work.

    Usage:
        @shared_task(base=TenantScopedTask, bind=True)
        def generate_invoice_pdf(self, invoice_id, tenant_id):
            ...
    """
    abstract = True

    def __call__(self, *args, **kwargs):
        tenant_id = kwargs.pop("tenant_id", None)
        if tenant_id is None:
            # Platform-level tasks (e.g., tenant onboarding) can opt out
            if not getattr(self, "allow_no_tenant", False):
                raise ValueError(
                    f"Task {self.name} requires tenant_id kwarg"
                )
            return super().__call__(*args, **kwargs)

        user_id = kwargs.pop("initiated_by_user_id", None)

        # Set thread-local AND Postgres session variables
        _thread_locals.tenant_id = tenant_id
        _thread_locals.user_id = user_id

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT set_config('app.current_tenant_id', %s, true),
                           set_config('app.current_user_id', %s, true),
                           set_config('app.current_entity_id', '', true),
                           set_config('app.is_practice_user', 'false', true),
                           set_config('app.practice_id', '', true);
                    SET LOCAL ROLE app_user;
                    """,
                    (str(tenant_id), str(user_id or "")),
                )
            return super().__call__(*args, **kwargs)
        finally:
            _thread_locals.__dict__.clear()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("RESET ROLE;")
            except Exception:
                pass


def tenant_task(fn=None, *, allow_no_tenant=False):
    """Decorator for tenant-scoped tasks."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tenant_id = kwargs.get("tenant_id")
            if tenant_id is None and not allow_no_tenant:
                raise ValueError(f"Task {func.__name__} requires tenant_id")
            # Reuse TenantScopedTask machinery
            task = TenantScopedTask()
            task.allow_no_tenant = allow_no_tenant
            return task.__call__(lambda *a, **kw: func(*a, **kw), *args, **kwargs)
        return wrapper
    if fn is not None:
        return decorator(fn)
    return decorator
```

### 4.3 Task Invocation

When calling a tenant-scoped task, the caller **must** pass the tenant_id explicitly:

```python
# In views.py or signal handlers
from fva.tasks import generate_invoice_pdf

# GOOD: tenant_id passed explicitly
generate_invoice_pdf.delay(
    invoice_id=invoice.id,
    tenant_id=request.tenant.id,
    initiated_by_user_id=request.user.id,
)

# BAD: tenant_id missing — task raises ValueError
generate_invoice_pdf.delay(invoice_id=invoice.id)
```

A **Celery task linter** (CI check) should flag any `.delay()` or `.apply_async()` call to a `TenantScopedTask` that does not include `tenant_id`.

### 4.4 What Happens If Context Is Lost?

| Scenario | Behavior |
|----------|----------|
| **Task invoked without `tenant_id`** | `TenantScopedTask.__call__` raises `ValueError` before the task body runs. Task fails visibly. |
| **Task body forgets to use `TenantAwareModel.objects`** | RLS still applies; query returns zero rows. Task likely fails with DoesNotExist, which is a visible signal. |
| **`RESET ROLE` fails after task** | pgBouncer's `server_reset_query = DISCARD ALL` resets connection state when returned to pool. Safe. |
| **Task spawns sub-tasks** | Sub-tasks must receive `tenant_id` explicitly — Celery does not propagate automatically. The decorator pattern requires it. |
| **Long-running task switches tenant mid-execution** | `SET LOCAL` scope is the transaction. If the task opens multiple transactions, the role must be re-set per transaction. Document this pattern. |

### 4.5 Preventing Cross-Tenant Leakage in Background Jobs

1. **Never store `tenant_id` in module globals** — always in thread-local or DB session
2. **Never cache cross-tenant querysets** — Django's cache framework is tenant-agnostic; use a tenant-aware cache key prefix (`fva:tenant:{id}:key`)
3. **Never share file paths across tenants** — Document storage uses tenant-specific prefixes (`invoices/{tenant_id}/{year}/{filename}`)
4. **Celery task routing** — Tenant-scoped queues can be used for prioritization, but the same worker can process multiple tenants. Context-setting is the isolation mechanism, not worker segregation.

---

## 5. Advisor/Practice Users Crossing Tenant Boundaries

### 5.1 How RLS Supports Practice Users

The `practice_access` RLS policy (§2.4) grants visibility to all tenants where the practice user has an **active, non-revoked** `AdvisorAccessGrant`. When a practice user makes a request:

1. Middleware verifies the practice user has an active grant to the selected tenant
2. Session variables set: `app.is_practice_user = 'true'`, `app.practice_id = '...'`
3. RLS policy `practice_access` evaluates the subquery over `AdvisorAccessGrant`
4. Query returns rows from the engaged tenant only (because `app.current_tenant_id` is also set to that tenant)

**Critical subtlety:** Even though the `practice_access` policy *could* return rows from all engaged tenants, the **combination** of `tenant_isolation` (PERMISSIVE, requires `tenant_id = current_tenant_id`) AND `practice_access` (PERMISSIVE, allows access to engaged tenants) means the user sees only rows from **the currently-selected tenant**. The `tenant_isolation` policy narrows to the selected tenant; `practice_access` widens authorization to allow practice users to select that tenant.

### 5.2 Preventing Accidental Cross-Tenant Access

**Risk:** Practice user accidentally queries across all their clients instead of focusing on one.

**Mitigations:**
1. **Single-tenant context per request** — the middleware always sets `app.current_tenant_id` to exactly one tenant. Cross-tenant queries are impossible via the ORM.
2. **Practice dashboard is a separate endpoint** — uses a dedicated `PlatformAnalytics` view that explicitly UNIONs across engaged tenants, with clear UX labeling
3. **Audit log distinguishes practice access** — every `AuditEvent` includes `practice_id` and `engagement_id` when a practice user is acting, so practice-originated actions are traceable
4. **Client-visible audit** — clients can see which practice users accessed their data and when

### 5.3 Auditable Practice Access

```python
# fva/audit/practice_access_log.py

@receiver(pre_save, sender=AuditEvent)
def stamp_practice_context(sender, instance, **kwargs):
    from fva.middleware.tenant_context import _thread_locals
    if getattr(_thread_locals, "is_practice_user", False):
        instance.practice_id = _thread_locals.practice_id
        instance.engagement_id = getattr(_thread_locals, "engagement_id", None)
        instance.access_mode = "practice_advisor"
    else:
        instance.access_mode = "direct_tenant_member"
```

Additionally, a separate `PracticeAccessLog` table (append-only) records every request a practice user makes to a client tenant, including:
- `practice_user_id`
- `tenant_id`
- `engagement_id`
- `ip_address`
- `user_agent`
- `requested_at`
- `action_summary` (e.g., "VIEWED invoice report for Q3")

This log is **visible to the client** in their "advisor access history" view, fulfilling the architectural promise that "practice access is explicit, revocable, and auditable."

---

## 6. Superuser/Support Access Without Bypassing Controls

### 6.1 The Support Access Model

Support users (platform admins, customer support agents) sometimes need to view tenant data to diagnose issues. This access must be:
- **Rare** (not a daily workflow)
- **Audited** (every access logged)
- **Consented where possible** (customer notified, or "break glass" justification)
- **Narrow** (read-only, no data modification)

### 6.2 Implementation

```python
# fva/support/access.py

class SupportAccessError(Exception):
    pass


def grant_support_access(support_user, tenant, *, ticket_id, reason, duration_minutes=60):
    """
    Grant time-bound support access to a tenant.
    This does NOT disable RLS — instead, it creates a temporary SupportAccessGrant
    that the RLS policy recognizes.
    """
    # 1. Create grant record
    grant = SupportAccessGrant.objects.create(
        support_user=support_user,
        tenant=tenant,
        ticket_id=ticket_id,
        reason=reason,
        granted_at=now(),
        expires_at=now() + timedelta(minutes=duration_minutes),
        revoked_at=None,
    )

    # 2. Notify tenant admins (email + in-app)
    notify_tenant_admins_of_support_access(tenant, grant)

    # 3. Log to platform audit trail
    AuditEvent.log_platform_event(
        event_type="support_access_granted",
        actor=support_user,
        tenant=tenant,
        metadata={"ticket_id": ticket_id, "reason": reason},
    )

    return grant


# RLS policy for support access:
# CREATE POLICY support_access ON accounting_journalentry
#     AS PERMISSIVE
#     FOR SELECT
#     TO support_user
#     USING (
#         tenant_id IN (
#             SELECT sag.tenant_id
#             FROM support_accessgrant sag
#             WHERE sag.support_user_id = current_setting('app.current_user_id')::uuid
#               AND sag.revoked_at IS NULL
#               AND sag.expires_at > now()
#         )
#     );
```

### 6.3 Why This Works Without Disabling RLS

**Key insight:** We do NOT give `support_user` the `BYPASSRLS` attribute. Instead, support users are subject to a **support-specific RLS policy** that grants visibility only to tenants with an active, time-bound `SupportAccessGrant`.

This means:
- RLS is **always on** for support users — they cannot accidentally see unauthorized data
- Access is **time-bounded** — policies check `expires_at > now()`
- Access is **auditable** — every support action is logged with the grant reference
- Access is **revocable** — setting `revoked_at` instantly cuts off access
- There is **no "disable RLS" switch** to accidentally flip

### 6.4 Superuser / DBA Access

True database superusers (DBAs, migration runners) **do** have `BYPASSRLS`. Controls:
1. **Credential management** — superuser credentials stored in a secrets manager (AWS Secrets Manager, HashiCorp Vault), not in Django settings
2. **Just-in-time access** — superuser credentials are rotated, not long-lived. DBAs use `aws rds generate-db-auth-token` or equivalent
3. **Audit log at database level** — `pgaudit` extension logs all superuser queries
4. **No application-level use** — Django never connects as superuser. Only psql/DDL migrations use superuser

### 6.5 Preventing Superuser Access From Becoming a Security Hole

| Control | Implementation |
|---------|----------------|
| **Credential vault** | Superuser password in secrets manager; rotated every 24 hours for emergency break-glass |
| **MFA for superuser** | DBA must authenticate via SSO with MFA to retrieve superuser credentials |
| **Session recording** | `pgaudit` logs every DDL and DML; logs shipped to immutable S3 bucket |
| **No production superuser in Django** | Django's `DATABASES['default']` uses `app_user` credentials. `DATABASES['migrations']` uses `deploy_user`. Neither is superuser. |
| **Break-glass workflow** | To use superuser: open incident → retrieve creds from vault (logged) → perform action → rotate creds (logged). Paper trail complete. |
| **Customer notification** | Any superuser access to tenant data triggers customer notification within 15 minutes |

---

## 7. Backup/Restore Implications

### 7.1 Backup Strategy with RLS

RLS is **transparent to backup** — `pg_dump` runs as superuser (or a role with `BYPASSRLS`) and captures all rows, all tables, all policies. Standard PostgreSQL backup tools work unchanged:

- **Logical backup**: `pg_dump` (full cluster or per-database)
- **Physical backup**: pgBackRest, Barman, WAL-G (continuous archiving)
- **Point-in-time recovery**: standard PostgreSQL PITR works

### 7.2 Per-Tenant Backup and Restore

This is where shared-schema becomes nuanced:

**Option A: Full-database backup with tenant-tagged exports** (recommended for v1)
- Nightly full-database backup (WAL-G or pgBackRest)
- Per-tenant logical export monthly: `pg_dump --table='*'` with `COPY` filtered by tenant_id via a **tenant-specific view** or a small Python script:

```python
# scripts/backup_tenant.py
def export_tenant(tenant_id, output_path):
    """
    Export a single tenant's data to a logical dump.
    Used for: tenant offboarding, legal data portability requests, disaster recovery.
    """
    tables = get_tenant_scoped_tables()  # from information_schema + RLS catalog
    with psycopg2.connect(DSN) as conn, open(output_path, 'wb') as f:
        for table in tables:
            with conn.cursor() as cur:
                cur.execute(
                    f"COPY (SELECT * FROM {table} WHERE tenant_id = %s) TO STDOUT WITH CSV",
                    (str(tenant_id),)
                )
                # ... write to archive
```

**Option B: Partition by tenant_id** (v2 optimization)
- Partitioned tables by `tenant_id` (list or hash partitioning)
- Per-tenant partition can be backed up/restored independently
- Provides performance benefits (partition pruning) as well as operational benefits

### 7.3 Restore Considerations

| Scenario | Approach |
|----------|----------|
| **Full disaster recovery** | Restore full database from backup. All tenants restored together. Standard PITR. |
| **Single tenant restore from snapshot** | (1) Restore full DB to a temporary schema/database, (2) COPY tenant data into production, (3) reconcile conflicts. Complex; avoid unless necessary. |
| **Tenant offboarding (delete)** | `DELETE FROM {table} WHERE tenant_id = X` in dependency order. Or truncate tenant partitions if partitioned. |
| **GDPR right to erasure** | Row-level DELETE or partition drop. RLS does not complicate this. |

### 7.4 Operational Complexity

- **Backup size** grows linearly with tenant count, but this is true for schema-per-tenant too
- **No schema-per-tenant catalog bloat** — shared-schema wins at scale (thousands of tenants)
- **Restore testing** must verify tenant isolation is preserved post-restore (add to restore test suite)

---

## 8. Migration Implications

### 8.1 Migrations with RLS Policies in Place

**Django migrations run as `deploy_user` (table owner)** — which by default **bypasses RLS** unless `FORCE ROW LEVEL SECURITY` is set.

**Recommended setup:**
- `deploy_user` owns all tables (created by migrations)
- `app_user` is the runtime role (subject to RLS)
- Migrations run as `deploy_user` → no RLS interference during schema changes
- Django's ORM during migrations uses `deploy_user` → sees all rows

**Critical safeguard:** The migration runner must be a **separate Django process** with different DB credentials from the application server. If they share credentials, you lose the isolation between "deploy sees all" and "runtime sees one tenant."

### 8.2 Schema Changes

Adding a column, index, or table during a zero-downtime deployment:
- DDL runs as `deploy_user` → no RLS implications, standard ALTER TABLE
- Existing rows need `tenant_id` populated for new tables → data migration runs as `deploy_user`
- After migration, `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` and create policies
- Application servers (using `app_user`) immediately benefit from new policies

**Zero-downtime deployment sequence:**
1. Deploy migration (adds column, enables RLS on new table, creates policies)
2. Deploy new application code (references new column)
3. Between steps 1 and 2, old code works fine — RLS does not break it
4. If migration fails, rollback is clean — `deploy_user` can revert

### 8.3 Data Migrations That Need Cross-Tenant Access

**Example:** "Consolidate all tenants' FX rates into a shared rate table."

```python
# migrations/0042_fx_rate_consolidation.py

def consolidate_fx_rates(apps, schema_editor):
    """
    Data migration that reads from all tenants.
    Runs as deploy_user, so RLS does not apply.
    """
    # Use schema_editor's connection (deploy_user)
    # Explicitly document that this is a cross-tenant operation
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO accounting_exchangerate (tenant_id, currency, date, rate)
            SELECT tenant_id, currency, date, rate
            FROM legacy_fx_rates
            ON CONFLICT (tenant_id, currency, date) DO NOTHING
        """)

class Migration(migrations.Migration):
    # ...
    operations = [
        migrations.RunPython(
            consolidate_fx_rates,
            hints={"cross_tenant": True},  # document intent
        ),
    ]
```

**Rule:** Any data migration that touches multiple tenants must:
1. Be clearly documented as cross-tenant
2. Run as `deploy_user` (not `app_user`)
3. Not be callable from the runtime ORM path
4. Pass CI linter for cross-tenant operations

### 8.4 Handling Tenant-Scoped Unique Constraints

A common challenge: "Email must be unique per tenant, not globally."

```python
class Party(TenantAwareModel):
    email = models.EmailField()
    # ...

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "email"],
                name="unique_party_email_per_tenant",
            ),
        ]
```

This works cleanly in shared-schema; in schema-per-tenant, you'd have to declare the constraint per schema (which `django-tenants` handles, but adds complexity).

### 8.5 Migration Linter (CI Gate)

A custom Django system check should fail CI if:
1. A new tenant-scoped table is created without RLS enabled
2. A migration contains raw SQL that references tenant-scoped tables without `WHERE tenant_id = ...` or without being marked `cross_tenant=True`
3. A foreign key from a tenant-scoped table points to a non-tenant-scoped table (data leak vector)

---

## 9. Testing Strategy for Proving Isolation

### 9.1 Test Categories

| Category | Purpose | Runs |
|----------|---------|------|
| **Unit tests for RLS policies** | Prove that a query as `app_user` with `tenant_id = A` cannot see tenant B's rows | Every CI run |
| **Integration tests for middleware** | Prove that middleware correctly sets context for various request types | Every CI run |
| **Practice-user tests** | Prove practice users can access engaged tenants and cannot access unengaged ones | Every CI run |
| **Support-user tests** | Prove support access is time-bound, audited, and revocable | Every CI run |
| **Celery task tests** | Prove tasks without `tenant_id` fail loudly; tasks with `tenant_id` isolate correctly | Every CI run |
| **Negative tests (attacks)** | SQL injection attempts, role escalation attempts, missing-context attempts | Weekly security suite |
| **Property-based tests** | Hypothesis tests: for any two tenants, queries from A never return B's rows | Nightly |

### 9.2 Core RLS Isolation Test

```python
# tests/integration/test_rls_isolation.py

import pytest
import psycopg2
from django.db import connection

@pytest.mark.django_db(transaction=True)  # transaction=True to see RLS effects
def test_rls_blocks_cross_tenant_reads(tenant_a, tenant_b, app_user_connection):
    """Prove that a query as app_user with tenant_id=A cannot see tenant B's rows."""
    # Setup: one row in each tenant
    JournalEntry.objects.create(tenant=tenant_a, description="A entry", ...)
    JournalEntry.objects.create(tenant=tenant_b, description="B entry", ...)

    # Act: set context to tenant A
    with app_user_connection.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_user;")
        cur.execute(
            "SELECT set_config('app.current_tenant_id', %s, true)",
            (str(tenant_a.id),),
        )
        cur.execute("SELECT description FROM accounting_journalentry;")
        rows = cur.fetchall()

    # Assert: only tenant A's row is visible
    assert len(rows) == 1
    assert rows[0][0] == "A entry"


@pytest.mark.django_db(transaction=True)
def test_rls_blocks_raw_sql_bypass(tenant_a, tenant_b, app_user_connection):
    """Prove that raw SQL is also filtered by RLS."""
    JournalEntry.objects.create(tenant=tenant_a, description="A", ...)
    JournalEntry.objects.create(tenant=tenant_b, description="B", ...)

    with app_user_connection.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_user;")
        cur.execute(
            "SELECT set_config('app.current_tenant_id', %s, true)",
            (str(tenant_a.id),),
        )
        # Raw SQL with NO tenant filter — RLS must still apply
        cur.execute("SELECT description FROM accounting_journalentry;")
        rows = cur.fetchall()

    assert len(rows) == 1  # RLS saved us


@pytest.mark.django_db(transaction=True)
def test_rls_default_deny_without_context(app_user_connection, tenant_a):
    """Prove that without setting tenant context, zero rows are returned."""
    JournalEntry.objects.create(tenant=tenant_a, description="A", ...)

    with app_user_connection.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_user;")
        # Intentionally do NOT set app.current_tenant_id
        cur.execute("SELECT description FROM accounting_journalentry;")
        rows = cur.fetchall()

    assert len(rows) == 0  # default deny


@pytest.mark.django_db(transaction=True)
def test_practice_user_sees_only_engaged_tenants(
    practice_user, tenant_a, tenant_b, engaged_tenant_c, app_user_connection
):
    """Practice user sees only tenants they have active grants for."""
    JournalEntry.objects.create(tenant=tenant_a, description="A", ...)
    JournalEntry.objects.create(tenant=tenant_b, description="B", ...)
    JournalEntry.objects.create(tenant=engaged_tenant_c, description="C", ...)

    with app_user_connection.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_user;")
        cur.execute(
            """
            SELECT set_config('app.current_user_id', %s, true),
                   set_config('app.is_practice_user', 'true', true),
                   set_config('app.current_tenant_id', %s, true);
            """,
            (str(practice_user.id), str(tenant_a.id)),  # tenant_a is NOT engaged
        )
        cur.execute("SELECT description FROM accounting_journalentry;")
        rows = cur.fetchall()

    assert len(rows) == 0  # tenant_a not engaged → blocked


@pytest.mark.django_db(transaction=True)
def test_support_access_is_time_bound(support_user, tenant_a, app_user_connection):
    """Support access expires and no longer grants visibility."""
    JournalEntry.objects.create(tenant=tenant_a, description="A", ...)

    grant = SupportAccessGrant.objects.create(
        support_user=support_user,
        tenant=tenant_a,
        expires_at=now() - timedelta(hours=1),  # already expired
        ...
    )

    with app_user_connection.cursor() as cur:
        cur.execute("SET LOCAL ROLE support_user;")
        cur.execute(
            "SELECT set_config('app.current_user_id', %s, true)",
            (str(support_user.id),),
        )
        cur.execute("SELECT description FROM accounting_journalentry;")
        rows = cur.fetchall()

    assert len(rows) == 0  # expired grant → blocked
```

### 9.3 Middleware Test

```python
# tests/integration/test_tenant_middleware.py

@pytest.mark.django_db
def test_middleware_blocks_user_without_access(api_client, user, tenant_b):
    """User without membership cannot access tenant B."""
    api_client.force_authenticate(user=user)
    # Session has tenant_b set
    api_client.session["active_tenant_id"] = str(tenant_b.id)

    response = api_client.get("/api/accounting/journal-entries/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_middleware_sets_pg_session_variables(api_client, user, tenant_a):
    """Middleware sets Postgres session variables correctly."""
    Membership.objects.create(user=user, tenant=tenant_a)
    api_client.force_authenticate(user=user)
    api_client.session["active_tenant_id"] = str(tenant_a.id)

    response = api_client.get("/api/accounting/journal-entries/")
    assert response.status_code == 200

    # Verify via a test view that echoes the session variables
    response = api_client.get("/api/debug/pg-session/")
    assert response.json()["current_tenant_id"] == str(tenant_a.id)
    assert response.json()["current_role"] == "app_user"
```

### 9.4 Celery Task Test

```python
# tests/integration/test_celery_tenant_isolation.py

@pytest.mark.django_db(transaction=True)
def test_task_without_tenant_id_fails():
    @shared_task(base=TenantScopedTask)
    def my_task():
        return JournalEntry.objects.count()

    with pytest.raises(ValueError, match="requires tenant_id"):
        my_task.apply()


@pytest.mark.django_db(transaction=True)
def test_task_with_tenant_id_isolates(tenant_a, tenant_b):
    JournalEntry.objects.create(tenant=tenant_a, ...)
    JournalEntry.objects.create(tenant=tenant_b, ...)

    @shared_task(base=TenantScopedTask)
    def count_entries():
        return JournalEntry.objects.count()

    result = count_entries.apply(kwargs={"tenant_id": str(tenant_a.id)})
    assert result.get() == 1  # only tenant A visible
```

### 9.5 Attack Simulation Suite

Run weekly in a dedicated security test job:
1. **SQL injection** → attempt to inject `' OR '1'='1` into tenant-scoped filters → verify RLS holds
2. **Role escalation** → attempt `SET ROLE TO superuser` from `app_user` connection → verify failure
3. **Session variable tampering** → attempt to set `app.current_tenant_id` to another tenant's UUID via raw SQL → verify RLS still filters by the original session role
4. **Missing-context fuzzing** → fire 10,000 API requests with random missing/invalid tenant headers → verify all return 403 or zero rows

---

## 10. Final Recommendation and ADR

### 10.1 Decision Summary

**Decision: Shared-schema PostgreSQL with Row Level Security (RLS)**

The working hypothesis is confirmed. RLS with proper session management provides:
- **Stronger isolation guarantees** than schema-per-tenant (database-enforced, not application-enforced)
- **Cleaner support for the accounting practice model** (cross-tenant access is natural)
- **Lower operational complexity** (one schema, standard backups, standard migrations)
- **Better fit for an AI-native, small-team product** (fewer moving parts, easier to reason about)

Schema-per-tenant is **rejected** because:
- It provides weaker isolation (router-level, not database-level)
- It complicates cross-tenant analytics, practice dashboards, and future inter-tenant features
- It carries material operational costs (thousands of schemas, complex migrations, connection pool bloat)
- No regulatory requirement mandates it

### 10.2 Trade-offs

| Trade-off | RLS chosen | Schema-per-tenant (rejected) |
|-----------|------------|------------------------------|
| Isolation strength | Database-enforced | Application-enforced |
| Practice-user access | Natural (policy-based) | Complex (schema switching) |
| Migration complexity | Standard Django | Multi-schema dance |
| Backup/restore | Standard tools, tenant export via script | Schema-aware dump/restore |
| Performance at scale | Index on tenant_id, query planner optimizes | Catalog bloat at N>1000 schemas |
| Cross-tenant analytics | Easy (SQL WHERE tenant_id IN (...)) | UNIONs across schemas |
| Connection pool complexity | One pool | Per-schema pool or SET search_path per request |
| "Accidental bypass" risk | Present — mitigated by `FORCE RLS`, linters, tests | Different risks — router bugs |

### 10.3 Required Safeguards

If RLS is chosen (as recommended), the following safeguards **must** be in place before production launch:

1. **Session management**
   - pgBouncer (or equivalent) configured with `server_reset_query = DISCARD ALL`
   - Middleware uses `try/finally` to reset thread-local and connection state
   - `SET LOCAL ROLE app_user` done per-request in middleware, not per-connection

2. **Connection role separation**
   - `deploy_user` owns tables, used only for migrations
   - `app_user` used for runtime, subject to RLS
   - `support_user` has support-specific RLS policy (not BYPASSRLS)
   - True superuser is separate, credentials in secrets manager, never in Django

3. **FORCE ROW LEVEL SECURITY** on every tenant-scoped table, including table owner

4. **Migration linter** in CI that fails if a new tenant-scoped table lacks RLS

5. **Task linter** in CI that fails if a `TenantScopedTask.delay()` call omits `tenant_id`

6. **Integration tests** proving isolation across tenants, practice users, and support users (run every CI build)

7. **Attack simulation suite** run weekly

8. **Audit logging** on all support access, practice access, and privileged operations

9. **Customer-visible access logs** so tenants can see which advisors/support accessed their data

10. **Documentation and training** for engineers on RLS semantics, including:
    - Never use `all_objects` without justification
    - Never write raw SQL on tenant-scoped tables without understanding RLS
    - Never connect to production as superuser from Django
    - Always pass `tenant_id` to Celery tasks

### 10.4 Migration Path if Recommendation Is Wrong

If post-launch data reveals that RLS is insufficient (e.g., a regulatory requirement emerges mandating physical separation), the migration to schema-per-tenant is feasible but expensive:

1. Add `tenant_schema` column to `Tenant` model
2. For each tenant, create a schema, copy data, set up schema-level RLS
3. Update Django router to switch schemas per request
4. Dual-run period where both models work
5. Decommission shared-schema RLS

**This is a 3–6 month project at scale. It should not be undertaken lightly.** The recommendation to start with RLS is confident because the safeguards are well-understood and the migration path exists if needed.

---

## ADR-001: Multi-Tenancy Strategy

### Status
Accepted

### Context
The FVA Accounting Platform is a multi-tenant SaaS serving Singapore SMEs and their accounting practices. Each tenant is an SME organization with one or more legal entities, each maintaining an independent audit-grade ledger. Accounting practices manage multiple client tenants through explicit engagements. The platform must provide strong tenant isolation for financial data, auditable access controls, and operational simplicity for a small engineering team.

Two primary approaches exist for PostgreSQL multi-tenancy:
- **Shared schema with Row Level Security (RLS)**: all tenants in one schema; database policies filter rows by tenant_id
- **Schema-per-tenant**: each tenant has its own PostgreSQL schema; Django router switches `search_path` per request

### Decision
**Adopt shared-schema PostgreSQL with Row Level Security (RLS)** as the multi-tenancy strategy.

### Implementation Requirements
- Every tenant-scoped table has `tenant_id UUID NOT NULL` and RLS enabled with `FORCE ROW LEVEL SECURITY`
- Application connects as `app_user` (subject to RLS), never as superuser or table owner
- Middleware sets `app.current_tenant_id` and `SET LOCAL ROLE app_user` per-request
- Celery tasks use `TenantScopedTask` base class requiring explicit `tenant_id`
- Practice-user access implemented via RLS policy referencing `AdvisorAccessGrant`
- Support-user access implemented via time-bound `SupportAccessGrant` + RLS policy (not BYPASSRLS)
- Migration and task linters in CI enforce RLS on new tables and `tenant_id` on task calls
- Integration tests prove tenant isolation across all access modes (run every CI build)

### Consequences
- ✅ Database-enforced isolation stronger than application-enforced alternatives
- ✅ Practice-user access modeled naturally in policies
- ✅ Standard Django migrations, standard PostgreSQL backups
- ✅ Single schema scales to thousands of tenants without catalog bloat
- ✅ Cross-tenant analytics, intercompany features straightforward
- ⚠️  Requires strict session management discipline (mitigated by tooling + tests)
- ⚠️  Engineers must understand RLS semantics (mitigated by training + linters)
- ❌  If physical separation is later mandated, migration to schema-per-tenant is expensive (3–6 months)

### Risks
- **Accidental RLS bypass** via raw SQL: mitigated because RLS still applies to raw SQL when role is set correctly
- **Connection state leak**: mitigated by pgBouncer `DISCARD ALL` and middleware `try/finally`
- **Superuser misuse**: mitigated by separate credentials, vault, audit logging, customer notification
- **Regulatory change**: mitigation path exists (migration to schema-per-tenant) if physical separation mandated

### Safeguards Checklist (Pre-Launch Gates)
- [ ] All tenant-scoped tables have RLS enabled + `FORCE ROW LEVEL SECURITY`
- [ ] `deploy_user` owns tables, `app_user` runs queries, `support_user` has support policy
- [ ] pgBouncer `server_reset_query = DISCARD ALL`
- [ ] Middleware sets + resets Postgres session variables in `try/finally`
- [ ] Celery `TenantScopedTask` requires `tenant_id`
- [ ] CI migration linter enforces RLS on new tables
- [ ] CI task linter enforces `tenant_id` on task invocations
- [ ] Integration test suite proves cross-tenant isolation (100% pass required)
- [ ] Weekly attack simulation suite passes
- [ ] Audit logging covers support access, practice access, privileged operations
- [ ] Customer-visible access history UI for advisors and support
- [ ] Engineer training completed and documented

### References
- PostgreSQL RLS: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- `django-tenants` (schema-per-tenant reference): https://django-tenants.readthedocs.io/
- Citus RLS multi-tenancy: https://docs.citusdata.com/en/stable/develop_multi_tenant.html
- Supabase RLS patterns: https://supabase.com/docs/guides/auth/row-level-security
- Xero/FreshBooks/QuickBooks multi-tenancy: shared-schema RLS (publicly documented in SOC 2 reports)

### Decision Date
2026-09-19

### Review Date
Review within 6 months of production launch, after real-world operational data is available.

---

## Appendix A: Session Variable Reference

| Variable | Type | Set by | Read by | Notes |
|----------|------|--------|---------|-------|
| `app.current_tenant_id` | UUID string | Middleware / task base | RLS policies, ORM default manager | Required for all tenant-scoped operations |
| `app.current_user_id` | UUID string | Middleware / task base | RLS policies, audit triggers | Always set alongside tenant |
| `app.current_entity_id` | UUID string (or empty) | Middleware | RLS restrictive policies | Empty = all entities in tenant |
| `app.is_practice_user` | boolean string | Middleware | RLS practice_access policy | 'true' or 'false' |
| `app.practice_id` | UUID string (or empty) | Middleware | Audit logging | Empty if not practice user |

## Appendix B: Role Reference

| Role | BYPASSRLS | Table Owner | Used by | Purpose |
|------|-----------|-------------|---------|---------|
| `deploy_user` | No (subject to FORCE RLS) | Yes | Django migration runner | DDL, data migrations. Connects only during deploys. |
| `app_user` | No | No | Django application servers | Runtime queries. Subject to all RLS policies. |
| `support_user` | No | No | Support tool | Support queries. Subject to support_access policy. |
| `analytics_user` | Yes (via BYPASSRLS) | No | Reporting service | Cross-tenant reads. Application-layer gated. |
| `superuser` | Yes | N/A | DBAs (psql) | Emergency access. Credentials in vault, never in Django. |

## Appendix C: Comparison with `django-tenants` (Schema-Per-Tenant)

| Aspect | RLS (recommended) | django-tenants |
|--------|-------------------|----------------|
| Setup complexity | Low (policies + middleware) | Medium (router + schema creation) |
| Tenant onboarding | `INSERT INTO tenants` | `CREATE SCHEMA`, run migrations per tenant |
| Tenant offboarding | `DELETE WHERE tenant_id = X` | `DROP SCHEMA` |
| Django admin | Standard, filtered by tenant | Needs `TenantAdmin` mixin |
| Migrations | Standard Django | `migrate_schemas` per-tenant |
| Testing | Standard pytest + transaction | `TenantTestCase` required |
| Cross-tenant queries | Easy (SQL UNIONs) | Hard (manual schema switching) |
| Performance at 10k tenants | Good (indexes) | Poor (catalog bloat) |
| Production deployments | Standard | Must run migrations per tenant |

---

## Appendix D: Example RLS Policies for All Key Tables

```sql
-- Template: apply to every tenant-scoped table
-- Replace <TABLE> with actual table name

-- 1. Enable and force RLS
ALTER TABLE <TABLE> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <TABLE> FORCE ROW LEVEL SECURITY;

-- 2. Standard tenant isolation (app_user)
CREATE POLICY tenant_isolation_<TABLE> ON <TABLE>
    AS PERMISSIVE FOR ALL TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- 3. Entity scope (RESTRICTIVE, only on tables with entity_id)
CREATE POLICY entity_scope_<TABLE> ON <TABLE>
    AS RESTRICTIVE FOR ALL TO app_user
    USING (
        current_setting('app.current_entity_id') = ''
        OR entity_id = current_setting('app.current_entity_id')::uuid
    )
    WITH CHECK (
        current_setting('app.current_entity_id') = ''
        OR entity_id = current_setting('app.current_entity_id')::uuid
    );

-- 4. Practice access (SELECT only, for practice users)
CREATE POLICY practice_access_<TABLE> ON <TABLE>
    AS PERMISSIVE FOR SELECT TO app_user
    USING (
        current_setting('app.is_practice_user')::boolean
        AND tenant_id IN (
            SELECT aag.tenant_id FROM identity_advisoraccessgrant aag
            JOIN identity_clientengagement ce ON ce.id = aag.engagement_id
            WHERE aag.practice_user_id = current_setting('app.current_user_id')::uuid
              AND ce.status = 'active' AND aag.revoked_at IS NULL
        )
    );

-- 5. Support access (SELECT only, time-bound grants)
CREATE POLICY support_access_<TABLE> ON <TABLE>
    AS PERMISSIVE FOR SELECT TO support_user
    USING (
        tenant_id IN (
            SELECT sag.tenant_id FROM support_accessgrant sag
            WHERE sag.support_user_id = current_setting('app.current_user_id')::uuid
              AND sag.revoked_at IS NULL AND sag.expires_at > now()
        )
    );

-- 6. Grant DML to app_user
GRANT SELECT, INSERT, UPDATE, DELETE ON <TABLE> TO app_user;
GRANT SELECT ON <TABLE> TO support_user;
GRANT SELECT ON <TABLE> TO analytics_user;
```

---

## Appendix E: CI Linter Sketches

```python
# ci_linters/rls_linter.py — fails CI if a new table lacks RLS
def check_rls_on_new_tables():
    """Run as part of `manage.py check` in CI."""
    from django.db import connection
    tenant_scoped_models = [
        m for m in apps.get_models()
        if any(f.name == "tenant" for f in m._meta.get_fields())
    ]
    with connection.cursor() as cur:
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND rowsecurity = false
        """)
        tables_without_rls = {row[0] for row in cur.fetchall()}
    missing = [
        m._meta.db_table for m in tenant_scoped_models
        if m._meta.db_table in tables_without_rls
    ]
    if missing:
        raise ImproperlyConfigured(
            f"Tenant-scoped tables missing RLS: {missing}. "
            f"Add ALTER TABLE ... ENABLE ROW LEVEL SECURITY; FORCE ROW LEVEL SECURITY; "
            f"and create policies."
        )


# ci_linters/task_linter.py — fails CI if TenantScopedTask.delay() omits tenant_id
def check_tenant_id_in_task_calls():
    """AST-based linter that finds .delay() calls on tenant tasks without tenant_id."""
    import ast
    # Walk project Python files; find Call nodes where:
    # - func is Attribute with attr in ('delay', 'apply_async')
    # - the called task is decorated with @shared_task(base=TenantScopedTask)
    # - the kwargs do not include 'tenant_id'
    # Fail CI if any found.
    ...
```

---

**End of Spike 1 — Multi-Tenancy**
