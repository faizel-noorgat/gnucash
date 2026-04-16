// frontend/src/routes/reports/cash-flow.tsx
import { useState } from 'react';
import { format, subMonths } from 'date-fns';
import { ReportDatePicker } from '@/components/reports/ReportDatePicker';
import { ReportTable } from '@/components/reports/ReportTable';
import { useCashFlow } from '@/hooks/use-reports';

export function CashFlowPage() {
  const [start, setStart] = useState(format(subMonths(new Date(), 12), 'yyyy-MM-dd'));
  const [end, setEnd] = useState(format(new Date(), 'yyyy-MM-dd'));
  const { data, isLoading } = useCashFlow(start, end);
  if (isLoading) return <div className="h-48 w-full animate-pulse rounded bg-muted" />;
  if (!data) return null;
  const fmt = (v: string) => parseFloat(v).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <ReportDatePicker label="From" value={start} onChange={setStart} />
        <ReportDatePicker label="To" value={end} onChange={setEnd} />
      </div>
      <ReportTable title="Cash Flow" rows={[
        { label: 'Money In', value: fmt(data.money_in) },
        { label: 'Money Out', value: fmt(data.money_out) },
        { label: 'Net Cash Flow', value: fmt(data.net_cash_flow), bold: true },
      ]} />
    </div>
  );
}
