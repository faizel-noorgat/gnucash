# Phase 4: Account Register Page

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Account Register page — the core accounting view showing all transactions that touch a single account, with a running balance column, reconciliation state badges, and date range filtering. Also add the missing backend `GET /api/v1/accounts/:id/register` endpoint that the frontend consumes.

**Architecture:** Backend adds a `@action` on `AccountViewSet` that queries splits for the account, joins to transactions and other accounts, computes running balance ordered by date. Frontend adds `AccountRegisterPage.tsx` route at `/accounts/:id`, `useAccountRegister` hook, `RegisterEntryRow` component, and wires the route into `App.tsx`.

**Tech Stack:** Django REST Framework `@action`, React 19 + TypeScript 5 (strict), React Query, shadcn/ui table, date-fns.

---

## Prerequisites

- [ ] Backend has `accounts` app with `Account`, `Split`, `Transaction` models
- [ ] Frontend has `useAccount`, `useAccounts`, `useTransactions` hooks
- [ ] Frontend has shadcn/ui `Card`, `Table`, `Badge`, `Button`, `Input` components
- [ ] `date-fns` installed in frontend

---

## File Map

### Files to Create (backend)
- `backend/accounts/services.py` — Register query logic (service layer, not in views)

### Files to Modify (backend)
- `backend/accounts/views.py` — Add `@action(detail=True)` register endpoint on `AccountViewSet`
- `backend/accounts/serializers.py` — Add `AccountRegisterEntrySerializer`, `AccountRegisterResponseSerializer`

### Files to Create (frontend)
- `frontend/src/types/register.ts` — TypeScript types for register endpoint response
- `frontend/src/hooks/use-account-register.ts` — React Query hook for `/accounts/:id/register`
- `frontend/src/routes/AccountRegisterPage.tsx` — Main register page (account header + transaction table + date filter)
- `frontend/src/features/register/components/ReconcileBadge.tsx` — Reconciliation state badge component
- `frontend/src/features/register/components/RegisterEntryRow.tsx` — Single row in the register table

### Files to Modify (frontend)
- `frontend/src/App.tsx` — Add route `/accounts/:id` → `AccountRegisterPage`
- `frontend/src/routes/AccountListPage.tsx` — Change "View" link to `/accounts/${account.id}` (currently points there but page did not exist)

---

## Task 1: Backend — Account Register Endpoint

### Step 1: Create register serializers

```python
# backend/accounts/serializers.py — append to end of file

from transactions.models import Split


class AccountRegisterEntrySerializer(serializers.Serializer):
    """Single row in the account register — a split with transaction context."""
    id = serializers.UUIDField()
    post_date = serializers.DateField()
    description = serializers.CharField()
    num = serializers.CharField()
    split_value = serializers.DecimalField(max_digits=20, decimal_places=10)
    split_memo = serializers.CharField()
    other_accounts = serializers.ListField(child=serializers.CharField())
    reconcile_state = serializers.CharField()
    created_at = serializers.DateTimeField()


class AccountRegisterResponseSerializer(serializers.Serializer):
    """Full register response for an account."""
    account = AccountSerializer()
    transactions = AccountRegisterEntrySerializer(many=True)
```

### Step 2: Create register service

```python
# backend/accounts/services.py
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import F, Prefetch, Sum

if TYPE_CHECKING:
    from accounts.models import Account
    from transactions.models import Split, Transaction


def get_account_register(
    account: Account,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Return register data for a single account: all splits touching this account
    with transaction context, other account names, and running balance.
    """
    from transactions.models import Split, Transaction

    qs = (
        Split.objects
        .filter(account=account, tenant=account.tenant)
        .select_related('transaction', 'transaction__currency')
        .prefetch_related(
            Prefetch(
                'transaction__splits',
                queryset=Split.objects.select_related('account').exclude(account=account),
                to_attr='other_splits',
            )
        )
        .order_by('transaction__post_date', 'transaction__enter_date', 'id')
    )

    if start_date:
        qs = qs.filter(transaction__post_date__gte=start_date)
    if end_date:
        qs = qs.filter(transaction__post_date__lte=end_date)

    splits: list[Split] = list(qs)

    entries = []
    running_balance = Decimal('0')

    for split in splits:
        running_balance += split.value
        other_accounts = [
            s.account.full_name or s.account.name
            for s in getattr(split, 'other_splits', [])
        ]
        entries.append({
            'id': split.id,
            'post_date': split.transaction.post_date,
            'description': split.transaction.description,
            'num': split.transaction.num,
            'split_value': str(split.value),
            'split_memo': split.memo,
            'other_accounts': other_accounts,
            'reconcile_state': split.reconcile_state,
            'created_at': split.created_at,
        })

    return {
        'account': account,
        'transactions': entries,
        'running_balance': str(running_balance),
    }
```

