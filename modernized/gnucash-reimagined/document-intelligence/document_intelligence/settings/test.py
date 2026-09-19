"""Django settings for Document Intelligence (test environment)."""

from __future__ import annotations

from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105
ALLOWED_HOSTS = ["*"]

# Use a fast password hasher for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# In-memory SQLite is NOT used here because the project depends on PostgreSQL
# features (RLS, JSONB, UUID PKs). Tests require a local Postgres instance.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "fva_test",
        "USER": "fva_test",
        "PASSWORD": "fva_test",  # noqa: S106 — test-only credentials
        "HOST": "localhost",
        "PORT": "5432",
    }
}

# Use moto for S3 mocking in tests
DOCUMENT_INTELLIGENCE["S3_ENDPOINT_URL"] = None  # noqa: F405
DOCUMENT_INTELLIGENCE["S3_BUCKET"] = "fva-documents-test"  # noqa: F405
DOCUMENT_INTELLIGENCE["OCR_PROVIDER"] = "mock"  # noqa: F405
DOCUMENT_INTELLIGENCE["AI_SUGGESTIONS_ENABLED"] = False  # noqa: F405

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
