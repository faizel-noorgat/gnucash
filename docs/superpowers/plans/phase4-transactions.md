# Phase 4: Transaction Pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the transaction list, create, and detail pages that wire the existing `TransactionForm` into full-screen pages with proper routing, pagination, and edit support.

**Architecture:** React 18 + TypeScript (strict) + Vite. shadcn/ui for primitives, React Query for server state, React Hook Form + Zod for form state. Components compose from Phase 3 (`TransactionForm`, `SplitInput`, `AccountPicker`).

**Tech Stack:** React 18, TypeScript, Tailwind CSS, shadcn/ui, @tanstack/react-query v5, react-router-dom v6, react-hook-form + zod, lucide-react

---

## Prerequisites: Install Missing shadcn/ui Primitives

Install `skeleton` and `badge` if not already present:

```bash
cd frontend
npx shadcn@latest add skeleton badge
```

---

## File Map

### Files to Create
- `frontend/src/routes/TransactionNewPage.tsx` — New transaction page, wraps `TransactionForm`
- `frontend/src/routes/TransactionListPage.tsx` — Paginated transaction list with date filter
- `frontend/src/routes/TransactionDetailPage.tsx` — View/edit single transaction

### Files to Modify
- `frontend/src/features/transactions/components/transaction-form.tsx` — Add edit mode via `transactionId` prop and `useUpdateTransaction`
- `frontend/src/hooks/use-transactions.ts` — Add `useUpdateTransaction` hook
- `frontend/src/App.tsx` — Replace transaction placeholder with routes

---

## Task 1: Add `useUpdateTransaction` Hook

**File:** `frontend/src/hooks/use-transactions.ts`

- [ ] **Step 1.1: Add update mutation to transaction hooks**

Add this export to the existing `frontend/src/hooks/use-transactions.ts` file. Place it after `useCreateTransaction` and before `useDeleteTransaction`.

```ts
// frontend/src/hooks/use-transactions.ts (append after useCreateTransaction)

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; currency: string; post_date: string; description: string; notes?: string; splits_data: { account: string; value: string; quantity?: string; memo?: string }[] }) =>
      api.put<Transaction>(`/transactions/${id}`, data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: txKeys.all });
      qc.invalidateQueries({ queryKey: txKeys.detail(variables.id) });
    },
  });
}
```

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

**Commit:**
```bash
git add frontend/src/hooks/use-transactions.ts
git commit -m "feat(frontend): add useUpdateTransaction mutation hook

Add PUT /transactions/:id mutation with cache invalidation
for both list and detail query keys."
```

---

## Task 2: Add Edit Mode to `TransactionForm`

**File:** `frontend/src/features/transactions/components/transaction-form.tsx`

- [ ] **Step 2.1: Update the component to support create and edit modes**

Replace the entire file contents with:

