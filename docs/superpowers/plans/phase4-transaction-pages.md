# Phase 4: Transaction Pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build three transaction-related pages (list, create, detail/edit) and extend the existing `TransactionForm` component to support edit mode. Wire all routes in `App.tsx`.

**Architecture:** React 18 + TypeScript + Vite. react-router-dom v6 for routing, React Query for server state, React Hook Form + Zod for form state, shadcn/ui for UI primitives.

**Tech Stack:** React 18, TypeScript strict, Tailwind CSS, shadcn/ui, @tanstack/react-query v5, react-router-dom v6, react-hook-form + zod, lucide-react, date-fns

---

## File Map

### Files to Create
- `frontend/src/routes/TransactionListPage.tsx` — Paginated transaction list with date filter
- `frontend/src/routes/TransactionNewPage.tsx` — New transaction form page
- `frontend/src/routes/TransactionDetailPage.tsx` — Single transaction view with splits table and edit/delete actions

### Files to Modify
- `frontend/src/types/transaction.ts` — Add `CreateTransactionData` and `UpdateTransactionData` types
- `frontend/src/hooks/use-transactions.ts` — Add `useUpdateTransaction` hook
- `frontend/src/features/transactions/components/transaction-form.tsx` — Add `transactionId` prop for edit mode, populate form with existing data
- `frontend/src/App.tsx` — Wire `/transactions`, `/transactions/new`, `/transactions/:id` routes

---

## Task 1: Add Missing Types and Update Hook

**Files:**
- Modify: `frontend/src/types/transaction.ts`
- Modify: `frontend/src/hooks/use-transactions.ts`

- [ ] **Step 1.1: Add Create/Update transaction data types**

Append these types to the existing `frontend/src/types/transaction.ts`:

```ts
// frontend/src/types/transaction.ts — append to end of file

export interface CreateTransactionData {
  currency: string;
  post_date: string;
  description: string;
  notes?: string;
  splits_data: {
    account: string;
    value: string;
    quantity?: string;
    memo?: string;
  }[];
}

export interface UpdateTransactionData {
  id: string;
  currency?: string;
  post_date?: string;
  description?: string;
  notes?: string;
  splits_data?: {
    account: string;
    value: string;
    quantity?: string;
    memo?: string;
  }[];
}
```

- [ ] **Step 1.2: Add `useUpdateTransaction` hook**

Append to the existing `frontend/src/hooks/use-transactions.ts`:

```ts
// frontend/src/hooks/use-transactions.ts — append to end of file

import type { UpdateTransactionData } from '@/types/transaction';

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: UpdateTransactionData) =>
      api.put<Transaction>(`/transactions/${id}`, body),
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
git add frontend/src/types/transaction.ts frontend/src/hooks/use-transactions.ts
git commit -m "feat(frontend): add UpdateTransactionData type and useUpdateTransaction hook

Add missing CreateTransactionData and UpdateTransactionData types
for typed transaction mutations. Add useUpdateTransaction hook with
cache invalidation for both list and detail queries."
```

---

## Task 2: Extend TransactionForm for Edit Mode

**Files:**
- Modify: `frontend/src/features/transactions/components/transaction-form.tsx`
- Modify: `frontend/src/features/transactions/components/transaction-form-schema.ts`

- [ ] **Step 2.1: Update the schema to allow empty notes without default**

The current schema uses `.default('')` on notes which can interfere with `form.reset()` in edit mode. Change the notes field:

```ts
// frontend/src/features/transactions/components/transaction-form-schema.ts
// Replace the existing notes line:
//   notes: z.string().max(1000).optional().default(''),
// With:
  notes: z.string().max(1000).optional().or(z.literal('')),
```

- [ ] **Step 2.2: Replace the entire TransactionForm component with edit-mode support**

Replace the full contents of `frontend/src/features/transactions/components/transaction-form.tsx` with:

