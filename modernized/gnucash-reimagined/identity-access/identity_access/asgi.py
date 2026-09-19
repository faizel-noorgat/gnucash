"""
ASGI config for Identity & Access Service.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'identity_access.settings.production')

application = get_asgi_application()
