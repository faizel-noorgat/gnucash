"""
Development settings for Identity & Access Service.
"""

from .base import *

DEBUG = True

# Development-specific apps
INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = [
    '127.0.0.1',
]

# Database - use SQLite for faster development tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Cache - use local memory for development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Email - use console backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS - allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Logging - more verbose in development
LOGGING['loggers']['identity_access']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'

# Security - relax for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# JWT - longer lifetime for development
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = 1440  # 24 hours
JWT_REFRESH_TOKEN_LIFETIME_DAYS = 30

# Disable RLS in development (unless explicitly testing)
MULTI_TENANCY['RLS_ENABLED'] = os.environ.get('ENABLE_RLS_IN_DEV', 'False').lower() == 'true'
