"""
Test Configuration and Fixtures
"""
import pytest
from django.test import Client
from rest_framework.test import APIClient
from identity_access.domain.models import (
    User, Tenant, LegalEntity, Membership, Role, Permission,
    Practice, PracticeMembership, ClientEngagement, AdvisorAccessGrant
)


@pytest.fixture
def api_client():
    """Return DRF APIClient."""
    return APIClient()


@pytest.fixture
def user_factory(db):
    """Factory for creating test users."""
    def create_user(email='test@example.com', password='testpass123!', **kwargs):
        return User.objects.create_user(
            email=email,
            password=password,
            **kwargs
        )
    return create_user


@pytest.fixture
def user(user_factory):
    """Create a default test user."""
    return user_factory()


@pytest.fixture
def tenant_factory(db):
    """Factory for creating test tenants."""
    def create_tenant(name='Test Tenant', slug='test-tenant', created_by=None, **kwargs):
        return Tenant.objects.create(
            name=name,
            slug=slug,
            created_by=created_by,
            **kwargs
        )
    return create_tenant


@pytest.fixture
def tenant(tenant_factory, user):
    """Create a default test tenant."""
    return tenant_factory(created_by=user)


@pytest.fixture
def legal_entity_factory(db):
    """Factory for creating test legal entities."""
    def create_entity(tenant, name='Test Entity', created_by=None, **kwargs):
        return LegalEntity.objects.create(
            tenant=tenant,
            name=name,
            created_by=created_by,
            **kwargs
        )
    return create_entity


@pytest.fixture
def legal_entity(legal_entity_factory, tenant, user):
    """Create a default test legal entity."""
    return legal_entity_factory(tenant=tenant, created_by=user)


@pytest.fixture
def membership_factory(db):
    """Factory for creating test memberships."""
    def create_membership(user, tenant, role='admin', status='active', **kwargs):
        return Membership.objects.create(
            user=user,
            tenant=tenant,
            role=role,
            status=status,
            **kwargs
        )
    return create_membership


@pytest.fixture
def membership(membership_factory, user, tenant):
    """Create a default test membership."""
    return membership_factory(user=user, tenant=tenant)


@pytest.fixture
def role_factory(db):
    """Factory for creating test roles."""
    def create_role(name='Test Role', **kwargs):
        return Role.objects.create(name=name, **kwargs)
    return create_role


@pytest.fixture
def permission_factory(db):
    """Factory for creating test permissions."""
    def create_permission(codename='test_permission', **kwargs):
        return Permission.objects.create(
            codename=codename,
            name='Test Permission',
            **kwargs
        )
    return create_permission


@pytest.fixture
def practice_factory(db):
    """Factory for creating test practices."""
    def create_practice(name='Test Practice', slug='test-practice', created_by=None, **kwargs):
        return Practice.objects.create(
            name=name,
            slug=slug,
            created_by=created_by,
            **kwargs
        )
    return create_practice


@pytest.fixture
def practice(practice_factory, user):
    """Create a default test practice."""
    return practice_factory(created_by=user)


@pytest.fixture
def practice_membership_factory(db):
    """Factory for creating test practice memberships."""
    def create_membership(user, practice, role='staff', status='active', **kwargs):
        return PracticeMembership.objects.create(
            user=user,
            practice=practice,
            role=role,
            status=status,
            **kwargs
        )
    return create_membership


@pytest.fixture
def practice_membership(practice_membership_factory, user, practice):
    """Create a default test practice membership."""
    return practice_membership_factory(user=user, practice=practice)


@pytest.fixture
def client_engagement_factory(db):
    """Factory for creating test client engagements."""
    def create_engagement(practice, tenant, status='active', **kwargs):
        return ClientEngagement.objects.create(
            practice=practice,
            tenant=tenant,
            status=status,
            **kwargs
        )
    return create_engagement


@pytest.fixture
def client_engagement(client_engagement_factory, practice, tenant):
    """Create a default test client engagement."""
    return client_engagement_factory(practice=practice, tenant=tenant)


@pytest.fixture
def advisor_access_grant_factory(db, role_factory):
    """Factory for creating test advisor access grants."""
    def create_grant(engagement, practice_user, tenant_role=None, **kwargs):
        if tenant_role is None:
            tenant_role = role_factory(name='Accountant')
        return AdvisorAccessGrant.objects.create(
            engagement=engagement,
            practice_user=practice_user,
            tenant_role=tenant_role,
            **kwargs
        )
    return create_grant


@pytest.fixture
def authenticated_client(api_client, user):
    """Return authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client
