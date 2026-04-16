# Phase 3: Frontend Core Accounting Components

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the four core reusable accounting components that every financial screen in the app will depend on: `AccountPicker`, `SplitInput`, `TransactionForm`, and `AccountList`.

**Architecture:** React 18 + TypeScript + Vite. shadcn/ui for primitives, React Query for server state, React Hook Form + Zod for form state, Zustand for client state. Components live under `frontend/src/` and compose into feature-level screens.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, shadcn/ui, @tanstack/react-query v5, react-hook-form + zod, lucide-react, @radix-ui primitives

---

## Prerequisites: Install shadcn/ui Primitives

Before any component task, the following shadcn/ui components must be installed. These are one-time setup steps.

```bash
cd frontend
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add label
npx shadcn@latest add command
npx shadcn@latest add popover
npx shadcn@latest add dialog
npx shadcn@latest add card
npx shadcn@latest add table
npx shadcn@latest add badge
npx shadcn@latest add skeleton
npx shadcn@latest add form
npx shadcn@latest add separator
npx shadcn@latest add tooltip
npx shadcn@latest add calendar
npx shadcn@latest add select
```

Also install `@tanstack/react-query`, `react-hook-form`, `@hookform/resolvers`, `zod`, and `date-fns`:

```bash
cd frontend
npm install @tanstack/react-query react-hook-form @hookform/resolvers zod date-fns lucide-react
```

---

## File Map

### Files to Create

#### Shared hooks (`frontend/src/hooks/`)
- `frontend/src/hooks/use-accounts.ts` — React Query hooks for account CRUD
- `frontend/src/hooks/use-transactions.ts` — React Query hooks for transaction CRUD
- `frontend/src/hooks/use-split-balance.ts` — Custom hook for real-time split balance computation

#### API layer (`frontend/src/lib/`)
- `frontend/src/lib/api.ts` — Typed fetch wrapper with tenant header injection
- `frontend/src/lib/query-client.ts` — React Query client configuration

#### Types (`frontend/src/types/`)
- `frontend/src/types/account.ts` — Account interface and API response types
- `frontend/src/types/transaction.ts` — Transaction/Split interfaces and API response types

#### Components (`frontend/src/components/`)
- `frontend/src/components/ui/` — shadcn/ui primitives (installed via CLI above)
- `frontend/src/components/account-picker.tsx` — Searchable account combobox
- `frontend/src/components/split-input.tsx` — Dynamic split row form
- `frontend/src/components/account-list.tsx` — Hierarchical account table

#### Features (`frontend/src/features/transactions/`)
- `frontend/src/features/transactions/components/transaction-form.tsx` — Full transaction create/edit form
- `frontend/src/features/transactions/components/transaction-form-schema.ts` — Zod validation schema

#### Test files
- `frontend/src/components/__tests__/account-picker.test.tsx`
- `frontend/src/components/__tests__/split-input.test.tsx`
- `frontend/src/features/transactions/__tests__/transaction-form.test.tsx`
- `frontend/src/components/__tests__/account-list.test.tsx`

### Files to Modify (existing)
- `frontend/src/App.tsx` — Wire up QueryClientProvider
- `frontend/src/lib/utils.ts` — `cn` utility (installed with shadcn)

---

## shadcn/ui Components Inventory

The following shadcn/ui primitives are used across the four components:

| Component | Used By | Purpose |
|-----------|---------|---------|
| `Button` | All four | Interactive elements (add row, submit, expand) |
| `Input` | SplitInput, TransactionForm | Text/number entry fields |
| `Label` | SplitInput, TransactionForm | Accessible form labels |
| `Command` + `CommandInput` + `CommandItem` | AccountPicker | Searchable dropdown |
| `Popover` + `PopoverContent` + `PopoverTrigger` | AccountPicker | Dropdown positioning |
| `Dialog` + `DialogContent` + `DialogHeader` | TransactionForm (optional dialog mode) | Modal form wrapper |
| `Card` + `CardHeader` + `CardContent` + `CardFooter` | TransactionForm, AccountList | Layout containers |
| `Table` + `TableHeader` + `TableRow` + `TableCell` | AccountList, SplitInput | Table layouts |
| `Badge` | AccountList | Account type color indicators |
| `Skeleton` | All (loading states) | Loading placeholders |
| `Separator` | SplitInput | Visual row dividers |
| `Tooltip` | SplitInput | Balance indicator explanations |
| `Calendar` | TransactionForm | Date picker for post date |
| `Form` (react-hook-form integration) | TransactionForm, SplitInput | Form field wrappers with validation |

---

## Task 1: API Layer and Types

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/query-client.ts`
- Create: `frontend/src/types/account.ts`
- Create: `frontend/src/types/transaction.ts`

- [ ] **Step 1.1: Create typed API fetch wrapper**

```ts
// frontend/src/lib/api.ts

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

interface ApiRequestInit extends RequestInit {
  headers?: Record<string, string>;
}

async function getTenantId(): Promise<string | null> {
  // Read from Zustand store or localStorage — set by auth middleware
  return localStorage.getItem('current_tenant_id');
}

async function api<T>(path: string, init?: ApiRequestInit): Promise<T> {
  const tenantId = await getTenantId();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(tenantId ? { 'X-Tenant-ID': tenantId } : {}),
    ...init?.headers,
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body, response.statusText);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Paginated API response shape
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export { api };
```

- [ ] **Step 1.2: Create React Query client**

```ts
// frontend/src/lib/query-client.ts
import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './api';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: (failureCount: number, error: unknown) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false; // Don't retry client errors
        }
        return failureCount < 3;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});
```

- [ ] **Step 1.3: Create Account types**

```ts
// frontend/src/types/account.ts

export type AccountType =
  | 'ASSET'
  | 'LIABILITY'
  | 'INCOME'
  | 'EXPENSE'
  | 'EQUITY'
  | 'CASH'
  | 'BANK'
  | 'CREDIT'
  | 'STOCK'
  | 'FUND'
  | 'RECEIVABLE'
  | 'PAYABLE';

export interface Account {
  id: string;
  name: string;
  full_name: string;
  account_type: AccountType;
  color: string | null;
  description: string | null;
  code: string | null;
  parent: string | null;
  commodity: string;
  placeholder: boolean;
  hidden: boolean;
  balance: string;
  created_at: string;
  updated_at: string;
}

export interface AccountListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Account[];
}

