"""
Fixtures for the Identity & Access bounded context.

Moved here from tests/conftest.py when the suite was reorganized into
per-context directories, so that these names cannot shadow fixtures of the
same name defined by another context.
"""

import pytest


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
def user(db):
    """Create a test user.

    A User is platform-level and is NOT directly tenant-scoped - membership of a
    tenant is expressed through the Membership model. An earlier version of this
    fixture passed `tenant=` to create_user, which raised TypeError because User
    has no such field.
    """
    from apps.identity.models import User

    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
