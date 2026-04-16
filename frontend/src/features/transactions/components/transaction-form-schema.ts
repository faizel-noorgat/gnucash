import { z } from 'zod';

export const transactionFormSchema = z.object({
  currency: z.string().min(1, 'Currency is required.'),
  post_date: z.string().min(1, 'Date is required.'),
  description: z.string().min(1, 'Description is required.').max(200),
  notes: z.string().max(1000).optional().default(''),
  splits_data: z
    .array(z.object({
      account: z.string().uuid('Please select a valid account.'),
      value: z.string().min(1, 'Value is required.').refine((v) => { const n = parseFloat(v); return !isNaN(n) && n !== 0; }, { message: 'Must be a non-zero number.' }),
      quantity: z.string().optional(),
      memo: z.string().max(200).optional().default(''),
    }))
    .min(2, 'At least 2 splits required.')
    .refine((splits) => Math.abs(splits.reduce((sum, s) => sum + (parseFloat(s.value) || 0), 0)) < 0.005, { message: 'Splits must balance to zero.' }),
});

export type TransactionFormValues = z.infer<typeof transactionFormSchema>;