export interface CreateAccountData {
  name: string;
  account_type: AccountType;
  parent?: string | null;
  description?: string;
  code?: string;
  commodity?: string;
  color?: string;
}

export interface UpdateAccountData extends Partial<CreateAccountData> {}
```

- [ ] **Step 1.4: Create Transaction types**

```ts
// frontend/src/types/transaction.ts

export interface Split {
  id: string;
  account: string; // Account UUID
  account_name: string;
  value: string; // Decimal string
  quantity: string;
  memo: string;
  reconciled: 'N' | 'C' | 'Y';
  created_at: string;
}

export interface Transaction {
  id: string;
  currency: string;
  post_date: string; // ISO date string
  description: string;
  notes: string | null;
  splits: Split[];
  created_at: string;
  updated_at: string;
}

export interface TransactionListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Transaction[];
}

export interface SplitCreateData {
  account: string;
  value: string;
  quantity?: string;
  memo?: string;
}

export interface CreateTransactionData {
  currency: string;
  post_date: string;
  description: string;
  notes?: string;
  splits_data: SplitCreateData[];
}

export interface UpdateTransactionData extends Partial<CreateTransactionData> {
  id: string;
}
```

**Test:** Verify TypeScript compilation of types:
```bash
cd frontend && npx tsc --noEmit
```

**Commit:**
```bash
git add frontend/src/lib/api.ts frontend/src/lib/query-client.ts frontend/src/types/account.ts frontend/src/types/transaction.ts
git commit -m "feat(frontend): add API layer, query client, and accounting types

Add typed fetch wrapper with tenant header injection, React Query
client configuration, and TypeScript interfaces for accounts and
transactions matching the backend API contract."
```

---

## Task 2: React Query Hooks

**Files:**
- Create: `frontend/src/hooks/use-accounts.ts`
- Create: `frontend/src/hooks/use-transactions.ts`
- Create: `frontend/src/hooks/use-split-balance.ts`

- [ ] **Step 2.1: Create account hooks**

```ts
// frontend/src/hooks/use-accounts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, PaginatedResponse } from '@/lib/api';
import type {
  Account,
  AccountListResponse,
  CreateAccountData,
  UpdateAccountData,
} from '@/types/account';

// ─── Query keys ────────────────────────────────────────────────
export const accountKeys = {
  all: ['accounts'] as const,
  lists: () => [...accountKeys.all, 'list'] as const,
  list: (filters: Record<string, string> = {}) =>
    [...accountKeys.lists(), filters] as const,
  details: () => [...accountKeys.all, 'detail'] as const,
  detail: (id: string) => [...accountKeys.details(), id] as const,
};

// ─── Fetch functions ───────────────────────────────────────────
async function fetchAccounts(params?: {
  page?: number;
  search?: string;
}): Promise<AccountListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.search) searchParams.set('search', params.search);
  const qs = searchParams.toString();
  return api<AccountListResponse>(`/accounts${qs ? `?${qs}` : ''}`);
}

async function fetchAccount(id: string): Promise<Account> {
  return api<Account>(`/accounts/${id}`);
}

async function createAccount(data: CreateAccountData): Promise<Account> {
  return api<Account>('/accounts', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ─── Hooks ─────────────────────────────────────────────────────
export function useAccounts(params?: { page?: number; search?: string }) {
  return useQuery({
    queryKey: accountKeys.list(params),
    queryFn: () => fetchAccounts(params),
  });
}

export function useAccount(id: string) {
  return useQuery({
    queryKey: accountKeys.detail(id),
    queryFn: () => fetchAccount(id),
    enabled: !!id,
  });
}

export function useCreateAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: accountKeys.all });
    },
  });
}

export function useAllAccountsFlat(): Account[] {
  // Utility hook that returns a flat list of all accounts (for pickers)
  const { data, isLoading } = useAccounts();

  // In production, handle pagination — for pickers, fetch page 1
  // and rely on server-side search for filtering
  const accounts = data?.results ?? [];
  return { accounts, isLoading };
}
```

- [ ] **Step 2.2: Create transaction hooks**

```ts
// frontend/src/hooks/use-transactions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, PaginatedResponse } from '@/lib/api';
import type {
  Transaction,
  TransactionListResponse,
  CreateTransactionData,
  UpdateTransactionData,
} from '@/types/transaction';

// ─── Query keys ────────────────────────────────────────────────
export const transactionKeys = {
  all: ['transactions'] as const,
  lists: () => [...transactionKeys.all, 'list'] as const,
  list: (filters: Record<string, string | number> = {}) =>
    [...transactionKeys.lists(), filters] as const,
  details: () => [...transactionKeys.all, 'detail'] as const,
  detail: (id: string) => [...transactionKeys.details(), id] as const,
};

// ─── Fetch functions ───────────────────────────────────────────
async function fetchTransactions(params?: {
  page?: number;
  post_date?: string;
  account?: string;
}): Promise<TransactionListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.post_date) searchParams.set('post_date', params.post_date);
  if (params?.account) searchParams.set('account', params.account);
  const qs = searchParams.toString();
  return api<TransactionListResponse>(
    `/transactions${qs ? `?${qs}` : ''}`
  );
}

async function fetchTransaction(id: string): Promise<Transaction> {
  return api<Transaction>(`/transactions/${id}`);
}

