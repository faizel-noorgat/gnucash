// frontend/src/features/budgets/components/BudgetForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const budgetSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().min(1, 'End date is required'),
  style: z.enum(['TRADITIONAL', 'ENVELOPE']).default('TRADITIONAL'),
  rollover: z.boolean().default(false),
});
type BudgetFormValues = z.infer<typeof budgetSchema>;

export function BudgetForm({ onSuccess, onCancel }: { onSuccess?: () => void; onCancel?: () => void }) {
  const form = useForm<BudgetFormValues>({ resolver: zodResolver(budgetSchema), defaultValues: { style: 'TRADITIONAL', rollover: false } });
  const onSubmit = (data: BudgetFormValues) => { onSuccess?.(); };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      <Card>
        <CardHeader><CardTitle>New Budget</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2"><Label htmlFor="name">Name</Label><Input id="name" {...form.register('name')} /></div>
          <div className="space-y-2"><Label htmlFor="start_date">Start Date</Label><Input id="start_date" type="date" {...form.register('start_date')} /></div>
          <div className="space-y-2"><Label htmlFor="end_date">End Date</Label><Input id="end_date" type="date" {...form.register('end_date')} /></div>
          <div className="space-y-2">
            <Label>Style</Label>
            <select {...form.register('style')} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="TRADITIONAL">Traditional</option>
              <option value="ENVELOPE">Envelope</option>
            </select>
          </div>
        </CardContent>
        <CardFooter className="flex justify-between gap-4">
          {onCancel && <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>}
          <Button type="submit" className="ml-auto">Create Budget</Button>
        </CardFooter>
      </Card>
    </form>
  );
}
