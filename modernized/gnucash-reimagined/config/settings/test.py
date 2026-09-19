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
