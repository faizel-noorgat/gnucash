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
