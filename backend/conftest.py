from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user(db):
    return baker.make(User, email='test@example.com', password='testpass123')


@pytest.fixture
def tenant(db):
    return baker.make('tenants.Tenant', name='Test Tenant', slug='test-tenant')


@pytest.fixture
def membership(db, user, tenant):
    return baker.make(
        'tenants.TenantMembership',
        user=user,
        tenant=tenant,
        role='OWNER',
    )


@pytest.fixture
def api_client(db):
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user, tenant, membership):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}',
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    return api_client