```tsx
// frontend/src/features/transactions/components/transaction-form.tsx
import { CalendarIcon, Loader2 } from 'lucide-react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { format } from 'date-fns';
import * as React from 'react';
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
  /** When provided, the form operates in edit mode for this transaction. */
  transactionId?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
  defaultCurrency?: string;
}

function DatePickerField({ value, onChange, disabled }: {
  value: Date | undefined;
  onChange: (date: Date | undefined) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = React.useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn('w-full justify-start text-left font-normal', !value && 'text-muted-foreground')}
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
          onSelect={(date) => { onChange(date); setOpen(false); }}
          initialFocus
          disabled={(date) => date > new Date()}
        />
      </PopoverContent>
    </Popover>
  );
}

export function TransactionForm({ transactionId, onSuccess, onCancel, defaultCurrency = 'USD' }: TransactionFormProps) {
  const isEditMode = !!transactionId;

  const { data: existing, isLoading: isLoadingTx } = useTransaction(transactionId!);
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
    if (existing) {
      form.reset({
        currency: existing.currency,
        post_date: existing.post_date,
        description: existing.description,
        notes: existing.notes ?? '',
        splits_data: existing.splits.map((split) => ({
          account: split.account,
          value: split.value,
          quantity: split.quantity,
          memo: split.memo,
        })),
      });
    }
  }, [existing, form]);

  const onSubmit = (data: TransactionFormValues) => {
    if (isEditMode) {
      updateMutation.mutate({ id: transactionId, ...data }, { onSuccess });
    } else {
      createMutation.mutate(data, { onSuccess: () => { form.reset(); onSuccess?.(); } });
    }
  };

  if (isEditMode && isLoadingTx) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading transaction...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader><CardTitle>{isEditMode ? 'Edit Transaction' : 'New Transaction'}</CardTitle></CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Date</Label>
                <DatePickerField
                  value={form.watch('post_date') ? new Date(form.watch('post_date')) : undefined}
                  onChange={(date) => {
                    if (date) form.setValue('post_date', format(date, 'yyyy-MM-dd'), { shouldDirty: true, shouldValidate: true });
                  }}
                />
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
              <Input id="notes" {...form.register('notes')} placeholder="Additional details..." />
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

Key changes from the existing file:
- Added `transactionId` prop to `TransactionFormProps`
- Added `useTransaction` fetch for edit-mode data population
- Added `useUpdateTransaction` mutation
- Added `React.useEffect` to populate form via `form.reset()` when `existing` data loads
- Submit handler branches on `isEditMode` to call create vs update mutation
- Loading state renders skeleton card while fetching existing transaction
- Submit button label changes between "Create" and "Update"
- Header title changes between "New Transaction" and "Edit Transaction"

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

**Commit:**
```bash
git add frontend/src/features/transactions/components/transaction-form-schema.ts frontend/src/features/transactions/components/transaction-form.tsx
git commit -m "feat(frontend): add edit mode support to TransactionForm

