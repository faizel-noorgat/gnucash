---
glob: "backend/*/models.py"
---

# Backend — Django Model Rules

## Field Conventions
- Use `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)` for all model primary keys
- All models must include `created_at` and `updated_at` fields via a common abstract base class
- Use `models.CharField(max_length=...)` with explicit `max_length` — never omit it
- Use `models.TextField()` for content exceeding ~255 characters
- Use `models.DecimalField(max_digits=12, decimal_places=2)` for all monetary values — never `FloatField`
- Use `models.DateField()` for dates, `models.DateTimeField()` for timestamps
- Use `models.JSONField()` for flexible structured data (recurring templates, audit old/new values)

## Relationship Conventions
- All `ForeignKey` fields must specify `on_delete` explicitly — never rely on the default
- Use `on_delete=models.CASCADE` for child records (splits, budget categories)
- Use `on_delete=models.PROTECT` for reference data that must not be deleted while referenced
- All `ForeignKey` and `ManyToManyField` must specify `related_name` — never leave it as the default `<model>_set`
- `related_name` must be the plural form of the model name from the reverse perspective (e.g., `splits`, not `transaction_splits`)

## Tenant Scoping
- All models (except `User`) must include `tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)` as the first foreign key
- Set `current_tenant_field = 'tenant'` on the model Meta class for `django-multitenant`
- Use `MultiTenantManager` as the default manager for all tenant-scoped models

## Meta Class
- Every model must define a `class Meta` with at minimum `ordering = ['created_at']` or domain-appropriate ordering
- Use `constraints = [...]` with `UniqueConstraint` for uniqueness rules — do not use deprecated `unique_together`
- Use `indexes = [...]` for query performance — index foreign keys and frequently-filtered fields (`tenant_id`, `entry_date`)
- Set `verbose_name` and `verbose_name_plural` for admin display

## Double-Entry Invariants
- The `Split` model must enforce via `clean()` that `value` is non-zero
- Account type must be constrained to `models.TextChoices` enum — no free-text types
- Cannot change account type after transactions exist — enforce in model `clean()` or service layer

## Query Location
- Model methods are for simple, single-instance computed properties only
- Complex queries belong in custom model managers (`models.Manager` subclasses), not model methods
- Do not import other app's models inside model files — use managers and services for cross-app queries
- N+1 prevention: access related objects via `select_related()` and `prefetch_related()` in views, not model-level lazy access

## Sources
# Principles: [Cohesion (fields that belong together), Single Responsibility (no query logic in model definitions), Separation of Concerns]
# Web: https://docs.djangoproject.com/en/stable/ref/models/
# Web: https://context7.com/encode/django-rest-framework/llms.txt
# Date: 2026-04-16