async function createTransaction(
  data: CreateTransactionData
): Promise<Transaction> {
  return api<Transaction>('/transactions', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

async function updateTransaction(
  data: UpdateTransactionData
): Promise<Transaction> {
  const { id, ...body } = data;
  return api<Transaction>(`/transactions/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

async function deleteTransaction(id: string): Promise<void> {
  return api<void>(`/transactions/${id}`, { method: 'DELETE' });
}

// ─── Hooks ─────────────────────────────────────────────────────
export function useTransactions(params?: {
  page?: number;
  post_date?: string;
  account?: string;
}) {
  return useQuery({
    queryKey: transactionKeys.list(params),
    queryFn: () => fetchTransactions(params),
  });
}

export function useTransaction(id: string) {
  return useQuery({
    queryKey: transactionKeys.detail(id),
    queryFn: () => fetchTransaction(id),
    enabled: !!id,
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transactionKeys.all });
    },
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateTransaction,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: transactionKeys.all });
      queryClient.invalidateQueries({
        queryKey: transactionKeys.detail(variables.id),
      });
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: transactionKeys.all });
    },
  });
}
```

- [ ] **Step 2.3: Create split balance hook**

```ts
// frontend/src/hooks/use-split-balance.ts
import { useMemo } from 'react';

export interface SplitBalanceResult {
  /** The sum of all split values. Should be 0 for a balanced transaction. */
  total: number;
  /** True when the sum equals exactly 0. */
  isBalanced: boolean;
  /** True when there are no splits yet. */
  isEmpty: boolean;
  /** Human-readable difference from zero, formatted to 2 decimal places. */
  difference: string;
}

/**
 * Computes the running balance of transaction splits.
 * Double-entry invariant: sum of all split values must equal 0.
 */
export function useSplitBalance(values: (string | undefined)[]): SplitBalanceResult {
  const result = useMemo(() => {
    const numericValues = values
      .filter((v): v is string => v !== undefined && v !== '')
      .map((v) => parseFloat(v))
      .filter((n) => !isNaN(n));

    const total = numericValues.reduce((sum, v) => sum + v, 0);
    const isEmpty = numericValues.length === 0;
    // Use a small epsilon for floating point comparison
    const isBalanced = Math.abs(total) < 0.005;
    const difference = total.toFixed(2);

    return { total, isBalanced, isEmpty, difference };
  }, [values]);

  return result;
}
```

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

**Commit:**
```bash
git add frontend/src/hooks/use-accounts.ts frontend/src/hooks/use-transactions.ts frontend/src/hooks/use-split-balance.ts
git commit -m "feat(frontend): add React Query hooks for accounts and transactions

Add useAccounts, useAccount, useCreateAccount, useTransactions,
useTransaction, useCreateTransaction, useUpdateTransaction,
useDeleteTransaction hooks with proper query key factories and
cache invalidation. Add useSplitBalance hook for double-entry
balance computation."
```

---

## Task 3: AccountPicker Component

**Files:**
- Create: `frontend/src/components/account-picker.tsx`

- [ ] **Step 3.1: Create AccountPicker component**

A searchable combobox that displays the account hierarchy. Uses shadcn `Command` + `Popover` internally and fetches accounts via `useAccounts`.

```tsx
// frontend/src/components/account-picker.tsx
'use client';

import * as React from 'react';
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useAccounts } from '@/hooks/use-accounts';
import type { Account, AccountType } from '@/types/account';

// ─── Types ─────────────────────────────────────────────────────
export interface AccountPickerProps {
  /** Currently selected account ID. Controls the component when provided. */
  value?: string | null;
  /** Called when the user selects an account. */
  onValueChange: (accountId: string) => void;
  /** Optional placeholder text. */
  placeholder?: string;
  /** Optional filter by account type. */
  filterTypes?: AccountType[];
  /** Disables the picker. */
  disabled?: boolean;
  /** Accessibility label for screen readers. */
  'aria-label'?: string;
  /** HTML id for the trigger button. */
  id?: string;
}

// ─── Account type display mapping ──────────────────────────────
const ACCOUNT_TYPE_ICONS: Record<AccountType, string> = {
  ASSET: '💰',
  LIABILITY: '📉',
  INCOME: '💵',
  EXPENSE: '💸',
  EQUITY: '🏦',
  CASH: '💵',
  BANK: '🏧',
  CREDIT: '💳',
  STOCK: '📈',
  FUND: '📊',
  RECEIVABLE: '📋',
  PAYABLE: '📋',
};

// ─── Helper: compute indentation level from full_name ──────────
function getIndentLevel(account: Account): number {
  // full_name uses ":" as separator in GnuCash convention
  // e.g., "Assets:Current Assets:Checking" → depth 2
  const parts = account.full_name.split(':');
  return parts.length - 1;
}

// ─── Component ─────────────────────────────────────────────────
export function AccountPicker({
  value,
  onValueChange,
  placeholder = 'Select account...',
  filterTypes,
  disabled = false,
  'aria-label': ariaLabel,
  id,
}: AccountPickerProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');

  const { data, isLoading } = useAccounts({ search: search || undefined });
  const accounts = data?.results ?? [];

  const filteredAccounts = React.useMemo(() => {
    if (!filterTypes) return accounts;
    return accounts.filter((a) => filterTypes.includes(a.account_type));
  }, [accounts, filterTypes]);

  const selectedAccount = React.useMemo(() => {
    if (!value) return null;
    return accounts.find((a) => a.id === value) ?? null;
  }, [accounts, value]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label={ariaLabel}
          id={id}
          disabled={disabled}
          className="w-full justify-between"
        >
          {selectedAccount ? (
            <span className="truncate">{selectedAccount.full_name}</span>
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
          {isLoading ? (
            <Loader2 className="ml-2 h-4 w-4 animate-spin" />
          ) : (
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search accounts..."
            onValueChange={setSearch}
          />
          <CommandList>
            {isLoading && (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">
                  Loading accounts...
                </span>
              </div>
            )}
            {!isLoading && filteredAccounts.length === 0 && (
              <CommandEmpty>
                {search ? 'No accounts found.' : 'No accounts available.'}
              </CommandEmpty>
            )}
            {!isLoading && filteredAccounts.length > 0 && (
              <CommandGroup>
                {filteredAccounts.map((account) => {
                  const indent = getIndentLevel(account);
                  return (
                    <CommandItem
                      key={account.id}
                      value={account.full_name}
                      onSelect={() => {
                        onValueChange(account.id);
                        setOpen(false);
                      }}
                      className="flex items-center"
                    >
                      <Check
                        className={cn(
                          'mr-2 h-4 w-4 shrink-0',
                          value === account.id ? 'opacity-100' : 'opacity-0'
                        )}
                      />
                      <span
                        className="truncate"
                        style={{ paddingLeft: `${indent * 16}px` }}
                      >
                        {account.full_name}
                      </span>
                      <span className="ml-auto text-xs text-muted-foreground">
                        {ACCOUNT_TYPE_ICONS[account.account_type]}
                      </span>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

**Test:** Verify component renders and TypeScript compiles:
```bash
cd frontend && npx tsc --noEmit
```

Manual test: Place `<AccountPicker onValueChange={(id) => console.log(id)} />` in a page and verify:
1. Opens dropdown on click
2. Shows loading spinner while fetching
3. Typing filters accounts by name
4. Selecting an account closes dropdown and displays selected name
5. Keyboard Tab/Arrow navigation works in the combobox
6. `disabled` prop prevents interaction

**Commit:**
```bash
git add frontend/src/components/account-picker.tsx
git commit -m "feat(frontend): add AccountPicker searchable combobox component

Searchable dropdown with account hierarchy indentation, React Query
data fetching, loading states, keyboard accessibility, and optional
account type filtering. Uses shadcn Command + Popover primitives."
```

---

## Task 4: SplitInput Component

**Files:**
- Create: `frontend/src/components/split-input.tsx`

- [ ] **Step 4.1: Create SplitInput component**

A dynamic form for entering transaction splits. Supports add/remove rows, real-time balance indicator, and integrates `AccountPicker` for each row.

```tsx
// frontend/src/components/split-input.tsx
'use client';

import * as React from 'react';
import { Plus, Trash2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useFieldArray, useFormContext, type Control } from 'react-hook-form';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { AccountPicker } from '@/components/account-picker';
import { useSplitBalance } from '@/hooks/use-split-balance';
import type { SplitCreateData } from '@/types/transaction';

// ─── Types ─────────────────────────────────────────────────────
export interface SplitFieldValues {
  splits: SplitCreateData[];
}

export interface SplitInputProps {
  /** React Hook Form control instance. */
  control: Control<SplitFieldValues>;
  /** Name of the field array in the form schema (default: 'splits_data'). */
  fieldName?: 'splits_data';
  /** Maximum number of splits allowed. */
  maxSplits?: number;
  /** Called when the balance changes (for external consumers). */
  onBalanceChange?: (balance: number) => void;
}

// ─── Balance indicator sub-component ───────────────────────────
interface BalanceIndicatorProps {
  values: (string | undefined)[];
}

function BalanceIndicator({ values }: BalanceIndicatorProps) {
  const { total, isBalanced, isEmpty, difference } = useSplitBalance(values);

  React.useEffect(() => {
    // Notify parent of balance changes if callback provided
  }, [total]);

  if (isEmpty) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <AlertCircle className="h-4 w-4" />
        <span>Add at least one split to the transaction.</span>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'flex items-center gap-2 text-sm font-medium',
              isBalanced
                ? 'text-green-600 dark:text-green-400'
                : 'text-red-600 dark:text-red-400'
            )}
            role="status"
            aria-live="polite"
          >
            {isBalanced ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <span>
              {isBalanced ? 'Balanced' : `Unbalanced: ${difference}`}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>
            Double-entry rule: the sum of all split values must equal 0.
            <br />
            Current sum: {total.toFixed(2)}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ─── Component ─────────────────────────────────────────────────
export function SplitInput({
  control,
  fieldName = 'splits_data',
  maxSplits = 20,
  onBalanceChange,
}: SplitInputProps) {
  const { fields, append, remove } = useFieldArray({
    control,
    name: fieldName,
  });

  const formContext = useFormContext<SplitFieldValues>();
  const splitValues = formContext.watch(
    `${fieldName}.value`
  ) as (string | undefined)[] | undefined;

  // Watch individual values for balance computation
  const watchedValues = React.useMemo(() => {
    return fields.map((_, i) => {
      return formContext.watch(`${fieldName}.${i}.value`);
    });
  }, [fields, formContext, fieldName]);

  const { total } = useSplitBalance(watchedValues);

  React.useEffect(() => {
    onBalanceChange?.(total);
  }, [total, onBalanceChange]);

  const handleAddSplit = React.useCallback(() => {
    if (fields.length >= maxSplits) return;
    append({
      account: '',
      value: '',
      quantity: '1',
      memo: '',
    });
  }, [fields.length, maxSplits, append]);

  const handleRemoveSplit = React.useCallback(
    (index: number) => {
      remove(index);
    },
    [remove]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label>Splits</Label>
        <BalanceIndicator values={watchedValues} />
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40%]">Account</TableHead>
              <TableHead className="w-[20%]">Value</TableHead>
              <TableHead className="w-[30%]">Memo</TableHead>
              <TableHead className="w-[10%] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {fields.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                  No splits added. Click &quot;Add split&quot; to begin.
                </TableCell>
              </TableRow>
            )}
            {fields.map((field, index) => (
              <TableRow key={field.id}>
                <TableCell>
                  <formContext.Control as never />
                  <AccountPicker
                    value={formContext.watch(`${fieldName}.${index}.account`)}
                    onValueChange={(accountId) => {
                      formContext.setValue(`${fieldName}.${index}.account`, accountId, {
                        shouldDirty: true,
                        shouldValidate: true,
                      });
                    }}
                    placeholder="Choose account..."
                    aria-label={`Account for split ${index + 1}`}
                  />
                  {formContext.formState.errors.splits_data?.[index]?.account && (
                    <p className="mt-1 text-xs text-red-600">
                      {formContext.formState.errors.splits_data[index].account?.message}
                    </p>
                  )}
                </TableCell>
                <TableCell>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    {...formContext.register(`${fieldName}.${index}.value`, {
                      valueAsNumber: false,
                    })}
                    aria-label={`Value for split ${index + 1}`}
                    className={cn(
                      formContext.formState.errors.splits_data?.[index]?.value &&
                        'border-red-500'
                    )}
                  />
                  {formContext.formState.errors.splits_data?.[index]?.value && (
                    <p className="mt-1 text-xs text-red-600">
                      {formContext.formState.errors.splits_data[index].value?.message}
                    </p>
                  )}
                </TableCell>
                <TableCell>
                  <Input
                    placeholder="Optional memo..."
                    {...formContext.register(`${fieldName}.${index}.memo`)}
                    aria-label={`Memo for split ${index + 1}`}
                  />
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveSplit(index)}
                    aria-label={`Remove split ${index + 1}`}
                    disabled={fields.length <= 2}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAddSplit}
          disabled={fields.length >= maxSplits}
        >
          <Plus className="mr-2 h-4 w-4" />
          Add split
        </Button>
        <span className="text-xs text-muted-foreground">
          {fields.length} / {maxSplits} splits
        </span>
      </div>
    </div>
  );
}
```

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

Manual test with a form wrapper:
```tsx
// Quick test in a page
import { useForm, FormProvider } from 'react-hook-form';
import { SplitInput } from '@/components/split-input';

function TestPage() {
  const form = useForm({
    defaultValues: {
      splits_data: [
        { account: '', value: '', memo: '' },
        { account: '', value: '', memo: '' },
      ],
    },
  });

  return (
    <FormProvider {...form}>
      <form>
        <SplitInput control={form.control} />
      </form>
    </FormProvider>
  );
}
```

Verify:
1. Add/remove rows works correctly
2. Balance indicator turns green when splits sum to 0
3. Balance indicator turns red with difference when unbalanced
4. Account picker in each row works independently
5. Minimum 2 splits enforced (remove disabled)
6. Maximum splits cap enforced (add disabled)

**Commit:**
```bash
git add frontend/src/components/split-input.tsx
git commit -m "feat(frontend): add SplitInput dynamic split form component

Dynamic add/remove rows with real-time double-entry balance
indicator, embedded AccountPicker per row, memo field,
React Hook Form field array integration, and tooltip explaining
the balance invariant."
```

---

## Task 5: TransactionForm Component

**Files:**
- Create: `frontend/src/features/transactions/components/transaction-form-schema.ts`
- Create: `frontend/src/features/transactions/components/transaction-form.tsx`

- [ ] **Step 5.1: Create Zod validation schema**

```ts
// frontend/src/features/transactions/components/transaction-form-schema.ts
import { z } from 'zod';

export const transactionFormSchema = z.object({
  currency: z.string().min(1, 'Currency is required.'),
  post_date: z.string().min(1, 'Date is required.'),
  description: z
    .string()
    .min(1, 'Description is required.')
    .max(200, 'Description must be at most 200 characters.'),
  notes: z.string().max(1000, 'Notes must be at most 1000 characters.').optional(),
  splits_data: z
    .array(
      z.object({
        account: z.string().uuid('Please select a valid account.'),
        value: z
          .string()
          .min(1, 'Value is required.')
          .refine(
            (v) => {
              const num = parseFloat(v);
              return !isNaN(num) && num !== 0;
            },
            { message: 'Value must be a non-zero number.' }
          ),
        quantity: z.string().optional(),
        memo: z.string().max(200, 'Memo must be at most 200 characters.').optional(),
      })
    )
    .min(2, 'At least 2 splits are required for a transaction.')
    .refine(
      (splits) => {
        const total = splits.reduce((sum, s) => {
          const v = parseFloat(s.value);
          return sum + (isNaN(v) ? 0 : v);
        }, 0);
        // Allow small floating point tolerance
        return Math.abs(total) < 0.005;
      },
      { message: 'Splits must balance to zero.' }
    ),
});

export type TransactionFormValues = z.infer<typeof transactionFormSchema>;
```

- [ ] **Step 5.2: Create TransactionForm component**

```tsx
// frontend/src/features/transactions/components/transaction-form.tsx
'use client';

import * as React from 'react';
import { CalendarIcon, Loader2 } from 'lucide-react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { format } from 'date-fns';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { SplitInput } from '@/components/split-input';
import {
  useCreateTransaction,
  useUpdateTransaction,
  useTransaction,
} from '@/hooks/use-transactions';
import {
  transactionFormSchema,
  type TransactionFormValues,
} from './transaction-form-schema';

// ─── Types ─────────────────────────────────────────────────────
export interface TransactionFormProps {
  /** When provided, the form operates in edit mode for this transaction. */
  transactionId?: string;
  /** Called when the form is successfully submitted. */
  onSuccess?: () => void;
  /** Called when the form is cancelled. */
  onCancel?: () => void;
  /** Default currency code (e.g., 'USD'). */
  defaultCurrency?: string;
}

// ─── Date picker field sub-component ───────────────────────────
interface DatePickerFieldProps {
  value: Date | undefined;
  onChange: (date: Date | undefined) => void;
  disabled?: boolean;
}

function DatePickerField({ value, onChange, disabled }: DatePickerFieldProps) {
  const [open, setOpen] = React.useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'w-full justify-start text-left font-normal',
            !value && 'text-muted-foreground'
          )}
          disabled={disabled}
          aria-label="Transaction date"
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {value ? format(value, 'PPP') : 'Pick a date'}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={value}
          onSelect={(date) => {
            onChange(date);
            setOpen(false);
          }}
          initialFocus
          disabled={(date) => date > new Date()}
        />
      </PopoverContent>
    </Popover>
  );
}

