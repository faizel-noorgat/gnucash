from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date

import pytest
from django.test import Client
from model_bakery import baker

from accounts.models import Account, AccountType
from accounts.services import get_account_register
from transactions.models import Split, Transaction


@pytest.fixture
def asset_account(tenant, commodity):
    return baker.make(
        Account, tenant=tenant, account_type=AccountType.ASSET,
        name='Checking', commodity=commodity, full_name='Assets:Checking',
    )


@pytest.fixture
def expense_account(tenant, commodity):
    return baker.make(
        Account, tenant=tenant, account_type=AccountType.EXPENSE,
        name='Groceries', commodity=commodity, full_name='Expenses:Groceries',
    )


@pytest.fixture
def transaction(tenant, user, commodity):
    return baker.make(
        Transaction, tenant=tenant, post_date=date(2025, 3, 15),
        description='Grocery store', currency=commodity, created_by=user,
    )


@pytest.fixture
def split_out(asset_account, tenant, transaction):
    return baker.make(
        Split, account=asset_account, tenant=tenant,
        transaction=transaction, value=Decimal('-50.00'),
        reconcile_state=Split.ReconcileState.NONE,
    )


@pytest.fixture
def split_in(expense_account, tenant, transaction):
    return baker.make(
        Split, account=expense_account, tenant=tenant,
        transaction=transaction, value=Decimal('50.00'),
        reconcile_state=Split.ReconcileState.CLEARED,
    )


@pytest.mark.django_db
class TestAccountRegisterService:
    def test_single_transaction_split(self, asset_account, transaction, split_out, expense_account):
        result = get_account_register(asset_account)
        assert len(result['transactions']) == 1
        entry = result['transactions'][0]
        assert entry['description'] == 'Grocery store'
        assert entry['split_value'] == '-50.00'
        assert 'Expenses:Groceries' in entry['other_accounts']
        assert result['running_balance'] == '-50.00'

    def test_running_balance_accumulates(self, asset_account, tenant, commodity, user):
        tx1 = baker.make(Transaction, tenant=tenant, post_date=date(2025, 1, 1),
                         description='Deposit', currency=commodity, created_by=user)
        tx2 = baker.make(Transaction, tenant=tenant, post_date=date(2025, 1, 5),
                         description='Withdrawal', currency=commodity, created_by=user)
        baker.make(Split, account=asset_account, tenant=tenant, transaction=tx1,
                   value=Decimal('100.00'))
        baker.make(Split, account=asset_account, tenant=tenant, transaction=tx2,
                   value=Decimal('-30.00'))

        result = get_account_register(asset_account)
        assert result['running_balance'] == '70.00'

    def test_date_filter_excludes_out_of_range(self, asset_account, tenant, commodity, user):
        tx_early = baker.make(Transaction, tenant=tenant, post_date=date(2025, 1, 1),
                              description='Early', currency=commodity, created_by=user)
        tx_late = baker.make(Transaction, tenant=tenant, post_date=date(2025, 6, 1),
                             description='Late', currency=commodity, created_by=user)
        baker.make(Split, account=asset_account, tenant=tenant, transaction=tx_early,
                   value=Decimal('10.00'))
        baker.make(Split, account=asset_account, tenant=tenant, transaction=tx_late,
                   value=Decimal('20.00'))

        result = get_account_register(asset_account, start_date='2025-02-01')
        assert len(result['transactions']) == 1
        assert result['transactions'][0]['description'] == 'Late'

    def test_empty_account(self, asset_account):
        result = get_account_register(asset_account)
        assert result['transactions'] == []
        assert result['running_balance'] == '0'


@pytest.mark.django_db
class TestAccountRegisterEndpoint:
    def test_register_returns_entries(self, api_client, asset_account, transaction, split_out, expense_account):
        api_client.force_authenticate(user=transaction.created_by)
        response = api_client.get(f'/api/v1/accounts/{asset_account.id}/register/')
        assert response.status_code == 200
        assert response.data['account']['id'] == str(asset_account.id)
        assert len(response.data['transactions']) == 1

    def test_register_date_filter(self, api_client, asset_account, tenant, commodity, user):
        tx1 = baker.make(Transaction, tenant=tenant, post_date=date(2025, 1, 1),
                         description='Jan', currency=commodity, created_by=user)
        tx2 = baker.make(Transaction, tenant=tenant, post_date=date(2025, 6, 1),
                         description='Jun', currency=commodity, created_by=user)
        baker.make(Split, account=asset_account, tenant=tenant, transaction=tx1,
                   value=Decimal('10.00'))
        baker.make(Split, account=asset_account, tenant=tenant, transaction=tx2,
                   value=Decimal('20.00'))
        api_client.force_authenticate(user=user)
        response = api_client.get(
            f'/api/v1/accounts/{asset_account.id}/register/',
            {'start_date': '2025-03-01'},
        )
        assert response.status_code == 200
        assert len(response.data['transactions']) == 1
        assert response.data['transactions'][0]['description'] == 'Jun'

    def test_register_tenant_isolation(self, api_client, asset_account, other_tenant, commodity, user):
        """A user in a different tenant cannot see this account's register."""
        other_account = baker.make(
            Account, tenant=other_tenant, account_type=AccountType.EXPENSE,
            name='Other', commodity=commodity,
        )
        tx = baker.make(Transaction, tenant=other_tenant, post_date=date(2025, 1, 1),
                        description='Other tx', currency=commodity, created_by=user)
        baker.make(Split, account=other_account, tenant=other_tenant, transaction=tx,
                   value=Decimal('99.00'))

        api_client.force_authenticate(user=user)
        response = api_client.get(f'/api/v1/accounts/{asset_account.id}/register/')
        assert response.status_code == 200
        assert len(response.data['transactions']) == 0  # no splits in asset_account's tenant
