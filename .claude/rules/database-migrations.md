---
glob: "backend/*/migrations/*.py"
---

# Database — Migration Rules

## Migration Structure
- One migration per schema change — do not combine unrelated changes
- Never modify a migration after it has been applied to any environment (including production)
- Use `python manage.py makemigrations` — do not write migration files by hand unless performing data migrations
- Migration filenames are auto-generated — do not rename them

## Data Migrations
- Data migrations must use `apps.get_model()` to get historical model versions — never import model classes directly
- Data migrations with large datasets must batch updates in chunks of 1000 with `transaction.atomic()` per batch
- Set `atomic = False` on the Migration class for large data migrations to avoid long-running transactions
- Data migrations must be idempotent — running them twice must not corrupt data

## Dependencies
- Declare dependencies on other apps' migrations in the `dependencies` list when referencing cross-app models
- When a `RunPython` function accesses models from another app, include that app's latest migration as a dependency
- Do not remove dependencies from the `dependencies` list even if Django suggests they are unnecessary

## Destructive Operations
- Never delete a column in a single migration — use a three-step process: (1) make column nullable, (2) backfill/verify, (3) remove field
- Never rename a column directly in production — use `RenameField` with a migration that has been tested against a production-like database
- Adding non-nullable fields to existing tables requires a default value or a two-step migration (nullable first, then backfill)

## PostgreSQL-Specific
- Use `AddConstraint` and `AddIndex` operations for RLS-supporting indexes and constraints
- RLS policies are managed via `migrations.RunSQL()` — not Django model operations
- Index creation on large tables: use `AddIndexConcurrently` for PostgreSQL to avoid table locks

## Squash Policy
- Do not squash migrations during active development
- Squash only after a release is tagged and all environments have applied the squashed migrations
- Keep the original migration files alongside the squashed version until all environments have migrated

## Sources
# Principles: [SRP (one migration = one schema change), Open/Closed (migrations are append-only)]
# Web: https://docs.djangoproject.com/en/stable/topics/migrations/
# Web: https://docs.djangoproject.com/en/stable/howto/writing-migrations/
# Date: 2026-04-16