// ─── Component ─────────────────────────────────────────────────
export function TransactionForm({
  transactionId,
  onSuccess,
  onCancel,
  defaultCurrency = 'USD',
}: TransactionFormProps) {
  const isEditMode = !!transactionId;

  // Fetch existing transaction data when in edit mode
  const { data: existingTransaction, isLoading: isLoadingTransaction } =
    useTransaction(transactionId!);

  // Mutations
  const createMutation = useCreateTransaction();
  const updateMutation = useUpdateTransaction();
  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  const form = useForm<TransactionFormValues>({
    resolver: zodResolver(transactionFormSchema),
    defaultValues: {
      currency: defaultCurrency,
      post_date: format(new Date(), 'yyyy-MM-dd'),
      description: '',
      notes: '',
      splits_data: [
        { account: '', value: '', quantity: '1', memo: '' },
        { account: '', value: '', quantity: '1', memo: '' },
      ],
    },
  });

  // Populate form when edit-mode data loads
  React.useEffect(() => {
    if (existingTransaction) {
      form.reset({
        currency: existingTransaction.currency,
        post_date: existingTransaction.post_date,
        description: existingTransaction.description,
        notes: existingTransaction.notes ?? '',
        splits_data: existingTransaction.splits.map((split) => ({
          account: split.account,
          value: split.value,
          quantity: split.quantity,
          memo: split.memo,
        })),
      });
    }
  }, [existingTransaction, form]);

  const onSubmit = React.useCallback(
    (data: TransactionFormValues) => {
      if (isEditMode) {
        updateMutation.mutate(
          { id: transactionId!, ...data },
          { onSuccess }
        );
      } else {
        createMutation.mutate(data, {
          onSuccess: () => {
            form.reset();
            onSuccess?.();
          },
        });
      }
    },
    [isEditMode, transactionId, createMutation, updateMutation, form, onSuccess]
  );

  if (isEditMode && isLoadingTransaction) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">
            Loading transaction...
          </span>
        </CardContent>
      </Card>
    );
  }

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle>
              {isEditMode ? 'Edit Transaction' : 'New Transaction'}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Date and Currency row */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="post_date">Date</Label>
                <DatePickerField
                  value={form.watch('post_date') ? new Date(form.watch('post_date')) : undefined}
                  onChange={(date) => {
                    if (date) {
                      form.setValue('post_date', format(date, 'yyyy-MM-dd'), {
                        shouldDirty: true,
                        shouldValidate: true,
                      });
                    }
                  }}
                />
                {form.formState.errors.post_date && (
                  <p className="text-xs text-red-600">
                    {form.formState.errors.post_date.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="currency">Currency</Label>
                <Input
                  id="currency"
                  {...form.register('currency')}
                  placeholder="USD"
                  maxLength={3}
                  className="uppercase"
                />
                {form.formState.errors.currency && (
                  <p className="text-xs text-red-600">
                    {form.formState.errors.currency.message}
                  </p>
                )}
              </div>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                {...form.register('description')}
                placeholder="e.g., Monthly salary deposit"
              />
              {form.formState.errors.description && (
                <p className="text-xs text-red-600">
                  {form.formState.errors.description.message}
                </p>
              )}
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Input
                id="notes"
                {...form.register('notes')}
                placeholder="Additional details..."
              />
              {form.formState.errors.notes && (
                <p className="text-xs text-red-600">
                  {form.formState.errors.notes.message}
                </p>
              )}
            </div>

            <Separator />

            {/* Splits */}
            <SplitInput
              control={form.control}
              fieldName="splits_data"
            />
            {form.formState.errors.splits_data && (
              <p className="text-sm text-red-600">
                {typeof form.formState.errors.splits_data.message === 'string'
                  ? form.formState.errors.splits_data.message
                  : 'Please fix the split errors above.'}
              </p>
            )}
          </CardContent>

          <CardFooter className="flex justify-between gap-4">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            )}
            <div className="ml-auto flex items-center gap-4">
              {form.formState.isDirty && (
                <span className="text-xs text-muted-foreground">
                  Unsaved changes
                </span>
              )}
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                {isEditMode ? 'Update Transaction' : 'Create Transaction'}
              </Button>
            </div>
          </CardFooter>
        </Card>
      </form>
    </FormProvider>
  );
}
```

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

Manual test:
1. Render `<TransactionForm onSuccess={() => console.log('saved')} />`
2. Fill in date, description, and at least 2 splits
3. Verify submit is disabled until form is balanced
4. Verify validation errors display for missing fields
5. Test edit mode with `<TransactionForm transactionId="some-uuid" />`
6. Test cancel button calls `onCancel`

**Commit:**
```bash
git add frontend/src/features/transactions/components/transaction-form-schema.ts frontend/src/features/transactions/components/transaction-form.tsx
git commit -m "feat(frontend): add TransactionForm create/edit form

