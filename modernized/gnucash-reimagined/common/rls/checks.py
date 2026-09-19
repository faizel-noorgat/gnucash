"""System checks for the RLS boundary.

The policies in this app are only worth the role that connects to them. A
superuser bypasses row-level security *even against a table with* ``FORCE ROW
LEVEL SECURITY`` set, and a role with ``BYPASSRLS`` does the same - so a
deployment that connects as either has a complete, correct, entirely advisory
set of policies and no isolation whatsoever. That is not a hypothetical: this
project's own settings point every environment at the ``postgres`` superuser,
because the runtime connection and the migration connection are the same
``DATABASES['default']`` entry.

Checking it in code rather than in a comment means the gap is reported by
``manage.py check``, which every deployment already runs, instead of being
rediscovered by whoever next reads the settings file.

Severity is a **warning**, not an error, on purpose. Migrations genuinely do
need the owning role - they create the policies - and with a single
``DATABASES['default']`` the deploy connection is the same one. An error here
would block ``manage.py migrate`` on exactly the deployments that need to run
it. The fix is to split the two connections, which is a deployment decision,
not something a check should force.
"""

from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.database)
def runtime_connection_can_bypass_rls(app_configs, **kwargs):
    """Warn when the configured connection can see through every policy."""
    if not getattr(settings, "RLS_ENABLED", False):
        # RLS is off in this environment; there is nothing to bypass.
        return []

    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT current_user, r.rolsuper, r.rolbypassrls
                FROM pg_roles r WHERE r.rolname = current_user
                """
            )
            row = cursor.fetchone()
    except Exception:
        # No database, or no permission to read pg_roles. Neither is this
        # check's business, and neither should turn into a startup failure.
        return []

    if row is None:
        return []

    role, is_superuser, bypasses_rls = row
    if not (is_superuser or bypasses_rls):
        return []

    reason = "a superuser" if is_superuser else "granted BYPASSRLS"
    return [
        Warning(
            f"The database connection for this environment is {reason} "
            f"(role {role!r}), so every row-level security policy is advisory "
            f"and tenant isolation is not enforced.",
            hint=(
                "Point the runtime connection at a role that owns nothing and "
                "has no BYPASSRLS - 'app_user', created by common/rls "
                "migrations. Deployments grant it LOGIN and a password out of "
                "band. Migrations still need an owning role, so the runtime "
                "and deploy connections have to be separate DATABASES entries."
            ),
            id="rls.W001",
        )
    ]
