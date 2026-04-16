---
glob: "backend/*/views.py"
---

# Backend — API Views Rules

## View Pattern
- Use DRF `ModelViewSet` for standard CRUD endpoints (accounts, transactions, budgets, receipts, recurring, notifications)
- Use `@action(detail=True/False)` decorator for non-CRUD operations (e.g., `process` on receipts, `register` on accounts)
- Use generic `APIView` only for non-model endpoints (auth login/logout, report generation, import/export)
- Do not use function-based views (`@api_view`) — class-based views only for consistency

## Business Logic
- Never place business logic in views — views orchestrate: authenticate, validate, delegate, respond
- Business logic lives in service modules (`services.py`) within each Django app
- Views call services; services return data or raise domain exceptions
- Do not write ORM queries directly in views — use model managers or service functions

## Validation
- Input validation happens in serializers, never in views
- Views call `serializer.is_valid(raise_exception=True)` — never handle validation errors manually
- Cross-field validation uses `validate(self, data)` method on the serializer
- Tenant scoping: views must set `tenant` on created objects — never trust client-provided tenant IDs

## Permission & Authentication
- Set `permission_classes` at the class level — default to `[IsAuthenticated]`
- Use `get_permissions()` for action-specific overrides (e.g., allow anonymous access to auth registration)
- Tenant isolation: use `X-Tenant-ID` header validated against user's memberships in a middleware, not per-view
- Use `perform_create()` and `perform_update()` on viewsets to set `created_by` and enforce ownership

## HTTP Status Codes
- `200 OK`: Successful GET, PUT
- `201 Created`: Successful POST creating a resource
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Validation failure
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found (or does not belong to tenant)
- `409 Conflict`: Concurrent modification, double-entry violation
- `422 Unprocessable Entity`: Business rule violation

## Query Optimization
- Override `get_queryset()` to apply `select_related()` and `prefetch_related()` for accessed relationships
- Apply tenant scoping in `get_queryset()` — filter by `self.request.tenant`
- Use pagination — default `PageNumberPagination` with configurable page size

## Response Format
- Return serialized data via DRF serializers — never construct dicts manually in views
- Use DRF's built-in pagination in list responses
- Error responses use DRF's default error format — do not customize unless there is a specific requirement

## Sources
# Principles: [SRP (one endpoint = one operation), Separation of Concerns (no business logic in transport layer), Dependency Inversion]
# Web: https://www.django-rest-framework.org/api-guide/viewsets/
# Web: https://www.django-rest-framework.org/api-guide/generic-views/
# Date: 2026-04-16