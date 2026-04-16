import { CalendarIcon, Loader2 } from 'lucide-react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { SplitInput } from '@/components/split-input';
import { useCreateTransaction } from '@/hooks/use-transactions';
import { transactionFormSchema, type TransactionFormValues } from './transaction-form-schema';

export interface TransactionFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  defaultCurrency?: string;
}

export function TransactionForm({ onSuccess, onCancel, defaultCurrency = 'USD' }: TransactionFormProps) {
  const createMutation = useCreateTransaction();
  const form = useForm<TransactionFormValues>({
    resolver: zodResolver(transactionFormSchema),
    defaultValues: {
      currency: defaultCurrency,
      post_date: format(new Date(), 'yyyy-MM-dd'),
      description: '',
      notes: '',
      splits_data: [
        { account: '', value: '', quantity: '1', memo: '' },
        { account: '', value: '', quantity: '1', memo: '' },
      ],
    },
  });

  const onSubmit = (data: TransactionFormValues) => {
    createMutation.mutate(data, { onSuccess: () => { form.reset(); onSuccess?.(); } });
  };

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader><CardTitle>New Transaction</CardTitle></CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Date</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className={cn('w-full justify-start text-left font-normal', !form.watch('post_date') && 'text-muted-foreground')}>
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {form.watch('post_date') ? format(new Date(form.watch('post_date')), 'PPP') : 'Pick a date'}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar mode="single" selected={new Date(form.watch('post_date'))} onSelect={(date) => { if (date) form.setValue('post_date', format(date, 'yyyy-MM-dd'), { shouldDirty: true, shouldValidate: true }); }} initialFocus />
                  </PopoverContent>
                </Popover>
                {form.formState.errors.post_date && <p className="text-xs text-red-600">{form.formState.errors.post_date.message}</p>}
              </div>
              <div className="space-y-2">
                <Label>Currency</Label>
                <Input {...form.register('currency')} placeholder="USD" maxLength={3} className="uppercase" />
                {form.formState.errors.currency && <p className="text-xs text-red-600">{form.formState.errors.currency.message}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input id="description" {...form.register('description')} placeholder="e.g., Monthly salary deposit" />
              {form.formState.errors.description && <p className="text-xs text-red-600">{form.formState.errors.description.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Input id="notes" {...form.register('notes')} placeholder="Additional details..." />
            </div>
            <Separator />
            <SplitInput />
            {form.formState.errors.splits_data && (
              <p className="text-sm text-red-600">{typeof form.formState.errors.splits_data.message === 'string' ? form.formState.errors.splits_data.message : 'Fix split errors above.'}</p>
            )}
          </CardContent>
          <CardFooter className="flex justify-between gap-4">
            {onCancel && <Button type="button" variant="outline" onClick={onCancel} disabled={createMutation.isPending}>Cancel</Button>}
            <div className="ml-auto flex items-center gap-4">
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Transaction
              </Button>
            </div>
          </CardFooter>
        </Card>
      </form>
    </FormProvider>
  );
}
