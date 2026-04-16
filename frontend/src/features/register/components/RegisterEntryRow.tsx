import { format } from 'date-fns';
import type { RegisterEntry } from '@/types/register';
import { ReconcileBadge } from './ReconcileBadge';

interface RegisterEntryRowProps {
  entry: RegisterEntry;
  runningBalance: string;
}

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

export function RegisterEntryRow({ entry, runningBalance }: RegisterEntryRowProps) {
  return (
    <tr className="border-b last:border-0 hover:bg-muted/50 transition-colors">
      <td className="px-4 py-2.5 text-sm text-muted-foreground whitespace-nowrap">
        {format(new Date(entry.post_date + 'T00:00:00'), 'MMM d, yyyy')}
      </td>
      <td className="px-4 py-2.5 text-sm font-mono whitespace-nowrap">{entry.num || '—'}</td>
      <td className="px-4 py-2.5 text-sm">
        <div className="font-medium">{entry.description}</div>
        {entry.split_memo && (
          <div className="text-xs text-muted-foreground truncate max-w-xs">{entry.split_memo}</div>
        )}
        <div className="text-xs text-muted-foreground">
          {entry.other_accounts.join(', ') || '—'}
        </div>
      </td>
      <td className={`px-4 py-2.5 text-sm text-right tabular-nums whitespace-nowrap ${parseFloat(entry.split_value) < 0 ? 'text-destructive' : 'text-foreground'}`}>
        {formatCurrency(entry.split_value)}
      </td>
      <td className="px-4 py-2.5 text-sm text-center whitespace-nowrap">
        <ReconcileBadge state={entry.reconcile_state} />
      </td>
      <td className="px-4 py-2.5 text-sm text-right tabular-nums font-medium whitespace-nowrap">
        {formatCurrency(runningBalance)}
      </td>
    </tr>
  );
}
