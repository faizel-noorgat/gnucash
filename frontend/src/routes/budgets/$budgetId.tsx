// frontend/src/routes/budgets/$budgetId.tsx
import { useParams } from 'react-router-dom';
import { useBudget } from '@/hooks/use-budgets';
import { Progress } from '@/components/ui/progress';

export function BudgetDetail() {
  const { budgetId } = useParams<{ budgetId: string }>();
  const { data } = useBudget(budgetId!);
  if (!data) return null;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{data.name}</h1>
      <div className="space-y-4">
        {data.categories.map((cat) => (
          <div key={cat.id} className="rounded-lg border p-4">
            <div className="flex justify-between"><span className="font-medium">{cat.account_name}</span><span>{cat.amount}</span></div>
            <Progress value={50} className="mt-2" />
          </div>
        ))}
      </div>
    </div>
  );
}
