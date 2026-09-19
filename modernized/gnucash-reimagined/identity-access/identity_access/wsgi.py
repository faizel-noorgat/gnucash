"""
WSGI config for Identity & Access Service.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'identity_access.settings.production')

application = get_wsgi_application()
