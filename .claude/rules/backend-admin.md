---
glob: "backend/*/admin.py"
---

# Backend — Django Admin Rules

## Admin Registration
- Register all models in their respective app's `admin.py` — do not leave models unregistered
- Use `@admin.register(Model)` decorator — not `admin.site.register()` calls
- Each model gets its own `ModelAdmin` class — do not share `ModelAdmin` across models

## Admin Display
- Set `list_display` with at minimum: `id`, `created_at`, and 2-3 domain-relevant fields
- Set `list_filter` for fields used to narrow results (tenant, type, status)
- Set `search_fields` for text fields that users will search by (name, description, email)
- Set `readonly_fields` for system-managed fields (`id`, `created_at`, `updated_at`)
- Set `ordering` to match the model's default ordering

## Admin Limitations
- Django admin is for internal/developer use only — not the end-user admin hub
- Do not customize admin templates heavily — the admin hub (React app) replaces it for production
- Do not add custom admin actions that perform business logic — use the service layer

## Tenant Awareness
- All `ModelAdmin` classes must filter by tenant via `get_queryset()` — do not show cross-tenant data
- Use `list_filter` with tenant field for superuser admin access

## Sources
# Principles: [Convention over Configuration, Separation of Concerns (admin is for ops, not business logic)]
# Web: https://docs.djangoproject.com/en/stable/ref/contrib/admin/
# Date: 2026-04-16