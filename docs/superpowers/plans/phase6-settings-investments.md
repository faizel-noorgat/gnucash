# Phase 6 — Settings Pages & Investment Portfolio UI

**Branch:** `phase-6-settings-investments`
**Estimate:** 6-8 hours
**Prerequisites:** Phase 1-5 complete, backend `tenants`, `investments`, `audit` apps functional

---

## Backend Verification (pre-work)

### Task 6.0 — Audit DELETE on TenantMembership & AuditLog pagination

- [ ] **6.0.1** Verify `TenantMembershipViewSet` DELETE works

The `TenantMembershipViewSet` uses `ModelViewSet`, so `DELETE` is supported. However, `get_queryset()` filters by `tenant__memberships__user=self.request.user` — any tenant member can delete any membership in tenants they belong to. There is no ownership check (e.g., only OWNER/ADMIN can remove members).

**Required fix before frontend work:** Add permission class to restrict delete to OWNER/ADMIN role.

Add `backend/tenants/permissions.py`:

```python
# backend/tenants/permissions.py
from __future__ import annotations

from rest_framework import permissions

from tenants.models import TenantMembership


class IsTenantAdmin(permissions.BasePermission):
    """
    Allow write access only to OWNER or ADMIN role members.
    Read access allowed for all tenant members.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return TenantMembership.objects.filter(
            tenant__memberships__user=request.user,
            role__in=['OWNER', 'ADMIN'],
        ).exists()
```

Update `backend/tenants/views.py`:

```python
# In TenantMembershipViewSet, change:
permission_classes = [IsAuthenticated]
# to:
permission_classes = [IsAuthenticated]

def get_permissions(self):
    if self.action in ('create', 'update', 'partial_update', 'destroy'):
        return [IsTenantAdmin()]
    return super().get_permissions()
```

- [ ] **6.0.2** Verify AuditLog pagination

`AuditLogViewSet` is `ReadOnlyModelViewSet`. Global DRF settings use `PageNumberPagination` with `PAGE_SIZE=50`. Pagination works out of the box. The response shape is:

```json
{ "count": 142, "next": "...", "previous": null, "results": [...] }
```

No backend changes needed.

---

## Frontend: Types

### Task 6.1 — Create TypeScript type definitions

- [ ] **6.1.1** `frontend/src/types/tenant.ts`

```typescript
// frontend/src/types/tenant.ts
export interface Tenant {
  id: string;
  name: string;
  slug: string;
  trial_ends_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TenantListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Tenant[];
}

export type MembershipRole = 'OWNER' | 'ADMIN' | 'MEMBER';

export interface TenantMembership {
  id: string;
  tenant: string;
  user: string;
  user_email: string;
  role: MembershipRole;
  joined_at: string;
}

export interface TenantMembershipListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: TenantMembership[];
}

export type MembershipAction = 'create' | 'update' | 'delete';

export interface CreateMembershipInput {
  user_email: string;
  role: MembershipRole;
}

export interface UpdateMembershipInput {
  id: string;
  role: MembershipRole;
}
```

- [ ] **6.1.2** `frontend/src/types/investment.ts`

```typescript
// frontend/src/types/investment.ts
export interface InvestmentAccount {
  id: string;
  tenant: string;
  account: string;
  account_name: string;
  institution: string;
  account_number: string;
}

export interface InvestmentAccountListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: InvestmentAccount[];
}

export interface InvestmentLot {
  id: string;
  tenant: string;
  account: string;
  security_id: string;
  quantity: string;
  purchase_date: string;
  purchase_price: string;
  cost_basis: string;
  is_closed: boolean;
  created_at: string;
}

export interface InvestmentLotListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: InvestmentLot[];
}

export interface Price {
  id: string;
  commodity: string;
  commodity_mnemonic: string;
  currency: string;
  date: string;
  source: string;
  price_type: string;
  value: string;
}

export interface PriceListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Price[];
}
```

- [ ] **6.1.3** `frontend/src/types/audit.ts`