```tsx
// frontend/src/features/transactions/components/transaction-form.tsx
import { CalendarIcon, Loader2 } from 'lucide-react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { format } from 'date-fns';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { SplitInput } from '@/components/split-input';
import { useCreateTransaction, useUpdateTransaction, useTransaction } from '@/hooks/use-transactions';
import { transactionFormSchema, type TransactionFormValues } from './transaction-form-schema';

export interface TransactionFormProps {
  transactionId?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
  defaultCurrency?: string;
}

export function TransactionForm({ transactionId, onSuccess, onCancel, defaultCurrency = 'USD' }: TransactionFormProps) {
  const isEdit = !!transactionId;
  const createMutation = useCreateTransaction();
  const updateMutation = useUpdateTransaction();
  const { data: existing, isLoading: isLoadingTx } = useTransaction(transactionId ?? '');
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

  useEffect(() => {
    if (existing && isEdit) {
      form.reset({
        currency: existing.currency,
        post_date: existing.post_date,
        description: existing.description,
        notes: existing.notes ?? '',
        splits_data: existing.splits.map((s) => ({
          account: s.account,
          value: s.value,
          quantity: s.quantity,
          memo: s.memo,
        })),
      });
    }
  }, [existing, isEdit, form]);

  const onSubmit = (data: TransactionFormValues) => {
    if (isEdit) {
      updateMutation.mutate({ id: transactionId!, ...data }, { onSuccess });
    } else {
      createMutation.mutate(data, {
        onSuccess: () => {
          form.reset();
          onSuccess?.();
        },
      });
    }
  };

  if (isEdit && isLoadingTx) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          <span className="text-sm text-muted-foreground">Loading transaction…</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader><CardTitle>{isEdit ? 'Edit Transaction' : 'New Transaction'}</CardTitle></CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Date</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className={cn('w-full justify-start text-left font-normal', !form.watch('post_date') && 'text-muted-foreground')}>
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {form.watch('post_date') ? format(new Date(form.watch('post_date')), 'PPP') : 'Pick a date'}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar mode="single" selected={new Date(form.watch('post_date'))} onSelect={(date) => { if (date) form.setValue('post_date', format(date, 'yyyy-MM-dd'), { shouldDirty: true, shouldValidate: true }); }} initialFocus />
                  </PopoverContent>
                </Popover>
                {form.formState.errors.post_date && <p className="text-xs text-red-600">{form.formState.errors.post_date.message}</p>}
              </div>
              <div className="space-y-2">
                <Label>Currency</Label>
                <Input {...form.register('currency')} placeholder="USD" maxLength={3} className="uppercase" />
                {form.formState.errors.currency && <p className="text-xs text-red-600">{form.formState.errors.currency.message}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input id="description" {...form.register('description')} placeholder="e.g., Monthly salary deposit" />
              {form.formState.errors.description && <p className="text-xs text-red-600">{form.formState.errors.description.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Input id="notes" {...form.register('notes')} placeholder="Additional details…" />
            </div>
            <Separator />
            <SplitInput />
            {form.formState.errors.splits_data && (
              <p className="text-sm text-red-600">{typeof form.formState.errors.splits_data.message === 'string' ? form.formState.errors.splits_data.message : 'Fix split errors above.'}</p>
            )}
          </CardContent>
          <CardFooter className="flex justify-between gap-4">
            {onCancel && <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>Cancel</Button>}
            <div className="ml-auto flex items-center gap-4">
              {form.formState.isDirty && <span className="text-xs text-muted-foreground">Unsaved changes</span>}
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEdit ? 'Update Transaction' : 'Create Transaction'}
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

**Commit:**
```bash
git add frontend/src/features/transactions/components/transaction-form.tsx
git commit -m "feat(frontend): add edit mode to TransactionForm

Accept optional transactionId prop to load existing transaction
via useTransaction and submit via useUpdateTransaction. Shows
loading state while fetching, populates form with splits,
and switches submit label between Create/Update."
```

---

## Task 3: Create `TransactionNewPage`

**File:** `frontend/src/routes/TransactionNewPage.tsx`

- [ ] **Step 3.1: Create new-transaction page**

```tsx
// frontend/src/routes/TransactionNewPage.tsx
import { useNavigate } from 'react-router-dom';
import { TransactionForm } from '@/features/transactions/components/transaction-form';

export function TransactionNewPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">New Transaction</h1>
      </div>
      <TransactionForm
        onSuccess={() => navigate('/transactions')}
        onCancel={() => navigate('/transactions')}
      />
    </div>
  );
}
```

**Commit:**
```bash
git add frontend/src/routes/TransactionNewPage.tsx
git commit -m "feat(frontend): add TransactionNewPage route

