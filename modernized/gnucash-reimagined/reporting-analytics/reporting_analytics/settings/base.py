"""
Django settings for reporting_analytics — shared base configuration.

Secrets are NEVER read from literals here; every sensitive value is
resolved from the environment at process start via os.environ /
python-dotenv.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = False

ALLOWED_HOSTS: list[str] = []

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    # Local
    "reporting_analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Tenant isolation — sets the RLS session variable per request.
    # Defined in reporting_analytics.middleware; must run before any
    # tenant-scoped query.
    "reporting_analytics.middleware.TenantContextMiddleware",
]

ROOT_URLCONF = "reporting_analytics.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "reporting_analytics.wsgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL with RLS
# ---------------------------------------------------------------------------

# Parse DATABASE_URL into a Django DATABASES dict.
_default_db_url = os.environ.get(
    "DATABASE_URL", "postgres://postgres:postgres@localhost:5432/fva_reporting"
)


def _parse_db_url(url: str) -> dict:
    """Parse a postgres:// URL into a django.db.backends.postgresql dict."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
        # The app user must NOT be a superuser and must NOT have BYPASSRLS;
        # this is how RLS policies become enforceable (ADR-008).
        "OPTIONS": {
            "options": "-c statement_timeout=30000",
        },
    }


DATABASES = {"default": _parse_db_url(_default_db_url)}

# ---------------------------------------------------------------------------
# Caches / Celery
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
# Priority queues — report generation is `low`, AI explainer is `normal`,
# ad-hoc drilldown is `high` (small, synchronous-feeling).
CELERY_TASK_QUEUE_DEFAULT = "normal"
CELERY_TASK_ROUTES = {
    "reporting_analytics.tasks.generate_report": {"queue": "low"},
    "reporting_analytics.tasks.run_analytic_query": {"queue": "normal"},
    "reporting_analytics.tasks.refresh_dashboard_tile": {"queue": "normal"},
}

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

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
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "reporting_analytics.exceptions.api_exception_handler",
}

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Reporting & Analytics — service-specific configuration
# ---------------------------------------------------------------------------

# Accounting Engine — base URL and golden-manifest path.
ACCOUNTING_ENGINE_URL = os.environ.get(
    "ACCOUNTING_ENGINE_URL", "http://localhost:8000"
)
ACCOUNTING_ENGINE_GOLDEN_MANIFEST = os.environ.get(
    "ACCOUNTING_ENGINE_GOLDEN_MANIFEST",
    str(BASE_DIR.parent / "accounting-engine" / "manifests" / "golden.lock"),
)

# LLM provider (one of: stub, openai, anthropic).
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "stub")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))

# Object storage — for exported PDFs / CSVs / large report artifacts.
OBJECT_STORAGE_ENDPOINT = os.environ.get("OBJECT_STORAGE_ENDPOINT", "")
OBJECT_STORAGE_BUCKET = os.environ.get("OBJECT_STORAGE_BUCKET", "fva-reports")
OBJECT_STORAGE_ACCESS_KEY = os.environ.get("OBJECT_STORAGE_ACCESS_KEY", "")
OBJECT_STORAGE_SECRET_KEY = os.environ.get("OBJECT_STORAGE_SECRET_KEY", "")

# Default tenant slug for development only.
DEFAULT_TENANT_SLUG = os.environ.get("DEFAULT_TENANT_SLUG", "fva-sandbox")

# Maximum in-memory rows a synchronous report query may touch before we
# force it to the async generator. Keeps the API responsive.
REPORT_SYNC_ROW_LIMIT = int(os.environ.get("REPORT_SYNC_ROW_LIMIT", "50000"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "reporting_analytics": {"level": "INFO", "propagate": False},
        "django.db.backends": {"level": "WARNING", "propagate": False},
    },
}