```typescript
// frontend/src/types/audit.ts
export type AuditAction = 'CREATE' | 'UPDATE' | 'DELETE' | 'LOGIN' | 'LOGOUT' | 'EXPORT';

export interface AuditLog {
  id: string;
  tenant: string;
  user: string | null;
  user_email: string | null;
  action: AuditAction;
  model: string;
  object_id: string;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string;
  timestamp: string;
}

export interface AuditLogListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditLog[];
}
```

**Commit step:**

```bash
git add frontend/src/types/tenant.ts frontend/src/types/investment.ts frontend/src/types/audit.ts
git commit -m "feat(phase6): add TypeScript types for tenant, investment, and audit

Add type definitions for Tenant, TenantMembership, InvestmentAccount,
InvestmentLot, Price, AuditLog, and their paginated list responses.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Frontend: Custom Hooks

### Task 6.2 — `use-users.ts` — Tenant membership hooks

- [ ] **6.2.1** `frontend/src/hooks/use-users.ts`

```typescript
// frontend/src/hooks/use-users.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  TenantMembership,
  TenantMembershipListResponse,
  CreateMembershipInput,
  UpdateMembershipInput,
} from '@/types/tenant';

export const membershipKeys = {
  all: ['memberships'] as const,
  list: () => [...membershipKeys.all, 'list'] as const,
  detail: (id: string) => [...membershipKeys.all, 'detail', id] as const,
};

export function useTenantMemberships() {
  return useQuery({
    queryKey: membershipKeys.list(),
    queryFn: () => api.get<TenantMembershipListResponse>('/tenant-memberships/'),
  });
}

export function useCreateMembership() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateMembershipInput) =>
      api.post<TenantMembership>('/tenant-memberships/', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: membershipKeys.all }),
  });
}

export function useUpdateMembership() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role }: UpdateMembershipInput) =>
      api.patch<TenantMembership>(`/tenant-memberships/${id}/`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: membershipKeys.all }),
  });
}

export function useDeleteMembership() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<void>(`/tenant-memberships/${id}/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: membershipKeys.all }),
  });
}
```

**Commit step:**

```bash
git add frontend/src/hooks/use-users.ts
git commit -m "feat(phase6): add use-users hooks for tenant membership CRUD

Add useTenantMemberships, useCreateMembership, useUpdateMembership,
useDeleteMembership hooks for TenantMembership API.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 6.3 — `use-investments.ts` — Investment hooks

- [ ] **6.3.1** `frontend/src/hooks/use-investments.ts`

```typescript
// frontend/src/hooks/use-investments.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  InvestmentAccount,
  InvestmentAccountListResponse,
  InvestmentLot,
  InvestmentLotListResponse,
  Price,
  PriceListResponse,
} from '@/types/investment';

export const investmentAccountKeys = {
  all: ['investment-accounts'] as const,
  list: () => [...investmentAccountKeys.all, 'list'] as const,
  detail: (id: string) => [...investmentAccountKeys.all, 'detail', id] as const,
  lots: (accountId: string) => [...investmentAccountKeys.all, 'lots', accountId] as const,
};

export const investmentLotKeys = {
  all: ['investment-lots'] as const,
  list: () => [...investmentLotKeys.all, 'list'] as const,
};

export const priceKeys = {
  all: ['prices'] as const,
  list: (params?: { commodity?: string }) => [...priceKeys.all, 'list', params] as const,
};

export function useInvestmentAccounts() {
  return useQuery({
    queryKey: investmentAccountKeys.list(),
    queryFn: () => api.get<InvestmentAccountListResponse>('/investments/'),
  });
}

export function useInvestmentAccount(id: string) {
  return useQuery({
    queryKey: investmentAccountKeys.detail(id),
    queryFn: () => api.get<InvestmentAccount>(`/investments/${id}/`),
    enabled: !!id,
  });
}

export function useInvestmentLots(accountId?: string) {
  const url = accountId ? `/investment-lots/?account=${accountId}` : '/investment-lots/';
  return useQuery({
    queryKey: accountId ? investmentAccountKeys.lots(accountId) : investmentLotKeys.list(),
    queryFn: () => api.get<InvestmentLotListResponse>(url),
    enabled: accountId !== undefined,
  });
}

