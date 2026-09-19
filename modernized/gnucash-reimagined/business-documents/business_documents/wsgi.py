"""
WSGI config for business documents service
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'business_documents.settings.development')

application = get_wsgi_application()
