// frontend/src/features/budgets/components/BudgetCard.tsx
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Budget } from '@/types/budget';

export function BudgetCard({ budget }: { budget: Budget }) {
  return (
    <Link to={`/budgets/${budget.id}`} className="block">
      <Card className="hover:bg-muted/50">
        <CardHeader><CardTitle className="text-lg">{budget.name}</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{budget.start_date} — {budget.end_date}</p>
          <p className="text-sm text-muted-foreground">{budget.style}{budget.rollover ? ' (Rollover)' : ''}</p>
          <p className="text-sm text-muted-foreground">{budget.categories.length} categories</p>
        </CardContent>
      </Card>
    </Link>
  );
}
