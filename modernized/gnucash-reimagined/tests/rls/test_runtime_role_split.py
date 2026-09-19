"""The runtime and deploy connections are two roles, and which one is which.

Every policy in this app is only worth the role that connects to it. A superuser
- and a role with ``BYPASSRLS`` - sees through row-level security even against a
table carrying ``FORCE ROW LEVEL SECURITY``, so a runtime connection naming
either has a complete, correct, entirely advisory boundary. The split is
therefore load-bearing, and these tests pin the properties that make it real
rather than nominal.

``config.settings.test`` is the one environment that cannot split the two: the
test runner creates and migrates the test database through the connection the
tests then run as. Development is checked in a subprocess instead, where
importing it cannot mutate the settings this suite is running under.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from config.settings.base import DEPLOY_DB_ALIAS, split_databases

PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: Everything about a connection that determines *which* database it reaches.
#: The two aliases must agree on all of these and differ only in credential.
LOCATION_KEYS = ("ENGINE", "NAME", "HOST", "PORT", "OPTIONS")

#: The keys that determine *who* is connecting.
CREDENTIAL_KEYS = ("USER", "PASSWORD")


def test_split_databases_returns_a_runtime_and_a_deploy_alias():
    runtime = {"ENGINE": "x", "NAME": "db", "USER": "app_user", "PASSWORD": "runtime"}
    databases = split_databases(runtime, {"USER": "owner", "PASSWORD": "owner"})

    assert set(databases) == {"default", DEPLOY_DB_ALIAS}
    assert DEPLOY_DB_ALIAS != "default", "the deploy alias must not be the runtime one"


def test_split_databases_varies_only_the_credential():
    """Both aliases reach the same database, so they cannot drift apart.

    A deploy alias pointing at a different host or database would be a silent
    misconfiguration: migrations would apply to one database and the
    application would read another.
    """
    runtime = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "gnucash_dev",
        "USER": "app_user",
        "PASSWORD": "app_user",
        "HOST": "localhost",
        "PORT": "5432",
        "OPTIONS": {"options": "-c search_path=public"},
    }
    databases = split_databases(runtime, {"USER": "postgres", "PASSWORD": "postgres"})

    for key in LOCATION_KEYS:
        assert databases["default"][key] == databases[DEPLOY_DB_ALIAS][key], key
    for key in CREDENTIAL_KEYS:
        assert databases["default"][key] != databases[DEPLOY_DB_ALIAS][key], key


def _development_settings():
    """Import ``config.settings.development`` in a subprocess and read it back.

    Importing it in-process would not be read-only: the module does
    ``INSTALLED_APPS += [...]`` against the very list object this suite's own
    settings still point at. A subprocess cannot touch this process's state.
    """
    script = (
        "import json;"
        "import config.settings.development as d;"
        "print(json.dumps({'databases': d.DATABASES, 'rls_enabled': d.RLS_ENABLED}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_development_runs_as_the_runtime_role_with_rls_enabled():
    """Development is RLS-enforced, and that needs both halves to be true.

    ``default`` connects as ``app_user``, which the policies bind but which owns
    nothing and cannot bypass. That only works with ``RLS_ENABLED`` on -
    otherwise the middleware issues no ``SET LOCAL`` and every tenant-scoped
    query returns nothing. And ``RLS_ENABLED`` on only works with ``default``
    bound by the policies; pointing it back at the owning role would make the
    flag meaningless.
    """
    config = _development_settings()
    databases = config["databases"]

    assert databases["default"]["USER"] == "app_user", (
        "development must run as the RLS-bound role, not the owning one"
    )
    assert config["rls_enabled"] is True, (
        "app_user with RLS_ENABLED off returns zero rows for every tenant query"
    )
    for key in CREDENTIAL_KEYS:
        assert databases["default"][key] != databases[DEPLOY_DB_ALIAS][key], (
            f"development shares its {key}; the two aliases are one credential"
        )
    for key in LOCATION_KEYS:
        assert databases["default"][key] == databases[DEPLOY_DB_ALIAS][key], key


@pytest.mark.django_db(transaction=True)
def test_the_bypass_warning_names_the_runtime_alias_and_the_way_out():
    """The check points at the runtime alias and names the deploy command.

    It carries ``Tags.database`` but inspects one alias on purpose: ``deploy``
    is *expected* to bypass, because FORCE ROW LEVEL SECURITY binds the table
    owner and nothing else can run the cross-tenant backfills. A per-alias
    check would report the correct configuration as a fault.
    """
    from django.core import checks
    from django.test import override_settings

    with override_settings(RLS_ENABLED=True):
        messages = [
            m for m in checks.run_checks(databases=["default"]) if m.id == "rls.W001"
        ]

    assert messages, "the suite's own superuser connection should trip this check"
    message = messages[0]
    # The alias it inspected: "default" is the runtime one.
    assert "'default'" in message.msg
    # And the command that uses the alias it deliberately left alone.
    assert DEPLOY_DB_ALIAS in message.hint
    assert f"--database={DEPLOY_DB_ALIAS}" in message.hint
