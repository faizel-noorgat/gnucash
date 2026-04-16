import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useCreateRecurringTransaction } from '@/hooks/use-recurring';
import type { RecurringFrequency } from '@/types/recurring';

const frequencies: RecurringFrequency[] = ['DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'YEARLY'];

export function RecurringNewPage() {
  const navigate = useNavigate();
  const createRecurring = useCreateRecurringTransaction();
  const [name, setName] = useState('');
  const [frequency, setFrequency] = useState<RecurringFrequency>('MONTHLY');
  const [startDate, setStartDate] = useState('');
  const [nextRun, setNextRun] = useState('');
  const [endDate, setEndDate] = useState('');
  const [autoCreate, setAutoCreate] = useState(false);
  const [advanceNoticeDays, setAdvanceNoticeDays] = useState(0);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError('Name is required.');
      return;
    }
    if (!startDate) {
      setFormError('Start date is required.');
      return;
    }
    if (!nextRun) {
      setFormError('Next run date is required.');
      return;
    }

    // Template contains empty splits/description — user fills in via edit page after creation.
    const template: Record<string, unknown> = {
      description: name,
      splits: [],
    };

    createRecurring.mutate(
      {
        name,
        template,
        frequency,
        start_date: startDate,
        next_run: nextRun,
        end_date: endDate || null,
        auto_create: autoCreate,
        advance_notice_days: advanceNoticeDays,
      },
      {
        onSuccess: () => navigate('/recurring'),
        onError: () => setFormError('Failed to create recurring transaction.'),
      },
    );
  }, [name, frequency, startDate, nextRun, endDate, autoCreate, advanceNoticeDays, createRecurring, navigate]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/recurring')}>Back</Button>
        <h1 className="text-2xl font-bold">New Recurring Template</h1>
      </div>
      <Card>
        <CardHeader><CardTitle>Template Details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                type="text"
                placeholder="e.g., Monthly Rent"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="frequency">Frequency</Label>
                <select
                  id="frequency"
                  className="flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value as RecurringFrequency)}
                >
                  {frequencies.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="startDate">Start Date</Label>
                <Input id="startDate" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="nextRun">Next Run Date</Label>
                <Input id="nextRun" type="date" value={nextRun} onChange={(e) => setNextRun(e.target.value)} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="endDate">End Date (optional)</Label>
                <Input id="endDate" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="flex items-center gap-2">
                <input
                  id="autoCreate"
                  type="checkbox"
                  checked={autoCreate}
                  onChange={(e) => setAutoCreate(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="autoCreate">Auto-create transactions</Label>
              </div>

              <div className="space-y-2">
                <Label htmlFor="advanceNotice">Advance Notice (days)</Label>
                <Input
                  id="advanceNotice"
                  type="number"
                  min={0}
                  value={advanceNoticeDays}
                  onChange={(e) => setAdvanceNoticeDays(Number(e.target.value))}
                />
              </div>
            </div>

            {formError && (
              <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
                <p className="text-sm text-destructive">{formError}</p>
              </div>
            )}

            <div className="flex gap-2">
              <Button type="submit" disabled={createRecurring.isPending}>
                {createRecurring.isPending ? 'Creating...' : 'Create Template'}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate('/recurring')} disabled={createRecurring.isPending}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
