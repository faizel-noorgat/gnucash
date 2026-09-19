"""System checks for the RLS boundary.

The policies in this app are only worth the role that connects to them. A
superuser bypasses row-level security *even against a table with* ``FORCE ROW
LEVEL SECURITY`` set, and a role with ``BYPASSRLS`` does the same - so a
deployment whose runtime connection names either has a complete, correct,
entirely advisory set of policies and no isolation whatsoever.

This check inspects exactly one connection: the ``default`` alias, because that
is the runtime one. It is deliberately not a per-alias check even though it
carries ``Tags.database``. The ``deploy`` alias *is* expected to be able to
bypass - see ``split_databases`` in ``config/settings/base.py`` - because
FORCE ROW LEVEL SECURITY binds the table owner too, so nothing else can run the
cross-tenant backfills. Iterating every alias would report the correct
configuration as a fault, which is how a check gets switched off.

Severity is a **warning**, not an error. ``manage.py migrate`` runs system
checks, and a deployment that still has one privileged alias needs to be able
to run that command to reach the split. An error here would block the fix on
exactly the deployments that need it, and the condition it reports is a
deployment decision rather than a defect in the code being checked.
"""

from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.database)
def runtime_connection_can_bypass_rls(app_configs, **kwargs):
    """Warn when the runtime connection can see through every policy."""
    if not getattr(settings, "RLS_ENABLED", False):
        # RLS is off in this environment; there is nothing to bypass.
        return []

    from django.db import connection

    alias = connection.alias
    deploy_alias = getattr(settings, "DEPLOY_DB_ALIAS", "deploy")

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
            f"The runtime database connection (alias {alias!r}) is {reason} "
            f"(role {role!r}), so every row-level security policy is advisory "
            f"and tenant isolation is not enforced.",
            hint=(
                "Point the runtime connection at a role that owns nothing and "
                "has no BYPASSRLS - 'app_user', created by common/rls "
                "migrations. Deployments grant it LOGIN and a password out of "
                "band. Migrations still need an owning role, so the runtime "
                f"and deploy connections are separate DATABASES entries; the "
                f"{deploy_alias!r} alias carries the owning credential and only "
                f"'manage.py migrate --database={deploy_alias}' uses it."
            ),
            id="rls.W001",
        )
    ]
