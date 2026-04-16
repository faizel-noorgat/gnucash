import { Badge } from '@/components/ui/badge';
import type { ReconcileState } from '@/types/register';

const RECONCILE_CONFIG: Record<
  ReconcileState,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  n: { label: 'Not Reconciled', variant: 'secondary' },
  c: { label: 'Cleared', variant: 'outline' },
  y: { label: 'Reconciled', variant: 'default' },
  f: { label: 'Frozen', variant: 'destructive' },
  v: { label: 'Void', variant: 'destructive' },
};

interface ReconcileBadgeProps {
  state: ReconcileState;
}

export function ReconcileBadge({ state }: ReconcileBadgeProps) {
  const config = RECONCILE_CONFIG[state] ?? RECONCILE_CONFIG['n'];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
