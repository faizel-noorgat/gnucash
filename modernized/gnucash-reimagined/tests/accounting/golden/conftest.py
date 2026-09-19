"""
Pytest configuration for accounting engine tests.
"""

import pytest
from django.test import TestCase


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    from tests.accounting.golden.factories import TenantFactory
    return TenantFactory()


@pytest.fixture
def legal_entity(tenant):
    """Create a test legal entity."""
    from tests.accounting.golden.factories import LegalEntityFactory
    return LegalEntityFactory(tenant=tenant)


@pytest.fixture
def currency(tenant):
    """Create a test currency."""
    from tests.accounting.golden.factories import CommodityFactory
    return CommodityFactory(tenant=tenant, mnemonic="USD", fraction=100)


@pytest.fixture
def user(db):
    """Create a test user."""
    from tests.accounting.golden.factories import UserFactory
    return UserFactory()
