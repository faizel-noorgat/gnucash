---
glob: "backend/*/urls.py"
---

# Backend — URL Routing Rules

## Router Pattern
- Use DRF `DefaultRouter` for registering ViewSets — do not wire views manually
- Register ViewSets with a `basename` matching the model name (singular): `router.register('accounts', AccountViewSet, basename='account')`
- API versioning via URL path: all routes under `/api/v1/`

## URL Structure
- Include app-level `urls.py` from the project `urls.py` via `include()`
- Each Django app owns its `urls.py` — do not define routes for other apps
- Custom `@action` endpoints on ViewSets generate URLs automatically — do not add manual URL patterns for them
- Non-ViewSet endpoints (auth, reports, imports) use `path()` in the appropriate app's `urls.py`

## Naming
- `app_name` must be set in every `urls.py` for URL namespacing
- URL names use kebab-case: `account-list`, `transaction-detail`
- Do not use raw regex patterns in URLs — use Django's path converters or `<uuid:pk>` syntax

## Admin Hub Routes
- Admin API routes live under `/api/v1/admin/` prefix — separate from tenant routes
- Admin ViewSets use the same router pattern but in a separate URL include

## Sources
# Principles: [Separation of Concerns (routing is configuration, not logic), Convention over Configuration]
# Web: https://www.django-rest-framework.org/api-guide/routers/
# Web: https://docs.djangoproject.com/en/stable/topics/http/urls/
# Date: 2026-04-16