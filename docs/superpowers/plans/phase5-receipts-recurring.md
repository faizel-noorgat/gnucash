# Phase 5: Receipt Capture & Recurring Transaction Management

## Scope

Frontend pages and hooks for receipt upload/processing and recurring transaction management. Backend endpoints already exist and are verified.

## Prerequisites Verified

| Component | File | Status |
|-----------|------|--------|
| Receipt model | `backend/receipts/models.py` | Exists: Status (PENDING, PROCESSED, MANUAL_REVIEW), OCR fields, auto/user category |
| ReceiptViewSet | `backend/receipts/views.py` | Exists: CRUD + `@action(detail=True) process` at `POST /api/v1/receipts/{id}/process/` |
| Receipt serializer | `backend/receipts/serializers.py` | Exists: includes `auto_category_name`, `user_category_name` read-only |
| RecurringTransaction model | `backend/recurring/models.py` | Exists: Frequency enum, enabled, next_run, template JSONField |
| RecurringTransactionViewSet | `backend/recurring/views.py` | Exists: standard CRUD, no extra actions |
| Tenant router | `backend/gnucash_web/urls.py` | Both `receipts` and `recurring` registered under `/api/v1/` |
| Account types | `frontend/src/types/account.ts` | Exists: Account interface for category picker |
| Transaction types | `frontend/src/types/transaction.ts` | Exists: SplitCreateData for template building |

---

## Task 1: Receipt TypeScript Types

**File:** `frontend/src/types/receipt.ts`

```typescript
export type ReceiptStatus = 'PENDING' | 'PROCESSED' | 'MANUAL_REVIEW';

export interface Receipt {
  id: string;
  tenant: string;
  transaction: string | null;
  file_url: string;
  ocr_text: string;
  vendor: string;
  total_amount: string | null;
  receipt_date: string | null;
  status: ReceiptStatus;
  auto_category: string | null;
  auto_category_name: string | null;
  user_category: string | null;
  user_category_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReceiptListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Receipt[];
}

export interface ReceiptCreateData {
  file_url: string;
  vendor?: string;
  receipt_date?: string;
}

export interface ReceiptUpdateData {
  user_category?: string | null;
  transaction?: string | null;
  status?: ReceiptStatus;
}
```

**Commit:** `feat(types): add Receipt TypeScript types`

---

## Task 2: Recurring Transaction TypeScript Types

**File:** `frontend/src/types/recurring.ts`

```typescript
export type RecurringFrequency = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'YEARLY';

export interface RecurringTransaction {
  id: string;
  tenant: string;
  name: string;
  template: Record<string, unknown>;
  frequency: RecurringFrequency;
  start_date: string;
  end_date: string | null;
  last_run: string | null;
  next_run: string;
  enabled: boolean;
  advance_notice_days: number;
  auto_create: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecurringTransactionListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: RecurringTransaction[];
}

export interface RecurringTransactionCreateData {
  name: string;
  template: Record<string, unknown>;
  frequency: RecurringFrequency;
  start_date: string;
  end_date?: string | null;
  next_run: string;
  advance_notice_days?: number;
  auto_create?: boolean;
}

export interface RecurringTransactionUpdateData {
  name?: string;
  template?: Record<string, unknown>;
  frequency?: RecurringFrequency;
  start_date?: string;
  end_date?: string | null;
  next_run?: string;
  enabled?: boolean;
  advance_notice_days?: number;
  auto_create?: boolean;
}
```

**Commit:** `feat(types): add RecurringTransaction TypeScript types`

---

## Task 3: Receipt React Query Hooks

