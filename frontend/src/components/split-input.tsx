// frontend/src/components/split-input.tsx
import * as React from 'react';
import { Plus, Trash2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useFormContext } from 'react-hook-form';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { AccountPicker } from '@/components/account-picker';
import { useSplitBalance } from '@/hooks/use-split-balance';

export interface SplitInputProps {
  fieldName?: 'splits_data';
  maxSplits?: number;
}

export function SplitInput({ fieldName = 'splits_data', maxSplits = 20 }: SplitInputProps) {
  const form = useFormContext();
  const fields = form.watch(fieldName) as { account: string; value: string; memo: string }[];

  const values = fields?.map((f) => f.value) ?? [];
  const { isBalanced, isEmpty, difference } = useSplitBalance(values);

  const addSplit = () => {
    if ((fields?.length ?? 0) >= maxSplits) return;
    const current = form.getValues(fieldName) ?? [];
    form.setValue(fieldName, [...current, { account: '', value: '', quantity: '1', memo: '' }], { shouldDirty: true, shouldValidate: true });
  };

  const removeSplit = (index: number) => {
    if ((fields?.length ?? 0) <= 2) return;
    const current = form.getValues(fieldName);
    current.splice(index, 1);
    form.setValue(fieldName, current, { shouldDirty: true, shouldValidate: true });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label>Splits</Label>
        {isEmpty ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <AlertCircle className="h-4 w-4" /><span>Add at least one split.</span>
          </div>
        ) : (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className={cn('flex items-center gap-2 text-sm font-medium', isBalanced ? 'text-green-600' : 'text-red-600')} role="status" aria-live="polite">
                  {isBalanced ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                  <span>{isBalanced ? 'Balanced' : `Unbalanced: ${difference}`}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent><p>Sum of all split values must equal 0. Current: {difference}</p></TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40%]">Account</TableHead>
              <TableHead className="w-[20%]">Value</TableHead>
              <TableHead className="w-[30%]">Memo</TableHead>
              <TableHead className="w-[10%] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {fields?.map((field, index) => (
              <TableRow key={index}>
                <TableCell>
                  <AccountPicker
                    value={field.account || null}
                    onValueChange={(id) => { form.setValue(`${fieldName}.${index}.account`, id, { shouldDirty: true, shouldValidate: true }); }}
                    placeholder="Choose account..."
                    aria-label={`Account for split ${index + 1}`}
                  />
                  {form.formState.errors.splits_data?.[index]?.account && (
                    <p className="mt-1 text-xs text-red-600">{String(form.formState.errors.splits_data[index].account?.message)}</p>
                  )}
                </TableCell>
                <TableCell>
                  <Input type="number" step="0.01" placeholder="0.00" value={field.value ?? ''} onChange={(e) => { form.setValue(`${fieldName}.${index}.value`, e.target.value, { shouldDirty: true, shouldValidate: true }); }} aria-label={`Value for split ${index + 1}`} />
                  {form.formState.errors.splits_data?.[index]?.value && (
                    <p className="mt-1 text-xs text-red-600">{String(form.formState.errors.splits_data[index].value?.message)}</p>
                  )}
                </TableCell>
                <TableCell>
                  <Input placeholder="Optional memo..." value={field.memo ?? ''} onChange={(e) => { form.setValue(`${fieldName}.${index}.memo`, e.target.value, { shouldDirty: true }); }} aria-label={`Memo for split ${index + 1}`} />
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="icon" onClick={() => removeSplit(index)} aria-label={`Remove split ${index + 1}`} disabled={(fields?.length ?? 0) <= 2}>
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Button type="button" variant="outline" size="sm" onClick={addSplit} disabled={(fields?.length ?? 0) >= maxSplits}>
        <Plus className="mr-2 h-4 w-4" /> Add split
      </Button>
    </div>
  );
}
