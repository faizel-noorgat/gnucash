"""Django settings for Document Intelligence (base)."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.postgres",
    "rest_framework",
    "django_filters",
    "document_intelligence",
]

MIDDLEWARE = [
    "document_intelligence.middleware.TenantContextMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "document_intelligence.urls"
WSGI_APPLICATION = "document_intelligence.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "fva"),
        "USER": os.environ.get("DB_USER", "fva_app"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {
            "options": "-c search_path=public",
        },
        "TEST": {
            "NAME": "fva_test",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.UUIDField"

USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
}

# Celery
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_ROUTES = {
    "document_intelligence.tasks.ocr.*": {"queue": "ocr_critical"},
    "document_intelligence.tasks.extraction.*": {"queue": "ocr_critical"},
    "document_intelligence.tasks.matching.*": {"queue": "normal"},
    "document_intelligence.tasks.notifications.*": {"queue": "low"},
}

# Document Intelligence-specific settings
DOCUMENT_INTELLIGENCE = {
    # Object storage
    "S3_BUCKET": os.environ.get("DOC_STORAGE_BUCKET", "fva-documents-dev"),
    "S3_REGION": os.environ.get("AWS_REGION", "ap-southeast-1"),
    "S3_ENDPOINT_URL": os.environ.get("S3_ENDPOINT_URL"),  # for MinIO in dev
    # OCR
    "OCR_PROVIDER": os.environ.get("OCR_PROVIDER", "aws_textract"),
    "OCR_CONFIDENCE_THRESHOLD": float(os.environ.get("OCR_CONFIDENCE_THRESHOLD", "0.75")),
    # AI suggestions
    "AI_SUGGESTIONS_ENABLED": os.environ.get("AI_SUGGESTIONS_ENABLED", "True").lower() == "true",
    "LLM_PROVIDER": os.environ.get("LLM_PROVIDER", "openai"),
    "AI_CONFIDENCE_THRESHOLD": float(os.environ.get("AI_CONFIDENCE_THRESHOLD", "0.80")),
    # Duplicate detection
    "DUPLICATE_INVOICE_WINDOW_DAYS": int(os.environ.get("DUPLICATE_INVOICE_WINDOW_DAYS", "90")),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "document_intelligence": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
