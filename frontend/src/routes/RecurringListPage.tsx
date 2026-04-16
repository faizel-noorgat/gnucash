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
