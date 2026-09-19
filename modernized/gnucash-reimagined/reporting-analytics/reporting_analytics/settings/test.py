"""Test settings — fast, deterministic, no external I/O."""

from .base import *  # noqa: F401,F403

# A throw-away secret; tests do not serve network traffic.
SECRET_KEY = "test-not-a-real-secret-do-not-use-in-production"

DEBUG = False
ALLOWED_HOSTS = ["*"]

# Use an in-memory SQLite database for unit tests that do NOT exercise
# RLS. Tests that exercise RLS must use the pytest `postgres` marker and
# are skipped unless a real Postgres URL is provided via TEST_DATABASE_URL.
import os

if os.environ.get("TEST_DATABASE_URL"):
    from urllib.parse import urlparse

    _url = urlparse(os.environ["TEST_DATABASE_URL"])
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _url.path.lstrip("/"),
            "USER": _url.username or "",
            "PASSWORD": _url.password or "",
            "HOST": _url.hostname or "localhost",
            "PORT": str(_url.port or 5432),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# Use the fast (insecure) password hasher in tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Celery runs synchronously in tests.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Force LLM provider to 'stub' unless a test explicitly overrides.
LLM_PROVIDER = os.environ.get("TEST_LLM_PROVIDER", "stub")
LLM_API_KEY = ""
LLM_MODEL = ""

# Disable RLS middleware in unit tests (we do not have a real Postgres
# session to SET LOCAL on). Acceptance tests that exercise RLS are
# marked with pytest.mark.rls and run against the postgres fixture.
MIDDLEWARE = [
    m
    for m in MIDDLEWARE  # noqa: F405
    if m != "reporting_analytics.middleware.TenantContextMiddleware"
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The golden-manifest path used by the dependency gate in tests.
ACCOUNTING_ENGINE_GOLDEN_MANIFEST = os.environ.get(
    "TEST_ACCOUNTING_ENGINE_GOLDEN_MANIFEST",
    "/tmp/fva-test-fixtures/accounting-engine/manifests/golden.lock",
)