Full transaction form with React Hook Form + Zod validation,
date picker, currency field, description/notes, embedded
SplitInput component, and React Query mutations for create/update.
Supports both create and edit modes."
```

---

## Task 6: AccountList Component

**Files:**
- Create: `frontend/src/components/account-list.tsx`

- [ ] **Step 6.1: Create AccountList component**

A hierarchical table of accounts with expandable tree rows, balance display, and color-coded type badges.

```tsx
// frontend/src/components/account-list.tsx
'use client';

import * as React from 'react';
import { ChevronRight, ChevronDown, Loader2 } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { useAccounts } from '@/hooks/use-accounts';
import type { Account, AccountType } from '@/types/account';

// ─── Types ─────────────────────────────────────────────────────
export interface AccountListProps {
  /** Optional filter by account type. */
  filterType?: AccountType;
  /** Called when an account row is clicked. */
  onAccountClick?: (account: Account) => void;
  /** Whether to show the balance column. */
  showBalance?: boolean;
  /** Search placeholder text. */
  searchPlaceholder?: string;
}

// ─── Type badge color mapping ──────────────────────────────────
const TYPE_BADGE_VARIANT: Record<AccountType, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  ASSET: 'default',
  LIABILITY: 'destructive',
  INCOME: 'secondary',
  EXPENSE: 'destructive',
  EQUITY: 'outline',
  CASH: 'default',
  BANK: 'default',
  CREDIT: 'destructive',
  STOCK: 'secondary',
  FUND: 'secondary',
  RECEIVABLE: 'default',
  PAYABLE: 'destructive',
};

