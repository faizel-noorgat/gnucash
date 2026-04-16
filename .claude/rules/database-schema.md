---
glob: "backend/**/*.sql"
---

# Database — PostgreSQL Schema Rules

## Row Level Security
- Every tenant-scoped table must have RLS enabled via `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY`
- RLS policy: `USING (tenant_id = current_setting('app.current_tenant')::uuid)` for tenant isolation
- Use `RESTRICTIVE` policies for tenant isolation, `PERMISSIVE` for admin access overrides
- Admin bypass policy: `USING (current_setting('app.is_admin')::boolean = true)` with `RESTRICTIVE` tenant policy
- Set `app.current_tenant` via Django middleware on every request — never trust client-side values

## Schema Design
- Use `UUID` for all primary keys and foreign keys — not `SERIAL` or `BIGINT`
- Use `TIMESTAMPTZ` for all timestamps — never `TIMESTAMP` without timezone
- Use `NUMERIC(12, 2)` for monetary columns — never `FLOAT` or `DOUBLE PRECISION`
- Use `TEXT` for variable-length text — PostgreSQL `TEXT` has no performance penalty vs `VARCHAR`
- Add `NOT NULL` constraints on all required columns — never rely on application-level validation alone

## Indexes
- Index all foreign key columns — PostgreSQL does not auto-index FKs
- Index columns used in `WHERE`, `JOIN`, and `ORDER BY` clauses
- Use partial indexes for filtered queries (e.g., `WHERE reconciled = 'NONE'`)
- Use `CREATE INDEX CONCURRENTLY` for production migrations — avoids table locks

## Constraints
- Use `CHECK` constraints for enum-like fields at the database level — not just in Django
- Use `UNIQUE` constraints for naturally unique columns (email, tenant slug)
- Multi-column unique constraints for tenant-scoped uniqueness: `UNIQUE (tenant_id, slug)`
- Use `FOREIGN KEY` constraints with `ON DELETE CASCADE` or `ON DELETE RESTRICT` — match Django's `on_delete`

## Migrations & Raw SQL
- Raw SQL in Django migrations via `migrations.RunSQL()` — not standalone `.sql` files
- RLS policies created via `RunSQL` in a migration — not via Django model operations
- Always include `REVOKE` and `GRANT` statements when creating new tables — default PostgreSQL permissions are too permissive

## Sources
# Principles: [Defense in Depth (RLS as second layer), Data Integrity (constraints at DB level)]
# Web: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
# Web: https://www.postgresql.org/docs/current/sql-createpolicy.html
# Date: 2026-04-16