Wraps TransactionForm with navigation back to transaction list
on success or cancel."
```

---

## Task 4: Create `TransactionListPage`

**File:** `frontend/src/routes/TransactionListPage.tsx`

- [ ] **Step 4.1: Create paginated transaction list with date filter**

```tsx
// frontend/src/routes/TransactionListPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { useTransactions, useDeleteTransaction } from '@/hooks/use-transactions';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function TransactionListPage() {
  const [page, setPage] = useState(1);
  const [dateFilter, setDateFilter] = useState<string>('');
  const deleteMutation = useDeleteTransaction();

  const { data, isLoading, error } = useTransactions({
    page,
    ...(dateFilter ? { post_date: dateFilter } : {}),
  });

  const handleDelete = (id: string) => {
    if (!window.confirm('Delete this transaction? This cannot be undone.')) return;
    deleteMutation.mutate(id);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <Card>
          <CardHeader><Skeleton className="h-6 w-32" /></CardHeader>
          <CardContent className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load transactions.</p>
      </div>
    );
  }

  const transactions = data?.results ?? [];
  const hasNext = !!data?.next;
  const hasPrev = !!data?.previous;
  const totalPages = data?.count ? Math.ceil(data.count / 20) : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">Transactions</h1>
        <Button asChild><Link to="/transactions/new"><Plus className="mr-2 h-4 w-4" />New</Link></Button>
      </div>

      {/* Date filter */}
      <div className="flex items-center gap-2">
        <label htmlFor="date-filter" className="text-sm font-medium">Date:</label>
        <input
          id="date-filter"
          type="date"
          value={dateFilter}
          onChange={(e) => { setDateFilter(e.target.value); setPage(1); }}
          className="rounded-md border bg-background px-3 py-1.5 text-sm"
        />
        {dateFilter && (
          <Button variant="ghost" size="sm" onClick={() => { setDateFilter(''); setPage(1); }}>
            Clear
          </Button>
        )}
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} Transactions</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Date</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Description</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Splits</th>
                <th className="w-24" />
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id} className="border-b last:border-0">
                  <td className="px-4 py-3 text-sm whitespace-nowrap">
                    {format(new Date(tx.post_date), 'MMM d, yyyy')}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{tx.description}</span>
                      {tx.notes && (
                        <Badge variant="outline" className="text-xs">Note</Badge>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {tx.splits?.length ?? 0}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="sm" asChild>
                        <Link to={`/transactions/${tx.id}`}>View</Link>
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(tx.id)} disabled={deleteMutation.isPending}>
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
              {transactions.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    No transactions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={!hasPrev}>
              <ChevronLeft className="mr-1 h-4 w-4" />Prev
            </Button>
            <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={!hasNext}>
              Next<ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

**Commit:**
```bash
git add frontend/src/routes/TransactionListPage.tsx
git commit -m "feat(frontend): add TransactionListPage with pagination and date filter

Paginated table of transactions with date filter input, skeleton
loading states, delete action with confirmation, and prev/next
pagination controls. Displays date, description, split count,
and note indicator."
```

---

## Task 5: Create `TransactionDetailPage`

**File:** `frontend/src/routes/TransactionDetailPage.tsx`

- [ ] **Step 5.1: Create view/edit transaction detail page**

```tsx
// frontend/src/routes/TransactionDetailPage.tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react';
import { useTransaction, useDeleteTransaction } from '@/hooks/use-transactions';
import { TransactionForm } from '@/features/transactions/components/transaction-form';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';

export function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>() as { id: string };
  const navigate = useNavigate();
  const { data, isLoading, error } = useTransaction(id);
  const deleteMutation = useDeleteTransaction();
  const [editing, setEditing] = useState(false);

  const handleDelete = () => {
    if (!window.confirm('Delete this transaction? This cannot be undone.')) return;
    deleteMutation.mutate(id, { onSuccess: () => navigate('/transactions') });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load transaction.</p>
        <Button variant="outline" size="sm" className="mt-2" onClick={() => navigate('/transactions')}>
          <ArrowLeft className="mr-2 h-4 w-4" />Back
        </Button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12 text-muted-foreground">Transaction not found.</div>
    );
  }

  if (editing) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
          <ArrowLeft className="mr-2 h-4 w-4" />Back to details
        </Button>
        <TransactionForm
          transactionId={id}
          onSuccess={() => setEditing(false)}
          onCancel={() => setEditing(false)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => navigate('/transactions')}>
          <ArrowLeft className="mr-2 h-4 w-4" />Back
        </Button>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
            <Pencil className="mr-2 h-4 w-4" />Edit
          </Button>
          <Button variant="outline" size="sm" onClick={handleDelete} disabled={deleteMutation.isPending}>
            <Trash2 className="mr-2 h-4 w-4" />Delete
          </Button>
        </div>
      </div>

      {/* Header info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">{data.description}</CardTitle>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{format(new Date(data.post_date), 'MMMM d, yyyy')}</span>
            <Badge variant="outline">{data.currency}</Badge>
            {data.notes && <span className="italic">{data.notes}</span>}
          </div>
        </CardHeader>
      </Card>

      {/* Splits */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Splits ({data.splits.length})</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Account</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Memo</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">Value</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">Quantity</th>
              </tr>
            </thead>
            <tbody>
              {data.splits.map((split) => (
                <tr key={split.id} className="border-b last:border-0">
                  <td className="px-4 py-3 text-sm font-mono">{split.account}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{split.memo || '—'}</td>
                  <td className="px-4 py-3 text-right text-sm font-mono">
                    <span className={parseFloat(split.value) < 0 ? 'text-red-600' : 'text-green-600'}>
                      {parseFloat(split.value).toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono">{parseFloat(split.quantity).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Metadata */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Metadata</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-muted-foreground">ID</span><span className="font-mono">{data.id}</span></div>
          <Separator />
          <div className="flex justify-between"><span className="text-muted-foreground">Created</span><span>{format(new Date(data.created_at), 'PPP p')}</span></div>
          <Separator />
          <div className="flex justify-between"><span className="text-muted-foreground">Last updated</span><span>{format(new Date(data.updated_at), 'PPP p')}</span></div>
          {data.created_by && (
            <>
              <Separator />
              <div className="flex justify-between"><span className="text-muted-foreground">Created by</span><span className="font-mono">{data.created_by}</span></div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

**Commit:**
```bash
git add frontend/src/routes/TransactionDetailPage.tsx
git commit -m "feat(frontend): add TransactionDetailPage with view/edit toggle

Detail page showing transaction header, splits table with
color-coded values, metadata card, inline edit via TransactionForm
with transactionId prop, and delete with confirmation. Displays
loading, error, and not-found states."
```

---

## Task 6: Wire Routes in `App.tsx`

**File:** `frontend/src/App.tsx`

- [ ] **Step 6.1: Replace placeholder with transaction routes**

Apply these edits to `frontend/src/App.tsx`:

1. Add imports at the top (after existing route imports):
```ts
import { TransactionListPage } from '@/routes/TransactionListPage';
import { TransactionNewPage } from '@/routes/TransactionNewPage';
import { TransactionDetailPage } from '@/routes/TransactionDetailPage';
```

2. Replace the single transactions placeholder line with three routes:
```ts
// Replace this line:
// <Route path="/transactions" element={<PlaceholderPage title="Transactions" />} />

// With these three lines:
<Route path="/transactions" element={<TransactionListPage />} />
<Route path="/transactions/new" element={<TransactionNewPage />} />
<Route path="/transactions/:id" element={<TransactionDetailPage />} />
```

Full resulting `App.tsx` for reference:

```tsx
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
import { TransactionListPage } from '@/routes/TransactionListPage';
import { TransactionNewPage } from '@/routes/TransactionNewPage';
import { TransactionDetailPage } from '@/routes/TransactionDetailPage';

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
              <Route path="/transactions" element={<TransactionListPage />} />
              <Route path="/transactions/new" element={<TransactionNewPage />} />
              <Route path="/transactions/:id" element={<TransactionDetailPage />} />
              <Route path="/budgets" element={<PlaceholderPage title="Budgets" />} />
              <Route path="/investments" element={<PlaceholderPage title="Investments" />} />
              <Route path="/receipts" element={<PlaceholderPage title="Receipts" />} />
              <Route path="/recurring" element={<PlaceholderPage title="Recurring" />} />
              <Route path="/reports" element={<ReportsIndex />} />
              <Route path="/reports/balance-sheet" element={<BalanceSheetPage />} />
              <Route path="/reports/income-statement" element={<IncomeStatementPage />} />
              <Route path="/reports/cash-flow" element={<CashFlowPage />} />
              <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

**Commit:**
```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): wire transaction routes in App

Replace Transactions placeholder with TransactionListPage,
TransactionNewPage, and TransactionDetailPage routes."
```

---

## Summary of Deliverables

| # | File | Action | Purpose |
|---|------|--------|---------|
| 1 | `frontend/src/hooks/use-transactions.ts` | Modify | Add `useUpdateTransaction` hook |
| 2 | `frontend/src/features/transactions/components/transaction-form.tsx` | Modify | Add edit mode (`transactionId`, fetch, populate, update) |
| 3 | `frontend/src/routes/TransactionNewPage.tsx` | Create | New transaction page wrapping `TransactionForm` |
| 4 | `frontend/src/routes/TransactionListPage.tsx` | Create | Paginated list with date filter, delete |
| 5 | `frontend/src/routes/TransactionDetailPage.tsx` | Create | View splits, metadata, inline edit toggle |
| 6 | `frontend/src/App.tsx` | Modify | Wire three transaction routes |

## Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/transactions` | `TransactionListPage` | Paginated list, date filter |
| `/transactions/new` | `TransactionNewPage` | Create form |
| `/transactions/:id` | `TransactionDetailPage` | View detail, toggle to edit |