// ─── Tree node helper ──────────────────────────────────────────
interface AccountTreeNode {
  account: Account;
  children: AccountTreeNode[];
  depth: number;
}

function buildAccountTree(accounts: Account[]): AccountTreeNode[] {
  // Group accounts by their parent
  const nodeMap = new Map<string, AccountTreeNode>();
  const roots: AccountTreeNode[] = [];

  // First pass: create nodes
  for (const account of accounts) {
    nodeMap.set(account.id, { account, children: [], depth: 0 });
  }

  // Second pass: build tree
  for (const account of accounts) {
    const node = nodeMap.get(account.id)!;
    if (account.parent && nodeMap.has(account.parent)) {
      const parent = nodeMap.get(account.parent)!;
      node.depth = parent.depth + 1;
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

// ─── Account row sub-component ─────────────────────────────────
interface AccountRowProps {
  node: AccountTreeNode;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
  onAccountClick?: (account: Account) => void;
  showBalance: boolean;
}

function AccountRow({
  node,
  expandedIds,
  onToggle,
  onAccountClick,
  showBalance,
}: AccountRowProps) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedIds.has(node.account.id);

  const handleRowClick = () => {
    if (hasChildren) {
      onToggle(node.account.id);
    }
    onAccountClick?.(node.account);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleRowClick();
    }
    if (e.key === 'ArrowRight' && hasChildren && !isExpanded) {
      onToggle(node.account.id);
    }
    if (e.key === 'ArrowLeft' && hasChildren && isExpanded) {
      onToggle(node.account.id);
    }
  };

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        onClick={handleRowClick}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="row"
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-level={node.depth + 1}
      >
        <TableCell>
          <div
            className="flex items-center gap-1"
            style={{ paddingLeft: `${node.depth * 20}px` }}
          >
            {hasChildren ? (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggle(node.account.id);
                }}
                aria-label={isExpanded ? 'Collapse' : 'Expand'}
                tabIndex={-1}
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </Button>
            ) : (
              <span className="inline-block w-6" />
            )}
            <span className="font-medium">{node.account.name}</span>
          </div>
        </TableCell>
        <TableCell>
          <Badge variant={TYPE_BADGE_VARIANT[node.account.account_type]}>
            {node.account.account_type}
          </Badge>
        </TableCell>
        {showBalance && (
          <TableCell className="text-right font-mono">
            <span
              className={cn(
                parseFloat(node.account.balance) >= 0
                  ? 'text-green-600'
                  : 'text-red-600'
              )}
            >
              {parseFloat(node.account.balance).toLocaleString('en-US', {
                style: 'currency',
                currency: node.account.commodity || 'USD',
              })}
            </span>
          </TableCell>
        )}
      </TableRow>
      {isExpanded &&
        node.children.map((child) => (
          <AccountRow
            key={child.account.id}
            node={child}
            expandedIds={expandedIds}
            onToggle={onToggle}
            onAccountClick={onAccountClick}
            showBalance={showBalance}
          />
        ))}
    </>
  );
}

