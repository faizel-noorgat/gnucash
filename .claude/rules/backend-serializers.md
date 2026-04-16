---
glob: "backend/*/serializers.py"
---

# Backend — Serializer Rules

## Base Class Selection
- Use `ModelSerializer` for all model-backed endpoints
- Use plain `Serializer` for non-model endpoints (auth login, import templates, report parameters)
- Use `ListSerializer` for bulk operations — do not loop serializers in views

## Field Conventions
- Use `fields = '__all__'` only for internal/admin serializers — list fields explicitly for public API serializers
- Use `read_only_fields` for computed or system-managed fields (`id`, `created_at`, `updated_at`, `full_name`)
- Never expose `tenant_id` as a writable field — set it from the request context
- Never expose internal fields (`password_hash`, `stripe_customer_id`) in any serializer

## Validation
- Field-level validation via `validate_<fieldname>(self, value)` methods
- Cross-field validation via `validate(self, data)` method
- Raise `serializers.ValidationError` with dict for field-specific errors, string for general errors
- Do not perform database queries in field-level validators — use object-level `validate()` for uniqueness checks

## Nested Objects
- Use nested `ModelSerializer` for read-only related objects (e.g., `account` within a split)
- For writable nested objects, override `create()` and `update()` — DRF does not support writable nested serializers by default
- Use `PrimaryKeyRelatedField` for write-only relationships where the client sends IDs
- Use `SlugRelatedField` with `slug_field` for lookups by natural keys (e.g., account by `full_name`)

## Tenant Scoping
- Serializer querysets for related fields must be scoped to the current tenant — use `queryset=` with tenant-filtered querysets
- Do not include tenant validation in serializers — it is handled by the middleware and view layer

## Output Representation
- Use `to_representation()` for custom output formatting (e.g., enum display values, computed summary fields)
- Use separate serializers for list vs. detail views when the detail requires significantly more data
- Do not include `HyperlinkedIdentityField` — use primary key or UUID-based URLs

## Sources
# Principles: [SRP (one serializer = one representation concern), Cohesion (validation belongs here, not in the view)]
# Web: https://www.django-rest-framework.org/api-guide/serializers/
# Web: https://context7.com/encode/django-rest-framework/llms.txt
# Date: 2026-04-16