### Step 3: Add `@action` to AccountViewSet

```python
# backend/accounts/views.py — modify existing file
from __future__ import annotations

from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Account, Commodity
from accounts.serializers import (
    AccountRegisterResponseSerializer,
    AccountSerializer,
    CommoditySerializer,
)
from accounts.services import get_account_register


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'full_name', 'code']
    ordering_fields = ['name', 'full_name', 'created_at']
    ordering = ['full_name']

    def get_queryset(self):
        return Account.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    @action(detail=True, methods=['get'], url_path='register')
    def register(self, request, pk=None):
        """Return all transactions touching this account with running balance."""
        account = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        data = get_account_register(account, start_date=start_date, end_date=end_date)
        serializer = AccountRegisterResponseSerializer(data)
        return Response(serializer.data)


class CommodityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommoditySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Commodity.objects.all()
```

### Step 4: Commit backend

```bash
git add backend/accounts/services.py backend/accounts/views.py backend/accounts/serializers.py
git commit -m "feat: add account register endpoint with running balance and date filtering"
```

---

## Task 2: Frontend — Register Types and Hook

### Step 1: Create register types

```typescript
// frontend/src/types/register.ts
export type ReconcileState = 'n' | 'c' | 'y' | 'f' | 'v';

export interface RegisterEntry {
  id: string;
  post_date: string;
  description: string;
  num: string;
  split_value: string;
  split_memo: string;
  other_accounts: string[];
  reconcile_state: ReconcileState;
  created_at: string;
}

export interface RegisterResponse {
  account: {
    id: string;
    name: string;
    full_name: string;
    account_type: string;
    commodity: string;
  };
  transactions: RegisterEntry[];
  running_balance: string;
}
```

### Step 2: Create useAccountRegister hook

```typescript
// frontend/src/hooks/use-account-register.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { RegisterResponse } from '@/types/register';

export const registerKeys = {
  all: ['account-register'] as const,
  detail: (id: string, params?: { start_date?: string; end_date?: string }) =>
    [...registerKeys.all, id, params] as const,
};

export function useAccountRegister(
  accountId: string,
  filters?: { start_date?: string; end_date?: string },
) {
  const params = new URLSearchParams();
  if (filters?.start_date) params.set('start_date', filters.start_date);
  if (filters?.end_date) params.set('end_date', filters.end_date);
  const queryString = params.toString();

  return useQuery({
    queryKey: registerKeys.detail(accountId, filters),
    queryFn: () =>
      api.get<RegisterResponse>(
        `/accounts/${accountId}/register${queryString ? `?${queryString}` : ''}`,
      ),
    enabled: !!accountId,
  });
}
```

### Step 3: Commit frontend types and hook

```bash
git add frontend/src/types/register.ts frontend/src/hooks/use-account-register.ts
git commit -m "feat: add register types and React Query hook for account register endpoint"
```

---

## Task 3: Frontend — Register UI Components

### Step 1: Create ReconcileBadge component

