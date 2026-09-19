"""
Test settings for GnuCash Reimagined project.
"""

from .base import *  # noqa: F403

DEBUG = False

# Use faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Database - use PostgreSQL for tests (RLS requires PostgreSQL)
# Tests will be marked as skipped if PostgreSQL is not available
#
# One alias, and `postgres` - unlike every other environment. That is a Django
# constraint, not a preference. The test runner creates *and* migrates the test
# database through the ``default`` connection, so the role that runs migrations
# is the role the tests then run as; there is no way to migrate as the owner and
# query as the runtime role. ``test_db_signature()`` compounds it by excluding
# USER, so a second alias with different credentials collapses into the same
# test database as a mirror rather than giving the tests a second identity.
# (django/test/utils.py, django/db/backends/base/creation.py.)
#
# So the RLS suite assumes the runtime role itself, per test, with
# ``SET LOCAL ROLE app_user`` inside the transaction under test - see
# tests/rls/conftest.py. Within that block the session is subject to the
# policies exactly as a real ``app_user`` connection is, which is what every
# isolation assertion rests on. The consequence to remember is the inverse:
# a test that does *not* enter ``rls_session()`` or ``app_role()`` runs as a
# superuser and cannot detect a missing tenant context.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "gnucash_test",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "5432",
        "TEST": {
            "NAME": "gnucash_test",
            "CREATE_DB": True,
        },
    }
}

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Celery - use synchronous execution for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use mock providers for tests
DOCUMENT_INTELLIGENCE["OCR_PROVIDER"] = "mock"  # noqa: F405
DOCUMENT_INTELLIGENCE["AI_PROVIDER"] = "mock"  # noqa: F405

# RLS - disabled for most unit tests, enabled for RLS-specific tests
# RLS-specific tests should override this setting
RLS_ENABLED = False  # noqa: F405

# Disable logging during tests
LOGGING = {}  # noqa: F405

# Faster authentication for tests
AUTH_PASSWORD_VALIDATORS = []

# Simplified middleware for tests
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # Tenant context middleware is tested separately in RLS tests
]