Add transactionId prop that switches form between create and edit
modes. Fetches existing transaction data via useTransaction hook,
populates form fields via form.reset(), and submits through
useUpdateTransaction mutation. Add loading state for data fetch."
```

---

## Task 3: Transaction List Page

**Files:**
- Create: `frontend/src/routes/TransactionListPage.tsx`

- [ ] **Step 3.1: Create the paginated transaction list page**

```tsx
// frontend/src/routes/TransactionListPage.tsx
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { useState } from 'react';
import { CalendarIcon, ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { useTransactions, useDeleteTransaction } from '@/hooks/use-transactions';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';
import { cn } from '@/lib/utils';
import type { Transaction } from '@/types/transaction';

function formatSplitSummary(tx: Transaction): string {
  const descriptions = tx.splits
    .filter((s) => s.memo)
    .map((s) => s.memo);
  if (descriptions.length > 0) return descriptions.join('; ');
  const net = tx.splits.reduce((sum, s) => sum + (parseFloat(s.value) || 0), 0);
  return `${tx.splits.length} splits, net ${net.toFixed(2)}`;
}

export function TransactionListPage() {
  const [page, setPage] = useState(1);
  const [dateFilter, setDateFilter] = useState<Date | undefined>(undefined);
  const [calendarOpen, setCalendarOpen] = useState(false);

  const dateParam = dateFilter ? format(dateFilter, 'yyyy-MM-dd') : undefined;
  const { data, isLoading, error } = useTransactions({ page, post_date: dateParam });
  const deleteMutation = useDeleteTransaction();

  const handleDelete = (id: string) => {
    if (window.confirm('Delete this transaction? This cannot be undone.')) {
      deleteMutation.mutate(id);
    }
  };

  const transactions = data?.results ?? [];
  const totalPages = Math.ceil((data?.count ?? 0) / 10); // DRF default page size

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Transactions</h1>
        <Button asChild>
          <Link to="/transactions/new">
            <Plus className="mr-2 h-4 w-4" />
            New Transaction
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" className={cn('w-[240px] justify-start text-left font-normal', !dateFilter && 'text-muted-foreground')}>
              <CalendarIcon className="mr-2 h-4 w-4" />
              {dateFilter ? format(dateFilter, 'PPP') : 'Filter by date...'}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={dateFilter}
              onSelect={(date) => { setDateFilter(date); setCalendarOpen(false); }}
              initialFocus
            />
          </PopoverContent>
        </Popover>
        {dateFilter && (
          <Button variant="ghost" size="sm" onClick={() => setDateFilter(undefined)}>
            Clear filter
          </Button>
        )}
      </div>

      {/* List */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 w-full animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">Failed to load transactions.</p>
        </div>
      )}

      {!isLoading && !error && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {data?.count ?? 0} Transactions
              {dateFilter && ` on ${format(dateFilter, 'PPP')}`}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Date</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Description</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Splits</th>
                    <th className="w-32" />
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="border-b last:border-0 hover:bg-muted/50">
                      <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                        {format(new Date(tx.post_date), 'MMM dd, yyyy')}
                      </td>
                      <td className="px-4 py-3">
                        <Link to={`/transactions/${tx.id}`} className="text-sm font-medium hover:underline">
                          {tx.description}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {formatSplitSummary(tx)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" asChild>
                            <Link to={`/transactions/${tx.id}`}>View</Link>
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(tx.id)}
                            disabled={deleteMutation.isPending}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {transactions.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted-foreground">
                        {dateFilter ? 'No transactions on this date.' : 'No transactions yet.'}
                        {!dateFilter && (
                          <Link to="/transactions/new" className="ml-1 text-primary hover:underline">
                            Create one
                          </Link>
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </p>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                    <ChevronLeft className="mr-1 h-4 w-4" /> Previous
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                    Next <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

**Commit:**
```bash
git add frontend/src/routes/TransactionListPage.tsx
git commit -m "feat(frontend): add TransactionListPage with pagination and date filter

Paginated transaction list with date picker filter, split summary,
inline delete with confirmation, and navigation to detail pages.
Includes loading skeleton, error banner, and empty state with
create link."
```

---

## Task 4: Transaction New Page

**Files:**
- Create: `frontend/src/routes/TransactionNewPage.tsx`

- [ ] **Step 4.1: Create the new transaction page**

```tsx
// frontend/src/routes/TransactionNewPage.tsx
import { useNavigate } from 'react-router-dom';
import { TransactionForm } from '@/features/transactions/components/transaction-form';

export function TransactionNewPage() {
  const navigate = useNavigate();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
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

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

**Commit:**
```bash
git add frontend/src/routes/TransactionNewPage.tsx
git commit -m "feat(frontend): add TransactionNewPage route

Thin wrapper page that renders TransactionForm in create mode
with navigation back to transaction list on success or cancel."
```

---

## Task 5: Transaction Detail Page

**Files:**
- Create: `frontend/src/routes/TransactionDetailPage.tsx`

- [ ] **Step 5.1: Create the transaction detail page**

```tsx
// frontend/src/routes/TransactionDetailPage.tsx
import { useParams, useNavigate, Link } from 'react-router-dom';
import { format } from 'date-fns';
import { ArrowLeft, Pencil, Trash2, Loader2 } from 'lucide-react';
import { useTransaction, useDeleteTransaction } from '@/hooks/use-transactions';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { Split } from '@/types/transaction';

function reconciledLabel(state: string): string {
  switch (state) {
    case 'Y': return 'Reconciled';
    case 'C': return 'Cleared';
    default: return 'Unreconciled';
  }
}

function reconciledVariant(state: string): 'default' | 'secondary' | 'outline' {
  switch (state) {
    case 'Y': return 'default';
    case 'C': return 'secondary';
    default: return 'outline';
  }
}

export function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: tx, isLoading, error } = useTransaction(id!);
  const deleteMutation = useDeleteTransaction();

  const handleDelete = () => {
    if (window.confirm('Delete this transaction? This cannot be undone.')) {
      deleteMutation.mutate(id!, { onSuccess: () => navigate('/transactions') });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load transaction.</p>
        <Button variant="outline" size="sm" className="mt-2" asChild>
          <Link to="/transactions">Back to Transactions</Link>
        </Button>
      </div>
    );
  }

  if (!tx) {
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground">Transaction not found.</p>
        <Button variant="outline" size="sm" asChild>
          <Link to="/transactions">Back to Transactions</Link>
        </Button>
      </div>
    );
  }

  const netValue = tx.splits.reduce((sum, s) => sum + (parseFloat(s.value) || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/transactions">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Link>
          </Button>
          <h1 className="text-2xl font-bold">{tx.description}</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/transactions/${tx.id}/edit`}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </Link>
          </Button>
          <Button variant="outline" size="sm" onClick={handleDelete} disabled={deleteMutation.isPending}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Summary card */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Details</CardTitle></CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <dt className="text-sm text-muted-foreground">Date</dt>
              <dd className="text-sm font-medium">{format(new Date(tx.post_date), 'PPP')}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Currency</dt>
              <dd className="text-sm font-medium">{tx.currency}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Net Value</dt>
              <dd className="text-sm font-medium">{netValue.toFixed(2)}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Created</dt>
              <dd className="text-sm font-medium">{format(new Date(tx.created_at), 'PPP')}</dd>
            </div>
          </dl>
          {tx.notes && (
            <>
              <Separator className="my-4" />
              <div>
                <dt className="text-sm text-muted-foreground">Notes</dt>
                <dd className="text-sm">{tx.notes}</dd>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Splits table */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Splits ({tx.splits.length})</CardTitle></CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                  <TableHead className="text-right">Quantity</TableHead>
                  <TableHead>Memo</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tx.splits.map((split: Split) => (
                  <TableRow key={split.id}>
                    <td className="font-mono text-sm">{split.account}</td>
                    <td className="text-right font-mono text-sm">{parseFloat(split.value).toFixed(2)}</td>
                    <td className="text-right font-mono text-sm">{parseFloat(split.quantity).toFixed(2)}</td>
                    <td className="text-sm text-muted-foreground">{split.memo || '-'}</td>
                    <td>
                      <Badge variant={reconciledVariant(split.reconcile_state)}>
                        {reconciledLabel(split.reconcile_state)}
                      </Badge>
                    </td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

**Commit:**
```bash
git add frontend/src/routes/TransactionDetailPage.tsx
git commit -m "feat(frontend): add TransactionDetailPage with splits table

Detail view showing transaction metadata, splits table with
reconciliation status badges, net value calculation, and
edit/delete action buttons. Includes loading skeleton, error
state, and not-found fallback."
```

---

## Task 6: Wire Routes in App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 6.1: Add imports for new page components**

Add these import lines to the existing imports block in `frontend/src/App.tsx`:

```ts
// Add after the existing import lines:
import { TransactionListPage } from '@/routes/TransactionListPage';
import { TransactionNewPage } from '@/routes/TransactionNewPage';
import { TransactionDetailPage } from '@/routes/TransactionDetailPage';
```

- [ ] **Step 6.2: Replace the placeholder `/transactions` route and add new routes**

Replace the existing `/transactions` placeholder route:

```tsx
// Replace this line:
//   <Route path="/transactions" element={<PlaceholderPage title="Transactions" />} />
// With these three routes:
              <Route path="/transactions" element={<TransactionListPage />} />
              <Route path="/transactions/new" element={<TransactionNewPage />} />
              <Route path="/transactions/:id" element={<TransactionDetailPage />} />
```

Note: The `/transactions/:id/edit` route should navigate to the same `TransactionDetailPage` in edit mode. Add this route as well:

```tsx
              <Route path="/transactions/:id/edit" element={<TransactionEditPageWrapper />} />
```

And add a small wrapper component before the `App` function:

```tsx
// Add before the `export function App()` declaration:
import { useParams, Navigate } from 'react-router-dom';
import { TransactionForm } from '@/features/transactions/components/transaction-form';

function TransactionEditPageWrapper() {
  const { id } = useParams<{ id: string }>();
  if (!id) return <Navigate to="/transactions" replace />;
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">Edit Transaction</h1>
      <TransactionForm
        transactionId={id}
        onSuccess={() => window.location.href = `/transactions/${id}`}
        onCancel={() => window.location.href = `/transactions/${id}`}
      />
    </div>
  );
}
```

**Test:** Verify TypeScript compilation:
```bash
cd frontend && npx tsc --noEmit
```

Verify the app starts:
```bash
cd frontend && npm run dev
```

Manual test checklist:
1. Navigate to `/transactions` — list page renders with transactions
2. Click "New Transaction" — navigates to `/transactions/new` with form
3. Submit a valid transaction — redirects to `/transactions`, new entry visible
4. Click "View" on any transaction — navigates to `/transactions/:id` detail view
5. Click "Edit" on detail page — navigates to `/transactions/:id/edit` with pre-filled form
6. Modify and submit edit — redirects back to detail page with updated data
7. Click "Delete" on detail page — confirms then redirects to list
8. Click "Delete" from list inline button — confirms then removes from list
9. Use date filter on list page — filters transactions by selected date
10. Pagination arrows work when more than one page of transactions exists

**Commit:**
```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): wire transaction routes in App.tsx

Replace /transactions placeholder with TransactionListPage,
add /transactions/new (TransactionNewPage), /transactions/:id
(TransactionDetailPage), and /transactions/:id/edit (edit wrapper
with pre-filled TransactionForm)."
```

---

## Summary of Deliverables

| # | Description | File | Action |
|---|-------------|------|--------|
| 1 | Add CreateTransactionData / UpdateTransactionData | `frontend/src/types/transaction.ts` | Modify |
| 2 | Add useUpdateTransaction hook | `frontend/src/hooks/use-transactions.ts` | Modify |
| 3 | Add edit mode to TransactionForm | `frontend/src/features/transactions/components/transaction-form.tsx` | Modify |
| 4 | Fix notes schema for edit-mode reset | `frontend/src/features/transactions/components/transaction-form-schema.ts` | Modify |
| 5 | Transaction list page with date filter | `frontend/src/routes/TransactionListPage.tsx` | Create |
| 6 | New transaction form page | `frontend/src/routes/TransactionNewPage.tsx` | Create |
| 7 | Transaction detail page with splits | `frontend/src/routes/TransactionDetailPage.tsx` | Create |
| 8 | Wire all transaction routes | `frontend/src/App.tsx` | Modify |

## Route Map

| URL | Component | Description |
|-----|-----------|-------------|
| `/transactions` | `TransactionListPage` | Paginated list with date filter |
| `/transactions/new` | `TransactionNewPage` | Create transaction form |
| `/transactions/:id` | `TransactionDetailPage` | View transaction + splits |
| `/transactions/:id/edit` | `TransactionEditPageWrapper` | Edit transaction form (pre-filled) |
