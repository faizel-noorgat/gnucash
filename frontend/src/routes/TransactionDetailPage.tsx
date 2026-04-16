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