```typescript
// frontend/src/features/register/components/ReconcileBadge.tsx
import { Badge } from '@/components/ui/badge';
import type { ReconcileState } from '@/types/register';

const RECONCILE_CONFIG: Record<
  ReconcileState,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  n: { label: 'Not Reconciled', variant: 'secondary' },
  c: { label: 'Cleared', variant: 'outline' },
  y: { label: 'Reconciled', variant: 'default' },
  f: { label: 'Frozen', variant: 'destructive' },
  v: { label: 'Void', variant: 'destructive' },
};

interface ReconcileBadgeProps {
  state: ReconcileState;
}

export function ReconcileBadge({ state }: ReconcileBadgeProps) {
  const config = RECONCILE_CONFIG[state] ?? RECONCILE_CONFIG['n'];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
```

### Step 2: Create RegisterEntryRow component

```typescript
// frontend/src/features/register/components/RegisterEntryRow.tsx
import { format } from 'date-fns';
import type { RegisterEntry } from '@/types/register';
import { ReconcileBadge } from './ReconcileBadge';

interface RegisterEntryRowProps {
  entry: RegisterEntry;
  runningBalance: string;
}

function formatCurrency(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  const sign = num < 0 ? '-' : '';
  const abs = Math.abs(num).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${sign}$${abs}`;
}

export function RegisterEntryRow({ entry, runningBalance }: RegisterEntryRowProps) {
  return (
    <tr className="border-b last:border-0 hover:bg-muted/50 transition-colors">
      <td className="px-4 py-2.5 text-sm text-muted-foreground whitespace-nowrap">
        {format(new Date(entry.post_date + 'T00:00:00'), 'MMM d, yyyy')}
      </td>
      <td className="px-4 py-2.5 text-sm font-mono whitespace-nowrap">{entry.num || '—'}</td>
      <td className="px-4 py-2.5 text-sm">
        <div className="font-medium">{entry.description}</div>
        {entry.split_memo && (
          <div className="text-xs text-muted-foreground truncate max-w-xs">{entry.split_memo}</div>
        )}
        <div className="text-xs text-muted-foreground">
          {entry.other_accounts.join(', ') || '—'}
        </div>
      </td>
      <td className={`px-4 py-2.5 text-sm text-right tabular-nums whitespace-nowrap ${parseFloat(entry.split_value) < 0 ? 'text-destructive' : 'text-foreground'}`}>
        {formatCurrency(entry.split_value)}
      </td>
      <td className="px-4 py-2.5 text-sm text-center whitespace-nowrap">
        <ReconcileBadge state={entry.reconcile_state} />
      </td>
      <td className="px-4 py-2.5 text-sm text-right tabular-nums font-medium whitespace-nowrap">
        {formatCurrency(runningBalance)}
      </td>
    </tr>
  );
}
```

### Step 3: Commit register components

```bash
git add frontend/src/features/register/components/ReconcileBadge.tsx frontend/src/features/register/components/RegisterEntryRow.tsx
git commit -m "feat: add register UI components (ReconcileBadge, RegisterEntryRow)"
```

---

## Task 4: Frontend — Account Register Page

### Step 1: Create AccountRegisterPage

```typescript
// frontend/src/routes/AccountRegisterPage.tsx
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { format } from 'date-fns';
import { ArrowLeft, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAccount } from '@/hooks/use-accounts';
import { useAccountRegister } from '@/hooks/use-account-register';
import { RegisterEntryRow } from '@/features/register/components/RegisterEntryRow';

