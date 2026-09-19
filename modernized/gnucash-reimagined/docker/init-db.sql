-- Bootstrap the application role for a containerised PostgreSQL instance.
--
-- SCOPE: this script creates the *role* only. It deliberately does NOT create
-- the RLS helper functions or any policy.
--
-- Functions and policies live in Django migrations, under common/rls/migrations/:
--
--    0001_rls_functions_and_app_role  - get_current_{tenant,user,entity}_id()
--                                       and the app_user role
--    0002_rls_tenant_isolation_policies - ENABLE + FORCE RLS and the
--                                       tenant_isolation policy, per table
--
-- They used to be defined here as well. That was the problem, not the
-- redundancy: this script targeted a single hard-coded database (gnucash_dev),
-- nothing on the development machine ever ran it (docker is not installed), and
-- it declared get_current_user_id() and get_current_entity_id() as
-- `RETURNS integer` against UUID primary keys - so the cast raised, an
-- `EXCEPTION WHEN OTHERS THEN RETURN NULL` handler swallowed it, and the
-- functions returned NULL for every input. Every policy keyed on user or entity
-- context would have read NULL silently. (B-0004)
--
-- Two definitions of the same security function, only one of which is executed,
-- is how the wrong one survives. So there is now exactly one: the migration.
-- A clean deployment gets the correct functions and policies from
-- `manage.py migrate`, whatever the database is called and however it is
-- provisioned.
--
-- The role is created here as well as in migration 0001 because a container
-- needs it to exist before the application can connect at all. Migration 0001
-- is idempotent over this (`IF NOT EXISTS`, then `ALTER ROLE`), so running both
-- is safe in either order.
--
-- The credential is granted here rather than in the migration because a
-- provisioning migration must never invent one, and granted here rather than
-- in the web service's start command because the role has to exist first.
-- Granting it is idempotent and nothing later revokes it: migration 0001
-- re-asserts NOSUPERUSER/NOBYPASSRLS/NOCREATEDB/NOCREATEROLE, deliberately not
-- LOGIN.
--
--     ALTER ROLE app_user LOGIN PASSWORD '<runtime password>';

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        -- NOLOGIN: deployments grant LOGIN and a password out of band, so this
        -- file never has to carry a credential. NOBYPASSRLS is the point of the
        -- role - a role that can bypass RLS makes every policy advisory.
        CREATE ROLE app_user NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;

-- Table and sequence privileges are granted by migration 0001, which runs after
-- the tables exist and can therefore grant on all of them, plus set the default
-- privileges that cover tables added later.