export function usePrices(params?: { commodity?: string }) {
  const qs = params?.commodity ? `?commodity=${params.commodity}` : '';
  return useQuery({
    queryKey: priceKeys.list(params),
    queryFn: () => api.get<PriceListResponse>(`/prices/${qs}`),
  });
}

export function useCreateInvestmentAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<InvestmentAccount>) =>
      api.post<InvestmentAccount>('/investments/', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: investmentAccountKeys.all }),
  });
}

export function useCreateInvestmentLot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<InvestmentLot>) =>
      api.post<InvestmentLot>('/investment-lots/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: investmentLotKeys.all });
      qc.invalidateQueries({ queryKey: investmentAccountKeys.all });
    },
  });
}
```

**Commit step:**

```bash
git add frontend/src/hooks/use-investments.ts
git commit -m "feat(phase6): add use-investments hooks for accounts, lots, and prices

Add React Query hooks for InvestmentAccount, InvestmentLot, and Price
APIs with proper cache key structure and invalidation.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 6.4 — `use-audit.ts` — Audit log hook

- [ ] **6.4.1** `frontend/src/hooks/use-audit.ts`

```typescript
// frontend/src/hooks/use-audit.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AuditLogListResponse } from '@/types/audit';

export const auditKeys = {
  all: ['audit-log'] as const,
  list: (params?: { action?: string; date_from?: string; date_to?: string; user?: string }) =>
    [...auditKeys.all, 'list', params] as const,
};

export function useAuditLog(params?: {
  action?: string;
  date_from?: string;
  date_to?: string;
  user?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.action) searchParams.set('search', params.action);
  if (params?.date_from) searchParams.set('date_from', params.date_from);
  if (params?.date_to) searchParams.set('date_to', params.date_to);
  if (params?.user) searchParams.set('user', params.user);

  const qs = searchParams.toString();
  return useQuery({
    queryKey: auditKeys.list(params),
    queryFn: () => api.get<AuditLogListResponse>(`/audit-log/${qs ? `?${qs}` : ''}`),
  });
}
```

**Commit step:**

```bash
git add frontend/src/hooks/use-audit.ts
git commit -m "feat(phase6): add use-audit hook for audit log with filters

Add useAuditLog hook supporting action, date range, and user filters.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Frontend: Pages

### Task 6.5 — `SettingsPage.tsx` — Tenant settings form

- [ ] **6.5.1** `frontend/src/routes/SettingsPage.tsx`

```typescript
// frontend/src/routes/SettingsPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';

interface TenantSummary {
  id: string;
  name: string;
  slug: string;
  trial_ends_at: string | null;
}

function useCurrentTenant(): TenantSummary | null {
  const tenantId = typeof window !== 'undefined' ? localStorage.getItem('gnucash_tenant_id') : null;
  if (!tenantId) return null;
  const raw = typeof window !== 'undefined' ? localStorage.getItem(`gnucash_tenant_${tenantId}`) : null;
  if (!raw) return null;
  try {
    return JSON.parse(raw) as TenantSummary;
  } catch {
    return null;
  }
}

