from __future__ import annotations

import pytest
from decimal import Decimal
from model_bakery import baker
from rest_framework import status


@pytest.mark.django_db
class TestDoubleEntryInvariant:
    def _transaction_payload(self, tenant, splits):
        account1 = baker.make('accounts.Account', tenant=tenant, account_type='ASSET')
        account2 = baker.make('accounts.Account', tenant=tenant, account_type='EXPENSE')
        commodity = baker.make('accounts.Commodity', mnemonic='USD', namespace='CURRENCY')
        return {
            'currency': str(commodity.id),
            'post_date': '2026-04-17',
            'description': 'Test transaction',
            'splits_data': [
                {'account': str(account1.id), 'value': s[0], 'quantity': s[1]}
                for s in splits
            ],
        }

    def test_splits_must_sum_to_zero_rejects_unbalanced(self, authenticated_client, tenant):
        response = authenticated_client.post(
            '/api/v1/transactions/',
            self._transaction_payload(tenant, [('100.00', '100.00'), ('50.00', '50.00')]),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'must sum to zero' in str(response.data).lower()

    def test_splits_must_sum_to_zero_accepts_balanced(self, authenticated_client, tenant):
        response = authenticated_client.post(
            '/api/v1/transactions/',
            self._transaction_payload(tenant, [('100.00', '100.00'), ('-100.00', '-100.00')]),
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data['splits']) == 2

    def test_minimum_two_splits_required(self, authenticated_client, tenant):
        response = authenticated_client.post(
            '/api/v1/transactions/',
            self._transaction_payload(tenant, [('100.00', '100.00')]),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'at least 2 splits' in str(response.data).lower()
