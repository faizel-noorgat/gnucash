"""
Provision the RLS helper functions and the runtime ``app_user`` role.

This migration supersedes ``docker/init-db.sql`` as the authoritative
provisioning mechanism. That file targeted a single hard-coded database
(``gnucash_dev``), was never executed by anything on this machine (docker is not
installed), and declared two of its three functions with the wrong return type.
A clean deployment now gets the correct functions from the migration graph.

Fail-closed contract shared by all three functions
--------------------------------------------------
Each function reads a transaction-local GUC and casts it to ``uuid``:

* **Unset or empty** -> ``NULL``. ``tenant_id = NULL`` is never true, so every
  policy denies and readers see no rows. That is the intended behaviour for
  genuinely context-free work.
* **Malformed** -> the cast itself raises ``invalid input syntax for type
  uuid``. The previous definitions wrapped the body in
  ``EXCEPTION WHEN OTHERS THEN RETURN NULL``, which converted a malformed
  context into a silent NULL: the same "no rows" outcome as a legitimately
  absent context, so a bug in the context writer was indistinguishable from
  normal operation. The exception handler is deliberately gone. A malformed
  tenant context is a defect and must be loud.

``RETURNS uuid`` on all three: every primary key in ``apps/identity`` and
``apps/accounting`` is ``models.UUIDField(primary_key=True)``, and
``common/middleware/tenant.py`` writes ``request.user.id``, which is that UUID.
The old ``get_current_user_id()`` / ``get_current_entity_id()`` declared
``RETURNS integer``, so the cast raised and the handler swallowed it - the
functions returned NULL for every input, always. (B-0004)
"""

from django.db import migrations

# `STABLE`, not `VOLATILE`: the value cannot change within a single statement.
# Written in SQL rather than plpgsql specifically so there is no block in which
# an exception handler could be reintroduced around the cast.
#
# DROP before CREATE, not CREATE OR REPLACE. `docker/init-db.sql` may already
# have created `get_current_user_id()` and `get_current_entity_id()` with
# `RETURNS integer`, and PostgreSQL refuses CREATE OR REPLACE when the return
# type differs - it would fail with "cannot change return type of existing
# function" and abort the migration on exactly the deployments that had run the
# old script. Dropping first makes this migration authoritative wherever it runs.
CREATE_FUNCTIONS = """
DROP FUNCTION IF EXISTS get_current_tenant_id();
DROP FUNCTION IF EXISTS get_current_user_id();
DROP FUNCTION IF EXISTS get_current_entity_id();

CREATE FUNCTION get_current_tenant_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid
$$;

CREATE OR REPLACE FUNCTION get_current_user_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.current_user_id', TRUE), '')::uuid
$$;

CREATE OR REPLACE FUNCTION get_current_entity_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.current_entity_id', TRUE), '')::uuid
$$;
"""

DROP_FUNCTIONS = """
DROP FUNCTION IF EXISTS get_current_tenant_id();
DROP FUNCTION IF EXISTS get_current_user_id();
DROP FUNCTION IF EXISTS get_current_entity_id();
"""

# The runtime role. It must not own any table - a table's owner can always
# disable its own RLS, so ownership is itself a bypass. It must not have
# BYPASSRLS for the same reason, and is NOLOGIN here so the migration never
# invents a credential; deployments grant LOGIN and a password out of band.
CREATE_ROLE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user NOLOGIN;
    END IF;
END
$$;

ALTER ROLE app_user NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOLOGIN;
"""

# Grants are deliberately on ALL tables in the schema rather than only the
# tenant-scoped ones: app_user is the runtime role for the whole application, so
# it needs to reach the global tables (users, tenants, permissions, ...) too.
# Reaching them is not the same as being isolated within them - which tables are
# policed is decided in 0002, and app_user can never widen that.
GRANT_PRIVILEGES = """
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;
"""

REVOKE_PRIVILEGES = """
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE USAGE, SELECT ON SEQUENCES FROM app_user;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM app_user;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM app_user;
REVOKE USAGE ON SCHEMA public FROM app_user;
"""


class Migration(migrations.Migration):
    # No model dependencies: this migration only creates functions, a role and
    # grants. It must run after the apps that own the tables exist so that
    # `ON ALL TABLES` can see them.
    dependencies = [
        ("identity", "0001_initial"),
        ("accounting", "0001_initial"),
        ("business_documents", "0001_initial"),
        ("document_intelligence", "0001_initial"),
        ("reporting", "0001_initial"),
    ]

    # These statements cannot run inside an atomic block: CREATE ROLE,
    # ALTER ROLE and GRANT/REVOKE on roles are not transactional in the sense
    # Django's atomic wrapper requires, and a failure halfway through a role
    # change leaves PostgreSQL refusing the whole transaction.
    atomic = False

    operations = [
        migrations.RunSQL(
            sql=CREATE_FUNCTIONS,
            reverse_sql=DROP_FUNCTIONS,
        ),
        migrations.RunSQL(
            sql=CREATE_ROLE,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=GRANT_PRIVILEGES,
            reverse_sql=REVOKE_PRIVILEGES,
        ),
    ]
