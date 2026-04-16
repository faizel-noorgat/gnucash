// frontend/src/routes/reports/index.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export function ReportsIndex() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Reports</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { label: 'Balance Sheet', path: '/reports/balance-sheet', desc: 'Assets = Liabilities + Equity' },
          { label: 'Income Statement', path: '/reports/income-statement', desc: 'Revenue - Expenses' },
          { label: 'Cash Flow', path: '/reports/cash-flow', desc: 'Money in vs money out' },
        ].map((r) => (
          <Link key={r.path} to={r.path} className="block rounded-lg border p-6 hover:bg-muted/50">
            <h3 className="font-semibold">{r.label}</h3>
            <p className="text-sm text-muted-foreground">{r.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
