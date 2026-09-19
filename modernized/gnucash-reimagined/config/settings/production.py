"""
Production settings for GnuCash Reimagined project.
"""

import environ

from .base import *  # noqa: F403

# Environment variable parsing
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    SECRET_KEY=(str, ""),
    DATABASE_URL=(str, "postgres://postgres:postgres@localhost:5432/gnucash_prod"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
)

# Read .env file if it exists
environ.Env.read_env(BASE_DIR / ".env")  # noqa: F405

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Database - PostgreSQL for production
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# Redis/Celery configuration
CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = env("REDIS_URL")

# Multi-tenancy - RLS enabled in production
RLS_ENABLED = True  # noqa: F405

# Document Intelligence - use real providers in production
# Configure via environment variables
DOCUMENT_INTELLIGENCE["OCR_PROVIDER"] = env("OCR_PROVIDER", default="aws_textract")  # noqa: F405
DOCUMENT_INTELLIGENCE["AI_PROVIDER"] = env("AI_PROVIDER", default="openai")  # noqa: F405

# Static files
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Logging - production logging configuration
LOGGING = {  # noqa: F405
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
