import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { format } from 'date-fns';
import { ArrowLeft, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAccount } from '@/hooks/use-accounts';
import { useAccountRegister } from '@/hooks/use-account-register';
import { RegisterEntryRow } from '@/features/register/components/RegisterEntryRow';

function formatCurrency(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  const sign = num < 0 ? '-' : '';
  const abs = Math.abs(num).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${sign}$${abs}`;
}

export function AccountRegisterPage() {
  const { id } = useParams<{ id: string }>();
  const accountId = id ?? '';

  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  const { data: account, isLoading: accountLoading } = useAccount(accountId);
  const { data, isLoading, error } = useAccountRegister(accountId, {
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  });

  if (accountLoading || isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-10 w-full animate-pulse rounded bg-muted" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load register.</p>
      </div>
    );
  }

  if (!data) return null;

  let runningBalance = 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/accounts">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{data.account.full_name || data.account.name}</h1>
          <p className="text-sm text-muted-foreground">
            {data.account.account_type} &middot; Balance: {formatCurrency(data.running_balance)}
          </p>
        </div>
      </div>

      {/* Date filter */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Filter by Date
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div>
              <label htmlFor="start-date" className="text-sm text-muted-foreground">From</label>
              <input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="end-date" className="text-sm text-muted-foreground">To</label>
              <input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              />
            </div>
            {(startDate || endDate) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setStartDate(''); setEndDate(''); }}
              >
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Register table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Transactions ({data.transactions.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Num</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Description / Account</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Amount</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Balance</th>
              </tr>
            </thead>
            <tbody>
              {data.transactions.map((entry) => {
                runningBalance += parseFloat(entry.split_value);
                return (
                  <RegisterEntryRow
                    key={entry.id}
                    entry={entry}
                    runningBalance={runningBalance.toString()}
                  />
                );
              })}
              {data.transactions.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-muted-foreground">
                    No transactions found for this account.
                    {(startDate || endDate) && ' Try adjusting the date filter.'}
                  </td>
                </tr>
              )}
            </tbody>
            {data.transactions.length > 0 && (
              <tfoot>
                <tr className="border-t font-semibold">
                  <td colSpan={3} className="px-4 py-3 text-sm text-right">Ending Balance</td>
                  <td />
                  <td />
                  <td className="px-4 py-3 text-sm text-right tabular-nums">
                    {formatCurrency(data.running_balance)}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
