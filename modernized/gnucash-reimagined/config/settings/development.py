"""
Development settings for GnuCash Reimagined project.
"""

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Database - PostgreSQL for development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "gnucash_dev",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "5432",
        "OPTIONS": {
            "options": "-c search_path=public",
        },
    }
}

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

# Disable RLS in development for easier debugging
# Set to True to test RLS policies
RLS_ENABLED = False  # noqa: F405
