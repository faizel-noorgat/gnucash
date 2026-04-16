// frontend/src/hooks/use-transactions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Transaction, TransactionListResponse } from '@/types/transaction';

export const txKeys = {
  all: ['transactions'] as const,
  list: (params?: { page?: number }) => [...txKeys.all, 'list', params] as const,
  detail: (id: string) => [...txKeys.all, 'detail', id] as const,
};

export function useTransactions(params?: { page?: number }) {
  return useQuery({
    queryKey: txKeys.list(params),
    queryFn: () => api.get<TransactionListResponse>('/transactions/'),
  });
}

export function useTransaction(id: string) {
  return useQuery({
    queryKey: txKeys.detail(id),
    queryFn: () => api.get<Transaction>(`/transactions/${id}`),
    enabled: !!id,
  });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { currency: string; post_date: string; description: string; notes?: string; splits_data: { account: string; value: string; quantity?: string; memo?: string }[] }) =>
      api.post<Transaction>('/transactions', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: txKeys.all }),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/transactions/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: txKeys.all }),
  });
}
