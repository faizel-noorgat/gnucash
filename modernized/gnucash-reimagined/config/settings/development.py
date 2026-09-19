"""
Development settings for GnuCash Reimagined project.
"""

import os

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Database - PostgreSQL for development, split into a runtime role and an
# owning role. See ``split_databases`` in base.py for why there are two.
#
# ``DB_PASSWORD`` defaults to the development password so a fresh checkout
# connects without ceremony; a real deployment sets it. The runtime role is
# ``app_user``, created by the RLS migrations with LOGIN granted out of band -
# see README.md, "Runtime and deploy database roles".
_RUNTIME_DB = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("DB_NAME", "gnucash_dev"),
    "USER": os.environ.get("DB_USER", "app_user"),
    "PASSWORD": os.environ.get("DB_PASSWORD", "app_user"),
    "HOST": os.environ.get("DB_HOST", "localhost"),
    "PORT": os.environ.get("DB_PORT", "5432"),
    "OPTIONS": {
        "options": "-c search_path=public",
    },
}

DATABASES = split_databases(  # noqa: F405
    _RUNTIME_DB,
    {
        "USER": os.environ.get("DB_OWNER_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_OWNER_PASSWORD", "postgres"),
    },
)

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Django Debug Toolbar
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
INTERNAL_IPS = ["127.0.0.1", "localhost"]

# CORS settings for development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Use mock providers for development
DOCUMENT_INTELLIGENCE["OCR_PROVIDER"] = "mock"  # noqa: F405
DOCUMENT_INTELLIGENCE["AI_PROVIDER"] = "mock"  # noqa: F405

# Simplified logging for development
LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405

# RLS is on in development, and it has to be: `default` connects as `app_user`,
# which the policies bind. With context propagation switched off the middleware
# issues no SET LOCAL, so every tenant-scoped query in development would return
# zero rows - a confusing failure that looks like missing data rather than a
# switched-off boundary.
#
# Turning it on is also the point of the split. Development is where a missing
# or wrong tenant context should show up, not production. Migrations are the
# one thing that can no longer be run on `default`:
#
#     python manage.py migrate --database=deploy
RLS_ENABLED = True  # noqa: F405
