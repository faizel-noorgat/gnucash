// frontend/src/routes/budgets/index.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useBudgets } from '@/hooks/use-budgets';
import { BudgetCard } from '@/features/budgets/components/BudgetCard';

export function BudgetList() {
  const { data, isLoading } = useBudgets();
  if (isLoading) return <div className="h-48 w-full animate-pulse rounded bg-muted" />;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Budgets</h1>
        <Button asChild><Link to="/budgets/new">New Budget</Link></Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {data?.results.map((b) => <BudgetCard key={b.id} budget={b} />)}
      </div>
    </div>
  );
}