export function SettingsPage() {
  const tenant = useCurrentTenant();
  const [name, setName] = useState(tenant?.name ?? '');

  const trialBadge = tenant?.trial_ends_at ? (
    new Date(tenant.trial_ends_at) > new Date() ? (
      <Badge variant="default">Trial active — ends {new Date(tenant.trial_ends_at).toLocaleDateString()}</Badge>
    ) : (
      <Badge variant="destructive">Trial expired</Badge>
    )
  ) : (
    <Badge variant="outline">No trial info</Badge>
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Tenant Information</CardTitle>
          <CardDescription>View and manage your workspace settings.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="tenant-name">Workspace name</Label>
            <Input
              id="tenant-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Workspace"
            />
          </div>
          <div className="space-y-2">
            <Label>Slug</Label>
            <p className="text-sm text-muted-foreground">{tenant?.slug ?? '—'}</p>
          </div>
          <div className="space-y-2">
            <Label>Trial status</Label>
            <div>{trialBadge}</div>
          </div>
          <Button type="button" disabled={name === tenant?.name}>Save</Button>
        </CardContent>
      </Card>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Quick Links</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link to="/settings/users">Manage Users</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/settings/audit-log">Audit Log</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Commit step:**

```bash
git add frontend/src/routes/SettingsPage.tsx
git commit -m "feat(phase6): add Settings page with tenant info and quick links

Display tenant name, slug, trial status, and navigation to Users and
Audit Log sub-pages.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 6.6 — `UsersPage.tsx` — Tenant member management

- [ ] **6.6.1** `frontend/src/routes/UsersPage.tsx`

```typescript
// frontend/src/routes/UsersPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  useTenantMemberships,
  useCreateMembership,
  useUpdateMembership,
  useDeleteMembership,
} from '@/hooks/use-users';
import type { MembershipRole } from '@/types/tenant';

const roleVariant: Record<MembershipRole, 'default' | 'secondary' | 'outline'> = {
  OWNER: 'default',
  ADMIN: 'secondary',
  MEMBER: 'outline',
};

export function UsersPage() {
  const { data, isLoading, error } = useTenantMemberships();
  const createMutation = useCreateMembership();
  const updateMutation = useUpdateMembership();
  const deleteMutation = useDeleteMembership();

  const [email, setEmail] = useState('');
  const [role, setRole] = useState<MembershipRole>('MEMBER');

  const handleAddMember = () => {
    if (!email.trim()) return;
    createMutation.mutate({ user_email: email.trim(), role });
    setEmail('');
    setRole('MEMBER');
  };

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load members.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Team Members</h1>
          <p className="text-sm text-muted-foreground">Manage who has access to this workspace.</p>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">Add Member</CardTitle></CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => { e.preventDefault(); handleAddMember(); }}
            className="flex gap-3 items-end"
          >
            <div className="flex-1 space-y-2">
              <Label htmlFor="member-email">Email</Label>
              <Input
                id="member-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
                disabled={createMutation.isPending}
              />
            </div>
            <div className="w-40 space-y-2">
              <Label htmlFor="member-role">Role</Label>
              <Select value={role} onValueChange={(v: MembershipRole) => setRole(v)} disabled={createMutation.isPending}>
                <SelectTrigger id="member-role"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="OWNER">Owner</SelectItem>
                  <SelectItem value="ADMIN">Admin</SelectItem>
                  <SelectItem value="MEMBER">Member</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={createMutation.isPending || !email.trim()}>
              {createMutation.isPending ? 'Adding...' : 'Add'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} Members</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead className="w-48">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.results.map((m) => (
                <TableRow key={m.id}>
                  <TableCell className="font-medium">{m.user_email}</TableCell>
                  <TableCell>
                    <Select
                      value={m.role}
                      onValueChange={(v: MembershipRole) => updateMutation.mutate({ id: m.id, role: v })}
                      disabled={m.role === 'OWNER'}
                    >
                      <SelectTrigger className="w-32">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="OWNER">Owner</SelectItem>
                        <SelectItem value="ADMIN">Admin</SelectItem>
                        <SelectItem value="MEMBER">Member</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(m.joined_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {m.role !== 'OWNER' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => deleteMutation.mutate(m.id)}
                        disabled={deleteMutation.isPending}
                      >
                        Remove
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {data?.results.length === 0 && (
                <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground">No members found.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Button variant="outline" asChild>
        <Link to="/settings">Back to Settings</Link>
      </Button>
    </div>
  );
}
```

**Commit step:**

```bash
git add frontend/src/routes/UsersPage.tsx
git commit -m "feat(phase6): add Users page for tenant member management

Team member list with add, role change (inline select), and remove
functionality. OWNER role cannot be removed or demoted.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 6.7 — `AuditLogPage.tsx` — Read-only audit log table

- [ ] **6.7.1** `frontend/src/routes/AuditLogPage.tsx`

```typescript
// frontend/src/routes/AuditLogPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { useAuditLog } from '@/hooks/use-audit';
import type { AuditAction } from '@/types/audit';

const actionColors: Record<AuditAction, 'default' | 'destructive' | 'secondary' | 'outline'> = {
  CREATE: 'default',
  UPDATE: 'secondary',
  DELETE: 'destructive',
  LOGIN: 'outline',
  LOGOUT: 'outline',
  EXPORT: 'secondary',
};

export function AuditLogPage() {
  const [action, setAction] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [userFilter, setUserFilter] = useState('');

  const { data, isLoading, error } = useAuditLog(
    action || dateFrom || dateTo || userFilter
      ? { action, date_from: dateFrom, date_to: dateTo, user: userFilter }
      : undefined,
  );

  const handleClearFilters = () => {
    setAction('');
    setDateFrom('');
    setDateTo('');
    setUserFilter('');
  };

  const hasFilters = action || dateFrom || dateTo || userFilter;

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-10 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load audit log.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <Button variant="outline" asChild><Link to="/settings">Back to Settings</Link></Button>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">Filters</CardTitle></CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => { e.preventDefault(); }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            <div className="space-y-2">
              <Label htmlFor="filter-action">Action</Label>
              <Input
                id="filter-action"
                value={action}
                onChange={(e) => setAction(e.target.value)}
                placeholder="CREATE, UPDATE..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-date-from">Date from</Label>
              <Input
                id="filter-date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-date-to">Date to</Label>
              <Input
                id="filter-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-user">User</Label>
              <Input
                id="filter-user"
                value={userFilter}
                onChange={(e) => setUserFilter(e.target.value)}
                placeholder="user@example.com"
              />
            </div>
          </form>
          {hasFilters && (
            <div className="mt-4">
              <Button variant="ghost" size="sm" onClick={handleClearFilters}>Clear filters</Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} entries</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Object ID</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.results.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(log.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Badge variant={actionColors[log.action]}>{log.action}</Badge>
                  </TableCell>
                  <TableCell className="text-sm">{log.user_email ?? 'system'}</TableCell>
                  <TableCell className="text-sm font-mono">{log.model}</TableCell>
                  <TableCell className="text-sm font-mono text-muted-foreground">
                    {log.object_id.slice(0, 8)}...
                  </TableCell>
                </TableRow>
              ))}
              {data?.results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    No audit log entries found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Commit step:**

```bash
git add frontend/src/routes/AuditLogPage.tsx
git commit -m "feat(phase6): add Audit Log page with action, date, and user filters

Read-only audit log table with filter controls, color-coded action badges,
and clear-filters button.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 6.8 — `InvestmentListPage.tsx` — Investment accounts list

- [ ] **6.8.1** `frontend/src/routes/InvestmentListPage.tsx`

```typescript
// frontend/src/routes/InvestmentListPage.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useInvestmentAccounts } from '@/hooks/use-investments';

export function InvestmentListPage() {
  const { data, isLoading, error } = useInvestmentAccounts();

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load investments.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Investments</h1>
        <Button asChild><Link to="/investments/new">New Investment</Link></Button>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} Investment Accounts</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Account</TableHead>
                <TableHead>Institution</TableHead>
                <TableHead>Account Number</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.results.map((inv) => (
                <TableRow key={inv.id}>
                  <TableCell className="font-medium">{inv.account_name}</TableCell>
                  <TableCell className="text-muted-foreground">{inv.institution || '—'}</TableCell>
                  <TableCell className="font-mono text-sm">{inv.account_number || '—'}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" asChild>
                      <Link to={`/investments/${inv.id}`}>View</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {data?.results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                    No investment accounts. Create one to get started.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Commit step:**

```bash
git add frontend/src/routes/InvestmentListPage.tsx
git commit -m "feat(phase6): add Investment List page

List of investment accounts with name, institution, and account number.
Links to detail page per account.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task 6.9 — `InvestmentDetailPage.tsx` — Lots table with cost basis

- [ ] **6.9.1** `frontend/src/routes/InvestmentDetailPage.tsx`

```typescript
// frontend/src/routes/InvestmentDetailPage.tsx
import { useParams, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useInvestmentAccount, useInvestmentLots } from '@/hooks/use-investments';

function formatDecimal(value: string, digits = 2): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return num.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function InvestmentDetailPage() {
  const { id } = useParams<{ id: string }>() as { id: string };
  const { data: account, isLoading: accountLoading } = useInvestmentAccount(id);
  const { data: lots, isLoading: lotsLoading } = useInvestmentLots(id);

  if (accountLoading || lotsLoading) {
    return <div className="space-y-4">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (!account) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Investment account not found.</p></div>;
  }

  const totalQuantity = lots?.results.reduce((sum, lot) => {
    if (lot.is_closed) return sum;
    return sum + parseFloat(lot.quantity);
  }, 0) ?? 0;

  const totalCostBasis = lots?.results.reduce((sum, lot) => {
    return sum + parseFloat(lot.cost_basis);
  }, 0) ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{account.account_name}</h1>
          {account.institution && <p className="text-sm text-muted-foreground">{account.institution}</p>}
        </div>
        <Button variant="outline" asChild><Link to="/investments">Back</Link></Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle className="text-sm font-medium text-muted-foreground">Holdings</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{formatDecimal(totalQuantity.toString(), 4)}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm font-medium text-muted-foreground">Total Cost Basis</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">${formatDecimal(totalCostBasis.toString())}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm font-medium text-muted-foreground">Lots</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">{lots?.count ?? 0}</p></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Lots</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Security</TableHead>
                <TableHead className="text-right">Quantity</TableHead>
                <TableHead className="text-right">Purchase Price</TableHead>
                <TableHead className="text-right">Cost Basis</TableHead>
                <TableHead>Purchase Date</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {lots?.results.map((lot) => (
                <TableRow key={lot.id}>
                  <TableCell className="font-mono font-medium">{lot.security_id}</TableCell>
                  <TableCell className="text-right">{formatDecimal(lot.quantity, 4)}</TableCell>
                  <TableCell className="text-right">${formatDecimal(lot.purchase_price)}</TableCell>
                  <TableCell className="text-right font-medium">${formatDecimal(lot.cost_basis)}</TableCell>
                  <TableCell className="text-muted-foreground">{new Date(lot.purchase_date).toLocaleDateString()}</TableCell>
                  <TableCell>
                    {lot.is_closed ? (
                      <Badge variant="outline">Closed</Badge>
                    ) : (
                      <Badge variant="default">Open</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {lots?.results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No lots recorded for this account.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Commit step:**

```bash
git add frontend/src/routes/InvestmentDetailPage.tsx
git commit -m "feat(phase6): add Investment Detail page with lots table

Display investment account summary (holdings, cost basis, lot count) and
a lots table with security, quantity, purchase price, cost basis, and
open/closed status.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Frontend: Route wiring

### Task 6.10 — Wire routes in `App.tsx`

- [ ] **6.10.1** Update `frontend/src/App.tsx`

Replace the placeholder routes and add the new pages. The diff:

```typescript
// Add imports at the top:
import { SettingsPage } from '@/routes/SettingsPage';
import { UsersPage } from '@/routes/UsersPage';
import { AuditLogPage } from '@/routes/AuditLogPage';
import { InvestmentListPage } from '@/routes/InvestmentListPage';
import { InvestmentDetailPage } from '@/routes/InvestmentDetailPage';

// Replace the placeholder route for /investments:
// FROM: <Route path="/investments" element={<PlaceholderPage title="Investments" />} />
// TO:   <Route path="/investments" element={<InvestmentListPage />} />
//       <Route path="/investments/:id" element={<InvestmentDetailPage />} />

// Replace the placeholder route for /settings:
// FROM: <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
// TO:   <Route path="/settings" element={<SettingsPage />} />
//       <Route path="/settings/users" element={<UsersPage />} />
//       <Route path="/settings/audit-log" element={<AuditLogPage />} />
```

Full updated file:

```typescript
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/query-client';
import { AuthLayout } from '@/components/layouts/AuthLayout';
import { RootLayout } from '@/components/layouts/RootLayout';
import { ProtectedRoute } from '@/routes/ProtectedRoute';
import { LoginPage } from '@/routes/LoginPage';
import { RegisterPage } from '@/routes/RegisterPage';
import { DashboardPage } from '@/routes/DashboardPage';
import { NotFoundPage } from '@/routes/NotFoundPage';
import { AccountListPage } from '@/routes/AccountListPage';
import { ReportsIndex } from '@/routes/reports';
import { BalanceSheetPage } from '@/routes/reports/balance-sheet';
import { IncomeStatementPage } from '@/routes/reports/income-statement';
import { CashFlowPage } from '@/routes/reports/cash-flow';
import { SettingsPage } from '@/routes/SettingsPage';
import { UsersPage } from '@/routes/UsersPage';
import { AuditLogPage } from '@/routes/AuditLogPage';
import { InvestmentListPage } from '@/routes/InvestmentListPage';
import { InvestmentDetailPage } from '@/routes/InvestmentDetailPage';

function PlaceholderPage({ title }: { title: string }) {
  return <div><h1 className="text-2xl font-bold">{title}</h1><p className="mt-2 text-muted-foreground">Coming soon.</p></div>;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route element={<RootLayout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/accounts" element={<AccountListPage />} />
              <Route path="/transactions" element={<PlaceholderPage title="Transactions" />} />
              <Route path="/budgets" element={<PlaceholderPage title="Budgets" />} />
              <Route path="/investments" element={<InvestmentListPage />} />
              <Route path="/investments/:id" element={<InvestmentDetailPage />} />
              <Route path="/receipts" element={<PlaceholderPage title="Receipts" />} />
              <Route path="/recurring" element={<PlaceholderPage title="Recurring" />} />
              <Route path="/reports" element={<ReportsIndex />} />
              <Route path="/reports/balance-sheet" element={<BalanceSheetPage />} />
              <Route path="/reports/income-statement" element={<IncomeStatementPage />} />
              <Route path="/reports/cash-flow" element={<CashFlowPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/settings/users" element={<UsersPage />} />
              <Route path="/settings/audit-log" element={<AuditLogPage />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

**Commit step:**

```bash
git add frontend/src/App.tsx
git commit -m "feat(phase6): wire settings, users, audit log, and investment routes

Replace placeholder routes with SettingsPage, UsersPage, AuditLogPage,
InvestmentListPage, and InvestmentDetailPage.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Backend: Permission fix

### Task 6.11 — Restrict TenantMembership writes to OWNER/ADMIN

- [ ] **6.11.1** `backend/tenants/permissions.py`

```python
# backend/tenants/permissions.py
from __future__ import annotations

from rest_framework import permissions

from tenants.models import TenantMembership


class IsTenantAdmin(permissions.BasePermission):
    """
    Allow write access only to OWNER or ADMIN role members.
    Read access allowed for all tenant members (handled by queryset).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return TenantMembership.objects.filter(
            tenant__memberships__user=request.user,
            role__in=[TenantMembership.Role.OWNER, TenantMembership.Role.ADMIN],
        ).exists()
```

- [ ] **6.11.2** Update `backend/tenants/views.py` — add permission check to `TenantMembershipViewSet`:

```python
# Add import:
from tenants.permissions import IsTenantAdmin

# In TenantMembershipViewSet, add:
def get_permissions(self):
    if self.action in ('create', 'update', 'partial_update', 'destroy'):
        return [IsTenantAdmin()]
    return super().get_permissions()
```

**Commit step:**

```bash
git add backend/tenants/permissions.py backend/tenants/views.py
git commit -m "fix(phase6): restrict TenantMembership writes to OWNER/ADMIN

Add IsTenantAdmin permission class that gates create, update, and delete
on TenantMembership to users with OWNER or ADMIN role in the tenant.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Verification checklist

- [ ] TypeScript compiles with `--noEmit`: `cd frontend && npx tsc --noEmit`
- [ ] No `any` types in new files: `cd frontend && npx tsc --noEmit --strict`
- [ ] ESLint passes: `cd frontend && npx eslint src/routes/SettingsPage.tsx src/routes/UsersPage.tsx src/routes/AuditLogPage.tsx src/routes/InvestmentListPage.tsx src/routes/InvestmentDetailPage.tsx src/hooks/use-investments.ts src/hooks/use-audit.ts src/hooks/use-users.ts`
- [ ] Backend tests pass: `cd backend && python manage.py test tenants.tests`
- [ ] Manual smoke test: login as tenant owner, visit `/settings`, `/settings/users`, `/settings/audit-log`, `/investments`, `/investments/:id`
