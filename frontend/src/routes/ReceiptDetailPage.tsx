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
