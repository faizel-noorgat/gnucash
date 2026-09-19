# Identity & Access Service

**Bounded Context:** Identity & Access  
**Version:** 1.0.0  
**Stack:** Django 5.x, Django REST Framework, PostgreSQL with RLS  
**Status:** Scaffolded — Phase E

---

## Overview

This service provides the platform foundation for authentication, authorization, multi-tenancy, and access control. It implements the accounting practice/advisor access model for FVA Advisory.

## Responsibilities

- **Authentication:** Email/password, OAuth, SSO (enterprise), MFA
- **Multi-Tenancy:** Shared-schema PostgreSQL with Row Level Security (RLS); defense-in-depth with ORM filters + database-enforced policies
- **Tenant & Legal Entity Management:** Workspace and entity lifecycle
- **User Memberships & Invitations:** User ↔ tenant relationships with roles
- **Role-Based Access Control (RBAC):** Workspace-level and entity-scoped permissions
- **Accounting Practice / Advisor Access:** Practice, PracticeMembership, ClientEngagement, AdvisorAccessGrant
- **Session Management:** JWT tokens, session lifecycle
- **API Token Management:** For API integrations
- **Notifications:** Cross-cutting infrastructure (email, in-app, workflow state machines)

## Architecture Decisions

- **ADR-001:** Modular monolith for v1 (5 bounded contexts in single Django app)
- **ADR-008:** Shared-schema PostgreSQL with RLS for multi-tenancy
- **ADR-005:** Accounting practice access model (Practice, PracticeMembership, ClientEngagement, AdvisorAccessGrant)

## Technology Choices

- **Backend Framework:** Django 5.x
- **API:** Django REST Framework (REST only for v1)
- **Database:** PostgreSQL 16+ with Row Level Security
- **Authentication:** django-allauth + custom MFA
- **Background Jobs:** Celery + Redis broker (for async notifications)
- **Notifications:** Polling for v1 (30s intervals); WebSockets deferred to v2

## Directory Structure

```
identity-access/
├── README.md
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── manage.py
├── pytest.ini
├── identity_access/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   ├── celery.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── tenant.py
│   │   │   ├── legal_entity.py
│   │   │   ├── membership.py
│   │   │   ├── role.py
│   │   │   ├── permission.py
│   │   │   ├── api_token.py
│   │   │   ├── practice.py
│   │   │   ├── client_engagement.py
│   │   │   ├── advisor_access_grant.py
│   │   │   ├── notification.py
│   │   │   └── workflow_state.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── authentication_service.py
│   │   │   ├── authorization_service.py
│   │   │   ├── tenant_service.py
│   │   │   ├── membership_service.py
│   │   │   ├── practice_service.py
│   │   │   └── notification_service.py
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── ...
│   ├── api/
│   │   ├── __init__.py
│   │   ├── views/
│   │   │   ├── __init__.py
│   │   │   ├── auth_views.py
│   │   │   ├── tenant_views.py
│   │   │   ├── membership_views.py
│   │   │   ├── practice_views.py
│   │   │   └── notification_views.py
│   │   ├── serializers/
│   │   │   ├── __init__.py
│   │   │   └── ...
│   │   ├── urls.py
│   │   ├── permissions.py
│   │   └── middleware.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── rls_policies.py
│       ├── tenant_context.py
│       └── migrations/
│           ├── __init__.py
│           └── ...
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   ├── test_models.py
    │   ├── test_services.py
    │   └── test_repositories.py
    ├── integration/
    │   ├── test_api.py
    │   ├── test_rls_isolation.py
    │   └── test_practice_access.py
    └── acceptance/
        ├── test_authentication_rules.py
        ├── test_authorization_rules.py
        └── test_multi_tenancy_rules.py
```

## Behavior Contract Rules

The following behavior-contract rules are enforced by this service:

### Authentication & Authorization
- **BR-AUTH-001:** Users must authenticate before accessing tenant resources
- **BR-AUTH-002:** API tokens must be scoped to specific permissions
- **BR-AUTH-003:** Expired tokens must be rejected
- **BR-AUTH-004:** MFA enrollment must be enforced for admin roles (configurable)

### Multi-Tenancy & Isolation
- **BR-TENANT-001:** Users can only access tenants they are members of
- **BR-TENANT-002:** Tenant context must be established before any tenant-scoped query
- **BR-TENANT-003:** RLS policies must prevent cross-tenant data leakage
- **BR-TENANT-004:** Practice users must explicitly switch tenant context

### Practice / Advisor Access
- **BR-PRACTICE-001:** Practice access requires explicit ClientEngagement
- **BR-PRACTICE-002:** Practice access is revocable by the client tenant
- **BR-PRACTICE-003:** All practice actions must be logged with practice_id and engagement_id
- **BR-PRACTICE-004:** Practice users cannot access client data without active AdvisorAccessGrant

### Notifications
- **BR-NOTIF-001:** Notifications must be delivered asynchronously (Celery)
- **BR-NOTIF-002:** Users can configure notification preferences
- **BR-NOTIF-003:** Workflow state transitions must be atomic and auditable

## Testing Strategy

- **Unit tests:** Model validation, service logic, repository methods
- **Integration tests:** API endpoints, RLS isolation, practice access workflows
- **Acceptance tests:** Behavior-contract rules (executable Given/When/Then)
- **Security tests:** RLS attack simulation, cross-tenant access attempts

## Running Tests

```bash
# Install dependencies
pip install -r requirements/dev.txt

# Run all tests
pytest

# Run acceptance tests only
pytest tests/acceptance/

# Run with coverage
pytest --cov=identity_access --cov-report=html
```

## Security Considerations

- **RLS Enforcement:** All tenant-scoped tables have `FORCE ROW LEVEL SECURITY`
- **Session Variables:** Tenant context set via `SET LOCAL` within database transactions
- **pgBouncer:** Configured with `DISCARD ALL` to prevent context leakage
- **Audit Trail:** All authentication/authorization events logged to AuditEvent table
- **Credential Handling:** No credential literals in code; use env-var placeholders

## Migration Path

This service is designed to be extracted as a standalone microservice if scaling demands it. Clear bounded context boundaries, dependency injection, and repository patterns facilitate future extraction.

---

**Next Steps:**
1. Implement domain models with RLS policies
2. Implement authentication/authorization services
3. Implement practice/advisor access workflows
4. Implement notification infrastructure
5. Write comprehensive acceptance tests for all behavior-contract rules
