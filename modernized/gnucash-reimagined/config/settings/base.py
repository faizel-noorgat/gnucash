"""
Base Django settings for GnuCash Reimagined project.

This module contains settings common to all environments.
Environment-specific settings should import from this module and override as needed.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# This should be overridden in environment-specific settings
SECRET_KEY = "django-insecure-change-me-in-production"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS: list[str] = []

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "drf_spectacular",
]

# Bounded context apps (order matters for dependencies)
LOCAL_APPS = [
    # Owns no models of its own - it carries the RLS migrations (helper
    # functions, the app_user role and the per-table policies) so that a clean
    # deployment receives them from the migration graph.
    "common.rls",
    "apps.identity",
    "apps.accounting",
    "apps.business_documents",
    "apps.document_intelligence",
    "apps.reporting",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Tenant context middleware (RLS)
    "common.middleware.tenant.TenantContextMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# This should be overridden in environment-specific settings
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# The application uses two credentials against one database, and which one a
# connection uses is the difference between an enforced boundary and a
# decorative one.
#
# ``default`` is the *runtime* connection. Every query the web and Celery
# processes issue goes through it, so it has to name a role that row-level
# security actually binds. A superuser - and a role with ``BYPASSRLS`` - sees
# through every policy, FORCEd or not, which leaves the 51 policed tables with
# correct, reviewed, thoroughly tested policies that nothing enforces. That was
# true of every environment here until the two connections were split.
#
# ``deploy`` is the *owning* connection, and only ``manage.py migrate
# --database=deploy`` may use it. Migrations write rows across tenant
# boundaries - the tenant backfills in ``apps/*/migrations`` set a child's
# ``tenant_id`` from its parent with no tenant context at all - and FORCE ROW
# LEVEL SECURITY binds the table owner too, so a role the policies apply to
# cannot perform them. It would not fail: it would update zero rows, in
# silence. The owning role is the one thing that can bypass, so it is kept off
# the request path entirely and reached only by an explicit operator command.
#
# ``app_user`` is NOLOGIN as created by ``common/rls/migrations/0001``, because
# a provisioning migration must never invent a credential. Grant it LOGIN and a
# password once, after the first migration - the role does not exist before
# then, and that migration re-asserts only the attributes that make the role
# safe to connect as, not LOGIN. The grant survives later migrations and test
# runs. See README.md, "Runtime and deploy database roles".
DEPLOY_DB_ALIAS = "deploy"


def split_databases(runtime, owner_credentials):
    """Return ``DATABASES`` with a runtime alias and an owning deploy alias.

    Both aliases address the same database: engine, host, port, name and
    options are all taken from ``runtime``, so the two cannot drift into
    pointing at different servers. Only the credential differs, which is the
    entire point. ``owner_credentials`` supplies just the keys that change -
    normally ``USER`` and ``PASSWORD``.
    """
    return {
        "default": runtime,
        DEPLOY_DB_ALIAS: {**runtime, **owner_credentials},
    }

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Custom user model
AUTH_USER_MODEL = "identity.User"

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Enforce tenant context in all API requests.
    # NOTE: this key was previously declared twice in this same dict literal, so
    # the single-entry version above was dead code that Python silently
    # discarded. Kept only the two-entry list, which is the intended policy.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "apps.identity.permissions.TenantScopedPermission",
    ],
}

# DRF Spectacular (OpenAPI schema generation)
SPECTACULAR_SETTINGS = {
    "TITLE": "GnuCash Reimagined API",
    "DESCRIPTION": "Modern multi-tenant cloud accounting SaaS platform",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Celery Configuration
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Multi-tenancy configuration
TENANT_HEADER = "HTTP_X_TENANT_ID"
TENANT_SESSION_KEY = "tenant_id"

# Row Level Security (RLS) configuration
RLS_ENABLED = True
RLS_TENANT_COLUMN = "tenant_id"
RLS_ENTITY_COLUMN = "legal_entity_id"  # Optional: for entity-scoped isolation

# Accounting configuration
ACCOUNTING = {
    # Default rounding mode for monetary calculations
    "ROUNDING_MODE": "ROUND_HALF_UP",
    # Maximum decimal places for monetary values
    "MAX_DECIMAL_PLACES": 10,
    # Default currency (ISO 4217)
    "DEFAULT_CURRENCY": "USD",
    # Enable trading accounts for multi-currency balancing
    "USE_TRADING_ACCOUNTS": True,
    # Mark trading accounts as system accounts (hidden from users)
    "HIDE_TRADING_ACCOUNTS": True,
}

# Document Intelligence configuration
DOCUMENT_INTELLIGENCE = {
    # OCR service provider: "aws_textract" | "google_documentai" | "mock"
    "OCR_PROVIDER": "mock",
    # AI/LLM provider for suggestions: "openai" | "anthropic" | "mock"
    "AI_PROVIDER": "mock",
    # Maximum file size for document uploads (in bytes)
    "MAX_UPLOAD_SIZE": 10 * 1024 * 1024,  # 10 MB
    # Allowed MIME types for document uploads
    "ALLOWED_MIME_TYPES": [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
    ],
}

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
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
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