**File:** `frontend/src/hooks/use-receipts.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  Receipt,
  ReceiptListResponse,
  ReceiptCreateData,
  ReceiptUpdateData,
} from '@/types/receipt';

export const receiptKeys = {
  all: ['receipts'] as const,
  list: () => [...receiptKeys.all, 'list'] as const,
  detail: (id: string) => [...receiptKeys.all, 'detail', id] as const,
};

export function useReceipts() {
  return useQuery({
    queryKey: receiptKeys.list(),
    queryFn: () => api.get<ReceiptListResponse>('/receipts'),
  });
}

export function useReceipt(id: string) {
  return useQuery({
    queryKey: receiptKeys.detail(id),
    queryFn: () => api.get<Receipt>(`/receipts/${id}`),
    enabled: !!id,
  });
}

export function useCreateReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ReceiptCreateData) => api.post<Receipt>('/receipts', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: receiptKeys.all }),
  });
}

export function useUpdateReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ReceiptUpdateData }) =>
      api.patch<Receipt>(`/receipts/${id}`, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: receiptKeys.list() });
      qc.invalidateQueries({ queryKey: receiptKeys.detail(id) });
    },
  });
}

export function useProcessReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<{ status: string }>(`/receipts/${id}/process/`, {}),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: receiptKeys.detail(id) });
    },
  });
}

export function useDeleteReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/receipts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: receiptKeys.all }),
  });
}
```

**Commit:** `feat(hooks): add receipt React Query hooks`

---

## Task 4: Recurring Transaction React Query Hooks

**File:** `frontend/src/hooks/use-recurring.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  RecurringTransaction,
  RecurringTransactionListResponse,
  RecurringTransactionCreateData,
  RecurringTransactionUpdateData,
} from '@/types/recurring';

export const recurringKeys = {
  all: ['recurring'] as const,
  list: () => [...recurringKeys.all, 'list'] as const,
  detail: (id: string) => [...recurringKeys.all, 'detail', id] as const,
};

export function useRecurringTransactions() {
  return useQuery({
    queryKey: recurringKeys.list(),
    queryFn: () => api.get<RecurringTransactionListResponse>('/recurring'),
  });
}

export function useRecurringTransaction(id: string) {
  return useQuery({
    queryKey: recurringKeys.detail(id),
    queryFn: () => api.get<RecurringTransaction>(`/recurring/${id}`),
    enabled: !!id,
  });
}

export function useCreateRecurringTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: RecurringTransactionCreateData) =>
      api.post<RecurringTransaction>('/recurring', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: recurringKeys.all }),
  });
}

export function useUpdateRecurringTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RecurringTransactionUpdateData }) =>
      api.patch<RecurringTransaction>(`/recurring/${id}`, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: recurringKeys.list() });
      qc.invalidateQueries({ queryKey: recurringKeys.detail(id) });
    },
  });
}

export function useDeleteRecurringTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/recurring/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: recurringKeys.all }),
  });
}
```

**Commit:** `feat(hooks): add recurring transaction React Query hooks`

---

## Task 5: Receipt List Page

**File:** `frontend/src/routes/ReceiptListPage.tsx`

```typescript
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useReceipts, useDeleteReceipt } from '@/hooks/use-receipts';
import type { ReceiptStatus } from '@/types/receipt';

const statusStyles: Record<ReceiptStatus, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  PROCESSED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  MANUAL_REVIEW: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

function StatusBadge({ status }: { status: ReceiptStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusStyles[status]}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString();
}

export function ReceiptListPage() {
  const { data, isLoading, error } = useReceipts();
  const deleteReceipt = useDeleteReceipt();

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load receipts.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Receipts</h1>
        <Button asChild><Link to="/receipts/upload">Upload Receipt</Link></Button>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} Receipts</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Vendor</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Amount</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Date</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Category</th>
                <th className="w-24" />
              </tr>
            </thead>
            <tbody>
              {data?.results.map((receipt) => (
                <tr key={receipt.id} className="border-b last:border-0">
                  <td className="px-4 py-3 text-sm font-medium">{receipt.vendor || 'Unknown'}</td>
                  <td className="px-4 py-3 text-sm">{receipt.total_amount ? `$${receipt.total_amount}` : '—'}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{formatDate(receipt.receipt_date)}</td>
                  <td className="px-4 py-3"><StatusBadge status={receipt.status} /></td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{receipt.user_category_name ?? receipt.auto_category_name ?? '—'}</td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm" asChild><Link to={`/receipts/${receipt.id}`}>View</Link></Button>
                  </td>
                </tr>
              ))}
              {data?.results.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">No receipts yet. Upload one to get started.</td></tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Commit:** `feat(pages): add receipt list page with status badges`

---

## Task 6: Receipt Upload Page

**File:** `frontend/src/routes/ReceiptUploadPage.tsx`

```typescript
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useCreateReceipt } from '@/hooks/use-receipts';

