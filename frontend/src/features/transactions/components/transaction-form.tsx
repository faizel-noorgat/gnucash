import { CalendarIcon, Loader2 } from 'lucide-react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { format } from 'date-fns';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { SplitInput } from '@/components/split-input';
import { useCreateTransaction, useUpdateTransaction, useTransaction } from '@/hooks/use-transactions';
import { transactionFormSchema, type TransactionFormValues } from './transaction-form-schema';

export interface TransactionFormProps {
  transactionId?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
  defaultCurrency?: string;
}

export function TransactionForm({ transactionId, onSuccess, onCancel, defaultCurrency = 'USD' }: TransactionFormProps) {
  const isEdit = !!transactionId;
  const createMutation = useCreateTransaction();
  const updateMutation = useUpdateTransaction();
  const { data: existing, isLoading: isLoadingTx } = useTransaction(transactionId ?? '');
  const isSubmitting = createMutation.isPending || updateMutation.isPending;

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

  useEffect(() => {
    if (existing && isEdit) {
      form.reset({
        currency: existing.currency,
        post_date: existing.post_date,
        description: existing.description,
        notes: existing.notes ?? '',
        splits_data: existing.splits.map((s) => ({
          account: s.account,
          value: s.value,
          quantity: s.quantity,
          memo: s.memo,
        })),
      });
    }
  }, [existing, isEdit, form]);

  const onSubmit = (data: TransactionFormValues) => {
    if (isEdit) {
      updateMutation.mutate({ id: transactionId!, ...data }, { onSuccess });
    } else {
      createMutation.mutate(data, {
        onSuccess: () => {
          form.reset();
          onSuccess?.();
        },
      });
    }
  };

  if (isEdit && isLoadingTx) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          <span className="text-sm text-muted-foreground">Loading transaction…</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader><CardTitle>{isEdit ? 'Edit Transaction' : 'New Transaction'}</CardTitle></CardHeader>
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
              <Input id="notes" {...form.register('notes')} placeholder="Additional details…" />
            </div>
            <Separator />
            <SplitInput />
            {form.formState.errors.splits_data && (
              <p className="text-sm text-red-600">{typeof form.formState.errors.splits_data.message === 'string' ? form.formState.errors.splits_data.message : 'Fix split errors above.'}</p>
            )}
          </CardContent>
          <CardFooter className="flex justify-between gap-4">
            {onCancel && <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>Cancel</Button>}
            <div className="ml-auto flex items-center gap-4">
              {form.formState.isDirty && <span className="text-xs text-muted-foreground">Unsaved changes</span>}
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEdit ? 'Update Transaction' : 'Create Transaction'}
              </Button>
            </div>
          </CardFooter>
        </Card>
      </form>
    </FormProvider>
  );
}