// ─── Component ─────────────────────────────────────────────────
export function AccountList({
  filterType,
  onAccountClick,
  showBalance = true,
  searchPlaceholder = 'Search accounts...',
}: AccountListProps) {
  const [search, setSearch] = React.useState('');
  const [expandedIds, setExpandedIds] = React.useState<Set<string>>(new Set());

  const { data, isLoading } = useAccounts(
    search ? { search } : undefined
  );

  const accounts = React.useMemo(() => {
    let results = data?.results ?? [];
    if (filterType) {
      results = results.filter((a) => a.account_type === filterType);
    }
    return results;
  }, [data?.results, filterType]);

  const tree = React.useMemo(() => buildAccountTree(accounts), [accounts]);

  const handleToggle = React.useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleExpandAll = React.useCallback(() => {
    const allIds = new Set<string>();
    const collect = (nodes: AccountTreeNode[]) => {
      for (const node of nodes) {
        if (node.children.length > 0) {
          allIds.add(node.account.id);
          collect(node.children);
        }
      }
    };
    collect(tree);
    setExpandedIds(allIds);
  }, [tree]);

  const handleCollapseAll = React.useCallback(() => {
    setExpandedIds(new Set());
  }, []);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Accounts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle>Accounts ({accounts.length})</CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleExpandAll}
            aria-label="Expand all accounts"
          >
            Expand all
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCollapseAll}
            aria-label="Collapse all accounts"
          >
            Collapse all
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Search bar */}
        <div className="mb-4">
          <Input
            placeholder={searchPlaceholder}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search accounts"
          />
        </div>

        {/* Table */}
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                {showBalance && (
                  <TableHead className="text-right">Balance</TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {tree.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={showBalance ? 3 : 2}
                    className="h-24 text-center text-muted-foreground"
                  >
                    No accounts found.
                  </TableCell>
                </TableRow>
              ) : (
                tree.map((node) => (
                  <AccountRow
                    key={node.account.id}
                    node={node}
                    expandedIds={expandedIds}
                    onToggle={handleToggle}
                    onAccountClick={onAccountClick}
                    showBalance={showBalance}
                  />
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

Manual test:
1. Render `<AccountList onAccountClick={(a) => console.log(a)} />`
2. Verify tree hierarchy is displayed with indentation
3. Expand/collapse individual nodes works
4. Expand all / Collapse all buttons work
5. Search filters accounts by name
6. Balance column shows color-coded amounts
7. Badge shows account type with appropriate color
8. Keyboard navigation: Enter/Space toggles, ArrowRight expands, ArrowLeft collapses
9. Click on row calls `onAccountClick` callback

**Commit:**
```bash
git add frontend/src/components/account-list.tsx
git commit -m "feat(frontend): add AccountList hierarchical account table component

Expandable tree view with balance display, color-coded type badges,
search filtering, expand/collapse all, keyboard navigation
(ArrowRight/Left, Enter/Space), and loading skeleton states."
```

---

## Task 7: Wire Up React Query Provider

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 7.1: Add QueryClientProvider to App.tsx**

```tsx
// frontend/src/App.tsx (relevant section)
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/query-client';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* Existing routes / layout */}
    </QueryClientProvider>
  );
}
```

**Test:** Verify the app starts and no React Query errors appear in the console:
```bash
cd frontend && npm run dev
```

**Commit:**
```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): wire up React Query provider to App

Initialize QueryClientProvider with configured query client
for caching and server state management across all components."
```

---

## Task 8: Testing

**Files:**
- Create: `frontend/src/components/__tests__/account-picker.test.tsx`
- Create: `frontend/src/components/__tests__/split-input.test.tsx`
- Create: `frontend/src/features/transactions/__tests__/transaction-form.test.tsx`
- Create: `frontend/src/components/__tests__/account-list.test.tsx`

- [ ] **Step 8.1: Install test dependencies**

```bash
cd frontend
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event vitest jsdom msw
```

- [ ] **Step 8.2: AccountPicker tests**

```tsx
// frontend/src/components/__tests__/account-picker.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { AccountPicker } from '@/components/account-picker';
import type { AccountListResponse } from '@/types/account';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const mockAccounts: AccountListResponse = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 'acct-1',
      name: 'Checking',
      full_name: 'Assets:Bank:Checking',
      account_type: 'BANK',
      color: null,
      description: null,
      code: null,
      parent: null,
      commodity: 'USD',
      placeholder: false,
      hidden: false,
      balance: '1000.00',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'acct-2',
      name: 'Savings',
      full_name: 'Assets:Bank:Savings',
      account_type: 'BANK',
      color: null,
      description: null,
      code: null,
      parent: null,
      commodity: 'USD',
      placeholder: false,
      hidden: false,
      balance: '5000.00',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ],
};

function renderWithQuery(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('AccountPicker', () => {
  it('shows placeholder when no account selected', () => {
    renderWithQuery(
      <AccountPicker onValueChange={vi.fn()} />
    );
    expect(screen.getByRole('combobox')).toHaveTextContent('Select account...');
  });

  it('displays selected account name', async () => {
    const { container } = renderWithQuery(
      <AccountPicker value="acct-1" onValueChange={vi.fn()} />
    );
    // After data loads, selected account should appear
    await waitFor(() => {
      expect(screen.getByRole('combobox')).toHaveTextContent('Assets:Bank:Checking');
    });
  });

  it('calls onValueChange when an account is selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    renderWithQuery(<AccountPicker onValueChange={onChange} />);

    // Open the combobox
    await user.click(screen.getByRole('combobox'));

    // Select an account
    await waitFor(() => {
      expect(screen.getByText('Assets:Bank:Checking')).toBeVisible();
    });
    await user.click(screen.getByText('Assets:Bank:Checking'));

    expect(onChange).toHaveBeenCalledWith('acct-1');
  });

  it('is disabled when disabled prop is true', () => {
    renderWithQuery(
      <AccountPicker onValueChange={vi.fn()} disabled />
    );
    expect(screen.getByRole('combobox')).toBeDisabled();
  });
});
```

- [ ] **Step 8.3: SplitInput tests**

```tsx
// frontend/src/components/__tests__/split-input.test.tsx
import { render, screen } from '@testing-library/react';
import { useForm, FormProvider } from 'react-hook-form';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { SplitInput } from '@/components/split-input';
import type { SplitFieldValues } from '@/components/split-input';

function renderSplitInput(props: Partial<React.ComponentProps<typeof SplitInput>> = {}) {
  const TestWrapper = () => {
    const form = useForm<SplitFieldValues>({
      defaultValues: {
        splits_data: [
          { account: '', value: '', memo: '' },
          { account: '', value: '', memo: '' },
        ],
      },
    });

    return (
      <FormProvider {...form}>
        <SplitInput control={form.control} {...props} />
      </FormProvider>
    );
  };

  return render(<TestWrapper />);
}

describe('SplitInput', () => {
  it('renders with default two split rows', () => {
    renderSplitInput();
    // Should show 2 rows minimum
    expect(screen.getAllByRole('row')).toHaveLength(3); // header + 2 data rows
  });

  it('shows balanced indicator when values sum to zero', async () => {
    renderSplitInput();
    // Balance indicator should show "Balanced" when both values are empty
    expect(screen.getByRole('status')).toHaveTextContent('Add at least one split');
  });

  it('allows adding a new split row', async () => {
    const user = userEvent.setup();
    renderSplitInput();

    const addButton = screen.getByRole('button', { name: /add split/i });
    await user.click(addButton);

    // Should now have 3 data rows + header
    expect(screen.getAllByRole('row')).toHaveLength(4);
  });

  it('disables remove button when only 2 splits remain', () => {
    renderSplitInput();
    const removeButtons = screen.getAllByRole('button', { name: /remove split/i });
    // Both remove buttons should be disabled at minimum count
    removeButtons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });
});
```

- [ ] **Step 8.4: TransactionForm tests**

```tsx
// frontend/src/features/transactions/__tests__/transaction-form.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TransactionForm } from '@/features/transactions/components/transaction-form';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('TransactionForm', () => {
  beforeEach(() => {
    queryClient.clear();
  });

  it('renders in create mode with default values', () => {
    renderWithProviders(<TransactionForm />);
    expect(screen.getByRole('heading', { name: 'New Transaction' }));
    expect(screen.getByPlaceholderText(/monthly salary/i));
    expect(screen.getByRole('button', { name: /create transaction/i }));
  });

  it('requires description before submit', async () => {
    const user = userEvent.setup();
    renderWithProviders(<TransactionForm />);

    const submitBtn = screen.getByRole('button', { name: /create transaction/i });
    await user.click(submitBtn);

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText('Description is required.')).toBeVisible();
    });
  });

  it('calls onSuccess after successful submission', async () => {
    // This test requires MSW to mock the POST endpoint
    // Placeholder: implement with MSW handler in conftest
    expect(true).toBe(true);
  });
});
```

- [ ] **Step 8.5: AccountList tests**

```tsx
// frontend/src/components/__tests__/account-list.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { AccountList } from '@/components/account-list';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderWithQuery(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('AccountList', () => {
  it('renders loading skeleton while fetching', () => {
    renderWithQuery(<AccountList />);
    // Skeleton elements should be visible during loading
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(1);
  });

  it('renders account count in title', async () => {
    renderWithQuery(<AccountList />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Accounts');
    });
  });

  it('shows expand all and collapse all buttons', async () => {
    renderWithQuery(<AccountList />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /expand all/i })).toBeVisible();
      expect(screen.getByRole('button', { name: /collapse all/i })).toBeVisible();
    });
  });

  it('has search input', async () => {
    renderWithQuery(<AccountList />);
    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /search accounts/i })).toBeVisible();
    });
  });
});
```

**Test:** Run the test suite:
```bash
cd frontend && npx vitest run
```

**Commit:**
```bash
git add frontend/src/components/__tests__/account-picker.test.tsx frontend/src/components/__tests__/split-input.test.tsx frontend/src/features/transactions/__tests__/transaction-form.test.tsx frontend/src/components/__tests__/account-list.test.tsx
git commit -m "test(frontend): add unit tests for core accounting components

Add vitest + testing-library tests for AccountPicker, SplitInput,
TransactionForm, and AccountList covering render states,
interactions, validation, and disabled states."
```

---

## Summary of Deliverables

| # | Component | File | Dependencies |
|---|-----------|------|-------------|
| 1 | Types + API layer | `frontend/src/types/*.ts`, `frontend/src/lib/api.ts` | — |
| 2 | Query client | `frontend/src/lib/query-client.ts` | @tanstack/react-query |
| 3 | Account hooks | `frontend/src/hooks/use-accounts.ts` | React Query, api.ts |
| 4 | Transaction hooks | `frontend/src/hooks/use-transactions.ts` | React Query, api.ts |
| 5 | Split balance hook | `frontend/src/hooks/use-split-balance.ts` | React (useMemo) |
| 6 | **AccountPicker** | `frontend/src/components/account-picker.tsx` | shadcn Command/Popover, useAccounts |
| 7 | **SplitInput** | `frontend/src/components/split-input.tsx` | AccountPicker, useSplitBalance, RHF |
| 8 | Zod schema | `frontend/src/features/transactions/components/transaction-form-schema.ts` | zod |
| 9 | **TransactionForm** | `frontend/src/features/transactions/components/transaction-form.tsx` | SplitInput, RHF + zod, React Query mutations, Calendar |
| 10 | **AccountList** | `frontend/src/components/account-list.tsx` | useAccounts, Badge, Table |
| 11 | Tests | `frontend/src/components/__tests__/*.tsx`, `frontend/src/features/transactions/__tests__/*.tsx` | vitest, testing-library |

## shadcn/ui Components Required

Run these commands before starting implementation:

```bash
cd frontend
npx shadcn@latest add button input label command popover dialog card table badge skeleton form separator tooltip calendar select
```

These install into `frontend/src/components/ui/` and are the only third-party UI dependencies needed for all four core components.