export function ReceiptUploadPage() {
  const navigate = useNavigate();
  const createReceipt = useCreateReceipt();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [vendor, setVendor] = useState('');
  const [receiptDate, setReceiptDate] = useState('');
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    setUploadError(null);
    if (selected && selected.type.startsWith('image/')) {
      const url = URL.createObjectURL(selected);
      setPreview(url);
    } else {
      setPreview(null);
    }
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadError(null);

    if (!file) {
      setUploadError('Please select a file to upload.');
      return;
    }

    // For now, file is uploaded client-side to a placeholder URL.
    // In production, replace with actual file upload to Cloudflare R2 via presigned URL.
    const fileUrl = `/uploads/${Date.now()}-${file.name}`;

    createReceipt.mutate(
      {
        file_url: fileUrl,
        vendor: vendor || undefined,
        receipt_date: receiptDate || undefined,
      },
      {
        onSuccess: (receipt) => navigate(`/receipts/${receipt.id}`),
        onError: () => setUploadError('Failed to upload receipt. Please try again.'),
      },
    );
  }, [file, vendor, receiptDate, createReceipt, navigate]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/receipts')}>Back</Button>
        <h1 className="text-2xl font-bold">Upload Receipt</h1>
      </div>
      <Card>
        <CardHeader><CardTitle>Receipt Details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="file">Receipt Image</Label>
              <Input
                id="file"
                type="file"
                accept="image/*"
                onChange={handleFileChange}
              />
              {preview && (
                <div className="mt-4 max-w-xs">
                  <img src={preview} alt="Receipt preview" className="rounded-md border" />
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="vendor">Vendor (optional)</Label>
                <Input
                  id="vendor"
                  type="text"
                  placeholder="e.g., Walmart"
                  value={vendor}
                  onChange={(e) => setVendor(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="receiptDate">Receipt Date (optional)</Label>
                <Input
                  id="receiptDate"
                  type="date"
                  value={receiptDate}
                  onChange={(e) => setReceiptDate(e.target.value)}
                />
              </div>
            </div>

            {uploadError && (
              <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
                <p className="text-sm text-destructive">{uploadError}</p>
              </div>
            )}

            <div className="flex gap-2">
              <Button type="submit" disabled={createReceipt.isPending || !file}>
                {createReceipt.isPending ? 'Uploading...' : 'Upload & Process'}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate('/receipts')} disabled={createReceipt.isPending}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Commit:** `feat(pages): add receipt upload page with image preview`

---

## Task 7: Receipt Detail Page

**File:** `frontend/src/routes/ReceiptDetailPage.tsx`

```typescript
import { useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useReceipt, useProcessReceipt, useUpdateReceipt } from '@/hooks/use-receipts';
import { useAccounts } from '@/hooks/use-accounts';
import type { ReceiptStatus } from '@/types/receipt';

function StatusBadge({ status }: { status: ReceiptStatus }) {
  const styles: Record<ReceiptStatus, string> = {
    PENDING: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    PROCESSED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    MANUAL_REVIEW: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

export function ReceiptDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: receipt, isLoading, error } = useReceipt(id);
  const { data: accounts } = useAccounts();
  const processReceipt = useProcessReceipt();
  const updateReceipt = useUpdateReceipt();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const handleProcess = useCallback(() => {
    processReceipt.mutate(id, {
      onError: () => setConfirmError('Failed to start OCR processing.'),
    });
  }, [id, processReceipt]);

  const handleConfirmCategory = useCallback(() => {
    if (!selectedCategory) {
      setConfirmError('Please select a category.');
      return;
    }
    updateReceipt.mutate(
      { id, data: { user_category: selectedCategory } },
      {
        onSuccess: () => setConfirmError(null),
        onError: () => setConfirmError('Failed to save category.'),
      },
    );
  }, [id, selectedCategory, updateReceipt]);

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-16 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error || !receipt) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load receipt.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/receipts')}>Back</Button>
        <h1 className="text-2xl font-bold">Receipt Detail</h1>
        <StatusBadge status={receipt.status} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left: Receipt Image & OCR */}
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Receipt Image</CardTitle></CardHeader>
            <CardContent>
              <div className="rounded-md border bg-muted p-4 text-center text-sm text-muted-foreground">
                {receipt.file_url ? (
                  <p className="break-all">{receipt.file_url}</p>
                ) : (
                  <p>No image available.</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Extracted Text (OCR)</CardTitle></CardHeader>
            <CardContent>
              {receipt.ocr_text ? (
                <pre className="whitespace-pre-wrap rounded-md border bg-muted p-4 text-sm">{receipt.ocr_text}</pre>
              ) : (
                <p className="text-sm text-muted-foreground">No text extracted yet.</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Details & Actions */}
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Receipt Details</CardTitle></CardHeader>
            <CardContent>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between"><dt className="text-muted-foreground">Vendor</dt><dd className="font-medium">{receipt.vendor || '—'}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Amount</dt><dd className="font-medium">{receipt.total_amount ? `$${receipt.total_amount}` : '—'}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Date</dt><dd>{receipt.receipt_date ?? '—'}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Auto Category</dt><dd>{receipt.auto_category_name ?? '—'}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Linked Transaction</dt><dd>{receipt.transaction ? <Link to={`/transactions/${receipt.transaction}`} className="text-primary underline">View</Link> : '—'}</dd></div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Confirm Category</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="category">Account Category</Label>
                <select
                  id="category"
                  className="flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={selectedCategory ?? receipt.user_category ?? ''}
                  onChange={(e) => setSelectedCategory(e.target.value || null)}
                >
                  <option value="">— Select category —</option>
                  {accounts?.results.map((account) => (
                    <option key={account.id} value={account.id}>{account.full_name}</option>
                  ))}
                </select>
              </div>
              <Button onClick={handleConfirmCategory} disabled={updateReceipt.isPending}>
                {updateReceipt.isPending ? 'Saving...' : 'Save Category'}
              </Button>
            </CardContent>
          </Card>

          {receipt.status === 'PENDING' && (
            <Card>
              <CardContent className="pt-6">
                <Button onClick={handleProcess} disabled={processReceipt.isPending} className="w-full">
                  {processReceipt.isPending ? 'Processing...' : 'Start OCR Processing'}
                </Button>
              </CardContent>
            </Card>
          )}

          {confirmError && (
            <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
              <p className="text-sm text-destructive">{confirmError}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Commit:** `feat(pages): add receipt detail page with OCR display and category confirmation`

---

## Task 8: Recurring Transaction List Page

**File:** `frontend/src/routes/RecurringListPage.tsx`

```typescript
import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  useRecurringTransactions,
  useUpdateRecurringTransaction,
  useDeleteRecurringTransaction,
} from '@/hooks/use-recurring';
import type { RecurringFrequency } from '@/types/recurring';

const frequencyLabels: Record<RecurringFrequency, string> = {
  DAILY: 'Daily',
  WEEKLY: 'Weekly',
  MONTHLY: 'Monthly',
  QUARTERLY: 'Quarterly',
  YEARLY: 'Yearly',
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString();
}

export function RecurringListPage() {
  const { data, isLoading, error } = useRecurringTransactions();
  const updateRecurring = useUpdateRecurringTransaction();
  const deleteRecurring = useDeleteRecurringTransaction();

  const handleToggle = useCallback((id: string, currentEnabled: boolean) => {
    updateRecurring.mutate({ id, data: { enabled: !currentEnabled } });
  }, [updateRecurring]);

  const handleDelete = useCallback((id: string) => {
    if (window.confirm('Delete this recurring transaction template? This cannot be undone.')) {
      deleteRecurring.mutate(id);
    }
  }, [deleteRecurring]);

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load recurring transactions.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Recurring Transactions</h1>
        <Button asChild><Link to="/recurring/new">New Template</Link></Button>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} Templates</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Name</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Frequency</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Next Run</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Last Run</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Enabled</th>
                <th className="w-32" />
              </tr>
            </thead>
            <tbody>
              {data?.results.map((rt) => (
                <tr key={rt.id} className="border-b last:border-0">
                  <td className="px-4 py-3 text-sm font-medium">{rt.name}</td>
                  <td className="px-4 py-3 text-sm">{frequencyLabels[rt.frequency]}</td>
                  <td className="px-4 py-3 text-sm">{formatDate(rt.next_run)}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{formatDate(rt.last_run)}</td>
                  <td className="px-4 py-3">
                    <Button
                      variant={rt.enabled ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleToggle(rt.id, rt.enabled)}
                      disabled={updateRecurring.isPending}
                    >
                      {rt.enabled ? 'On' : 'Off'}
                    </Button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm" asChild><Link to={`/recurring/${rt.id}`}>Edit</Link></Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(rt.id)} disabled={deleteRecurring.isPending}>Delete</Button>
                  </td>
                </tr>
              ))}
              {data?.results.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">No recurring templates yet.</td></tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Commit:** `feat(pages): add recurring transaction list page with enabled toggle`

---

## Task 9: Recurring New Page

**File:** `frontend/src/routes/RecurringNewPage.tsx`

```typescript
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useCreateRecurringTransaction } from '@/hooks/use-recurring';
import type { RecurringFrequency } from '@/types/recurring';

const frequencies: RecurringFrequency[] = ['DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'YEARLY'];

export function RecurringNewPage() {
  const navigate = useNavigate();
  const createRecurring = useCreateRecurringTransaction();
  const [name, setName] = useState('');
  const [frequency, setFrequency] = useState<RecurringFrequency>('MONTHLY');
  const [startDate, setStartDate] = useState('');
  const [nextRun, setNextRun] = useState('');
  const [endDate, setEndDate] = useState('');
  const [autoCreate, setAutoCreate] = useState(false);
  const [advanceNoticeDays, setAdvanceNoticeDays] = useState(0);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError('Name is required.');
      return;
    }
    if (!startDate) {
      setFormError('Start date is required.');
      return;
    }
    if (!nextRun) {
      setFormError('Next run date is required.');
      return;
    }

    // Template contains empty splits/description — user fills in via edit page after creation.
    const template: Record<string, unknown> = {
      description: name,
      splits: [],
    };

    createRecurring.mutate(
      {
        name,
        template,
        frequency,
        start_date: startDate,
        next_run: nextRun,
        end_date: endDate || null,
        auto_create: autoCreate,
        advance_notice_days: advanceNoticeDays,
      },
      {
        onSuccess: () => navigate('/recurring'),
        onError: () => setFormError('Failed to create recurring transaction.'),
      },
    );
  }, [name, frequency, startDate, nextRun, endDate, autoCreate, advanceNoticeDays, createRecurring, navigate]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/recurring')}>Back</Button>
        <h1 className="text-2xl font-bold">New Recurring Template</h1>
      </div>
      <Card>
        <CardHeader><CardTitle>Template Details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                type="text"
                placeholder="e.g., Monthly Rent"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="frequency">Frequency</Label>
                <select
                  id="frequency"
                  className="flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value as RecurringFrequency)}
                >
                  {frequencies.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="startDate">Start Date</Label>
                <Input id="startDate" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="nextRun">Next Run Date</Label>
                <Input id="nextRun" type="date" value={nextRun} onChange={(e) => setNextRun(e.target.value)} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="endDate">End Date (optional)</Label>
                <Input id="endDate" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="flex items-center gap-2">
                <input
                  id="autoCreate"
                  type="checkbox"
                  checked={autoCreate}
                  onChange={(e) => setAutoCreate(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="autoCreate">Auto-create transactions</Label>
              </div>

              <div className="space-y-2">
                <Label htmlFor="advanceNotice">Advance Notice (days)</Label>
                <Input
                  id="advanceNotice"
                  type="number"
                  min={0}
                  value={advanceNoticeDays}
                  onChange={(e) => setAdvanceNoticeDays(Number(e.target.value))}
                />
              </div>
            </div>

            {formError && (
              <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
                <p className="text-sm text-destructive">{formError}</p>
              </div>
            )}

            <div className="flex gap-2">
              <Button type="submit" disabled={createRecurring.isPending}>
                {createRecurring.isPending ? 'Creating...' : 'Create Template'}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate('/recurring')} disabled={createRecurring.isPending}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Commit:** `feat(pages): add new recurring transaction template page`

---

## Task 10: Wire Routes in App.tsx

Replace the placeholder routes in `frontend/src/App.tsx` for `/receipts`, `/recurring` and add sub-routes.

**File to edit:** `frontend/src/App.tsx`

Replace the placeholder `<Route path="/receipts" ...>` and `<Route path="/recurring" ...>` lines, and add imports and sub-routes.

```diff
+ import { ReceiptListPage } from '@/routes/ReceiptListPage';
+ import { ReceiptUploadPage } from '@/routes/ReceiptUploadPage';
+ import { ReceiptDetailPage } from '@/routes/ReceiptDetailPage';
+ import { RecurringListPage } from '@/routes/RecurringListPage';
+ import { RecurringNewPage } from '@/routes/RecurringNewPage';
```

Inside the `<Route element={<RootLayout />}>` block, replace:

```diff
- <Route path="/receipts" element={<PlaceholderPage title="Receipts" />} />
- <Route path="/recurring" element={<PlaceholderPage title="Recurring" />} />
+ <Route path="/receipts" element={<ReceiptListPage />} />
+ <Route path="/receipts/upload" element={<ReceiptUploadPage />} />
+ <Route path="/receipts/:id" element={<ReceiptDetailPage />} />
+ <Route path="/recurring" element={<RecurringListPage />} />
+ <Route path="/recurring/new" element={<RecurringNewPage />} />
```

**Commit:** `feat(routes): wire receipt and recurring pages into router`

---

## Task 11: Verify Backend `/process` Endpoint URL

The `ReceiptViewSet.process` action is defined as `@action(detail=True, methods=['post'])`. DRF DefaultRouter with `basename='receipt'` generates:

- `POST /api/v1/receipts/{id}/process/`

The hook in Task 3 uses `/receipts/${id}/process/` which matches.

**No backend changes required.** Confirm by checking `python manage.py show_urls | grep process` or reviewing `backend/gnucash_web/urls.py` which already registers `ReceiptViewSet` with basename `'receipt'`.

**Commit:** N/A (verification only)

---

## Task 12: TypeScript Type Check

Run:

```bash
cd frontend && npx tsc --noEmit
```

Fix any type errors. Expected: zero errors.

**Commit:** N/A

---

## Execution Order

Tasks can be executed in this dependency order:

1. Task 1 (Receipt types) -- no deps
2. Task 2 (Recurring types) -- no deps
3. Task 3 (Receipt hooks) -- depends on Task 1
4. Task 4 (Recurring hooks) -- depends on Task 2
5. Task 5 (Receipt list page) -- depends on Task 3
6. Task 6 (Receipt upload page) -- depends on Task 3
7. Task 7 (Receipt detail page) -- depends on Task 3
8. Task 8 (Recurring list page) -- depends on Task 4
9. Task 9 (Recurring new page) -- depends on Task 4
10. Task 10 (Wire routes) -- depends on Tasks 5-9
11. Task 11 (Verify backend) -- no deps, can run anytime
12. Task 12 (Type check) -- depends on all above

Parallel groups:
- Group A: Tasks 1, 2
- Group B: Tasks 3, 4
- Group C: Tasks 5, 6, 7, 8, 9
- Group D: Tasks 10, 11, 12
