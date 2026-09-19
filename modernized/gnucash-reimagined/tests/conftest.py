"""
Test configuration for GnuCash Reimagined.
"""

import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Configure database for tests."""
    from django.conf import settings

    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "gnucash_test",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "5432",
    }


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    from apps.identity.models import Tenant

    return Tenant.objects.create(
        name="Test Tenant",
        slug="test-tenant",
    )


@pytest.fixture
def legal_entity(tenant):
    """Create a test legal entity."""
    from apps.identity.models import LegalEntity

    return LegalEntity.objects.create(
        tenant=tenant,
        name="Test Entity",
        base_currency="USD",
    )


@pytest.fixture
def user(tenant):
    """Create a test user."""
    from apps.identity.models import User

    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        tenant=tenant,
    )
