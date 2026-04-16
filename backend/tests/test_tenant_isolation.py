from __future__ import annotations

import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
class TestTenantIsolation:
    def test_user_cannot_see_other_tenant_accounts(self, authenticated_client, tenant):
        other_tenant = baker.make('tenants.Tenant', name='Other', slug='other')
        baker.make('accounts.Account', tenant=other_tenant, name='Secret Account', account_type='ASSET')

        response = authenticated_client.get('/api/v1/accounts/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_user_cannot_create_in_other_tenant(self, authenticated_client, tenant):
        other_tenant = baker.make('tenants.Tenant', name='Other', slug='other')
        commodity = baker.make('accounts.Commodity', mnemonic='USD', namespace='CURRENCY')

        response = authenticated_client.post('/api/v1/accounts/', {
            'tenant': str(other_tenant.id),
            'name': 'Hijacked Account',
            'account_type': 'ASSET',
            'commodity': str(commodity.id),
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert str(response.data['tenant']) == str(tenant.id)

    def test_unauthenticated_user_rejected(self, api_client):
        response = api_client.get('/api/v1/accounts/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_without_tenant_membership_cannot_access(self, api_client, user, tenant):
        refresh = RefreshToken.for_user(user)
        # Create a different tenant that the user has no membership in
        other_tenant = baker.make('tenants.Tenant', name='Other', slug='no-access')
        api_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}',
            HTTP_X_TENANT_ID=str(other_tenant.id),
        )

        response = api_client.get('/api/v1/accounts/')
        # The middleware sets request.tenant from header, but user has no membership
        # View filters by request.tenant — returns empty
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
