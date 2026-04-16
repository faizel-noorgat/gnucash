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