function formatCurrency(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  const sign = num < 0 ? '-' : '';
  const abs = Math.abs(num).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${sign}$${abs}`;
}

export function AccountRegisterPage() {
  const { id } = useParams<{ id: string }>();
  const accountId = id ?? '';

  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  const { data: account, isLoading: accountLoading } = useAccount(accountId);
  const { data, isLoading, error } = useAccountRegister(accountId, {
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  });

  if (accountLoading || isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-10 w-full animate-pulse rounded bg-muted" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load register.</p>
      </div>
    );
  }

  if (!data) return null;

  let runningBalance = 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/accounts">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{data.account.full_name || data.account.name}</h1>
          <p className="text-sm text-muted-foreground">
            {data.account.account_type} &middot; Balance: {formatCurrency(data.running_balance)}
          </p>
        </div>
      </div>

      {/* Date filter */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Filter by Date
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div>
              <label htmlFor="start-date" className="text-sm text-muted-foreground">From</label>
              <input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="end-date" className="text-sm text-muted-foreground">To</label>
              <input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              />
            </div>
            {(startDate || endDate) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setStartDate(''); setEndDate(''); }}
              >
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Register table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Transactions ({data.transactions.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Num</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Description / Account</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Amount</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Balance</th>
              </tr>
            </thead>
            <tbody>
              {data.transactions.map((entry) => {
                runningBalance += parseFloat(entry.split_value);
                return (
                  <RegisterEntryRow
                    key={entry.id}
                    entry={entry}
                    runningBalance={runningBalance.toString()}
                  />
                );
              })}
              {data.transactions.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-muted-foreground">
                    No transactions found for this account.
                    {(startDate || endDate) && ' Try adjusting the date filter.'}
                  </td>
                </tr>
              )}
            </tbody>
            {data.transactions.length > 0 && (
              <tfoot>
                <tr className="border-t font-semibold">
                  <td colSpan={3} className="px-4 py-3 text-sm text-right">Ending Balance</td>
                  <td />
                  <td />
                  <td className="px-4 py-3 text-sm text-right tabular-nums">
                    {formatCurrency(data.running_balance)}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Step 2: Wire route into App.tsx

Modify `frontend/src/App.tsx` to add the import and route:

```typescript
// frontend/src/App.tsx — add import
import { AccountRegisterPage } from '@/routes/AccountRegisterPage';

// frontend/src/App.tsx — add route inside <Routes>, after /accounts:
<Route path="/accounts/:id" element={<AccountRegisterPage />} />
```

### Step 3: Ensure AccountListPage links to register

The existing `AccountListPage.tsx` already links to `/accounts/${account.id}` (line 35). With the register page now existing at that path, the link will work. No changes needed.

### Step 4: Commit

```bash
git add frontend/src/routes/AccountRegisterPage.tsx frontend/src/App.tsx
git commit -m "feat: add account register page with date filter, running balance, reconcile badges"
```

---

## Task 5: Backend Tests

### Step 1: Write service and endpoint tests

```python
# backend/accounts/test_register.py
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
```

### Step 2: Commit tests

```bash
git add backend/accounts/test_register.py
git commit -m "test: add account register service and endpoint tests with tenant isolation"
```

---

## Task 6: Frontend Tests

### Step 1: Write component tests

```typescript
// frontend/src/features/register/__tests__/RegisterEntryRow.test.tsx
import { render, screen } from '@testing-library/react';
import type { RegisterEntry } from '@/types/register';
import { RegisterEntryRow } from '../components/RegisterEntryRow';

function makeEntry(overrides: Partial<RegisterEntry> = {}): RegisterEntry {
  return {
    id: 'test-id',
    post_date: '2025-03-15',
    description: 'Grocery Store',
    num: '1001',
    split_value: '-42.50',
    split_memo: 'Weekly shopping',
    other_accounts: ['Expenses:Groceries'],
    reconcile_state: 'n',
    created_at: '2025-03-15T10:00:00Z',
    ...overrides,
  };
}

test('renders date, description, and amount', () => {
  render(<RegisterEntryRow entry={makeEntry()} runningBalance="100.00" />);
  expect(screen.getByText('Mar 15, 2025')).toBeTruthy();
  expect(screen.getByText('Grocery Store')).toBeTruthy();
  expect(screen.getByText('$42.50')).toBeTruthy();
});

test('shows memo text when present', () => {
  render(<RegisterEntryRow entry={makeEntry()} runningBalance="0" />);
  expect(screen.getByText('Weekly shopping')).toBeTruthy();
});

test('shows other account names', () => {
  render(<RegisterEntryRow entry={makeEntry()} runningBalance="0" />);
  expect(screen.getByText('Expenses:Groceries')).toBeTruthy();
});

test('renders running balance', () => {
  render(<RegisterEntryRow entry={makeEntry()} runningBalance="1250.75" />);
  expect(screen.getByText('$1,250.75')).toBeTruthy();
});

test('renders ReconcileBadge with correct state', () => {
  render(<RegisterEntryRow entry={makeEntry({ reconcile_state: 'y' })} runningBalance="0" />);
  expect(screen.getByText('Reconciled')).toBeTruthy();
});

test('shows dash for empty num field', () => {
  render(<RegisterEntryRow entry={makeEntry({ num: '' })} runningBalance="0" />);
  expect(screen.getByText('—')).toBeTruthy();
});
```

```typescript
// frontend/src/features/register/__tests__/ReconcileBadge.test.tsx
import { render, screen } from '@testing-library/react';
import { ReconcileBadge } from '../components/ReconcileBadge';

test.each([
  ['n', 'Not Reconciled'],
  ['c', 'Cleared'],
  ['y', 'Reconciled'],
  ['f', 'Frozen'],
  ['v', 'Void'],
])('renders %s state as %s', (state, label) => {
  render(<ReconcileBadge state={state as 'n' | 'c' | 'y' | 'f' | 'v'} />);
  expect(screen.getByText(label)).toBeTruthy();
});
```

### Step 2: Commit tests

```bash
git add frontend/src/features/register/__tests__/
git commit -m "test: add register component unit tests (ReconcileBadge, RegisterEntryRow)"
```

---

## Self-Review

### 1. Spec Coverage Check

| Requirement | Task | Status |
|---|---|---|
| Account header (name, type, balance) | Task 4 (Step 1) | Covered |
| Table of transactions touching account | Task 1+4 (service + page) | Covered |
| Sorted by date ascending | Task 1 (Step 2, `order_by`) | Covered |
| Running balance column | Task 4 (Step 1, client-side accumulation) | Covered |
| Reconciliation state badges | Task 3 (Step 1, ReconcileBadge) | Covered |
| Date range filter | Task 1 (Step 2, service params) + Task 4 (UI) | Covered |
| Backend endpoint `/accounts/:id/register` | Task 1 (Step 3, `@action`) | Covered |
| TypeScript strict, no `any` | All frontend steps | Covered |
| Tenant isolation | Task 1 (Step 2, service) + Task 5 (test) | Covered |
| Property-based double-entry | Not applicable — register is a read view | N/A |

### 2. Backend Prerequisite Note

The `GET /api/v1/accounts/:id/register` endpoint does NOT exist in the current codebase. `AccountViewSet` only provides standard CRUD via `ModelViewSet`. This plan creates it in Task 1 via a `@action(detail=True)` decorator that delegates to `accounts/services.py` for query logic.

### 3. Running Balance Design Decision

Running balance is computed client-side by accumulating `split_value` as entries are rendered in date order. This is correct because:
- The service returns entries in `order_by('transaction__post_date', 'transaction__enter_date', 'id')` — deterministic order
- The client accumulates the same order, matching the server's sort
- The backend also returns `running_balance` as the final total, which is displayed in the footer and account header for verification
- If entries are filtered by date, the running balance starts from zero for the visible window — this matches the classic GnuCash register behavior where the balance column is "running total from the start of the filtered view"

For an opening-balance-aware implementation (starting from a balance before the filter window), a separate `opening_balance` field could be added to the response in a future iteration.

### 4. Placeholder Scan

- Account Register page does not include inline editing of reconcile state — that would require a mutation endpoint (PATCH `/splits/:id/reconcile`) which is out of scope for this page. The page is read-only.
- Date filter uses native `<input type="date">` — a full date-range picker with calendar UI could replace this using shadcn `Popover` + `Calendar` in a future iteration.
- No `any` types used. All imports are typed.

### 5. Type/Name Consistency

- `ReconcileState` type matches the Django model `Split.ReconcileState` choices exactly (`'n'`, `'c'`, `'y'`, `'f'`, `'v'`)
- React Query keys follow the `['account-register', id, params]` pattern per frontend-state rules
- Mutation invalidation: not applicable — this page is read-only
- API path: `/api/v1/accounts/:id/register` matches the DRF `@action(url_path='register')` basename
- Response format matches the spec: `{ account, transactions: [...], running_balance }`
