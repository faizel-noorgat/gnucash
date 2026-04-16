// frontend/src/routes/reports/balance-sheet.tsx
import { useState } from 'react';
import { format } from 'date-fns';
import { ReportDatePicker } from '@/components/reports/ReportDatePicker';
import { ReportTable } from '@/components/reports/ReportTable';
import { useBalanceSheet } from '@/hooks/use-reports';

export function BalanceSheetPage() {
  const [asOf, setAsOf] = useState(format(new Date(), 'yyyy-MM-dd'));
  const { data, isLoading } = useBalanceSheet(asOf);

  if (isLoading) return <div className="h-48 w-full animate-pulse rounded bg-muted" />;
  if (!data) return null;

  const fmt = (v: string) => parseFloat(v).toLocaleString('en-US', { style: 'currency', currency: 'USD' });

  return (
    <div className="space-y-6">
      <div className="flex gap-4"><ReportDatePicker label="As of" value={asOf} onChange={setAsOf} /></div>
      <ReportTable title="Balance Sheet" rows={[
        { label: 'Total Assets', value: fmt(data.assets), bold: true },
        { label: 'Total Liabilities', value: fmt(data.liabilities), bold: true },
        { label: 'Equity', value: fmt(data.equity), bold: true },
        { label: 'Retained Earnings', value: fmt(data.retained_earnings), bold: true },
        { label: 'Balanced', value: data.balanced ? 'Yes' : 'No', bold: true },
      ]} />
    </div>
  );
}
