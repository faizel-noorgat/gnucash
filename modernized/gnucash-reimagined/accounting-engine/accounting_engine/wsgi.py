"""WSGI config for accounting-engine project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accounting_engine.settings")

application = get_wsgi_application()
