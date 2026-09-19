"""
Pytest configuration for business documents tests
"""
import pytest
import django
from django.conf import settings


def pytest_configure(config):
    """Configure Django settings for pytest"""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'rest_framework',
                'business_documents',
            ],
            REST_FRAMEWORK={
                'DEFAULT_AUTHENTICATION_CLASSES': [
                    'rest_framework.authentication.SessionAuthentication',
                ],
                'DEFAULT_PERMISSION_CLASSES': [
                    'rest_framework.permissions.IsAuthenticated',
                ],
            },
            SECRET_KEY='test-secret-key',
            USE_TZ=True,
        )
        django.setup()


@pytest.fixture
def api_client():
    """Provide API client for tests"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def tenant():
    """Provide a test tenant"""
    from business_documents.tests.factories import TenantFactory
    return TenantFactory()


@pytest.fixture
def legal_entity(tenant):
    """Provide a test legal entity"""
    from business_documents.tests.factories import LegalEntityFactory
    return LegalEntityFactory(tenant=tenant)


@pytest.fixture
def user():
    """Provide a test user"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username='testuser', password='testpass')
