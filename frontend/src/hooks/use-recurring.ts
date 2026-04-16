import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  RecurringTransaction,
  RecurringTransactionListResponse,
  RecurringTransactionCreateData,
  RecurringTransactionUpdateData,
} from '@/types/recurring';

export const recurringKeys = {
  all: ['recurring'] as const,
  list: () => [...recurringKeys.all, 'list'] as const,
  detail: (id: string) => [...recurringKeys.all, 'detail', id] as const,
};

export function useRecurringTransactions() {
  return useQuery({
    queryKey: recurringKeys.list(),
    queryFn: () => api.get<RecurringTransactionListResponse>('/recurring'),
  });
}

export function useRecurringTransaction(id: string) {
  return useQuery({
    queryKey: recurringKeys.detail(id),
    queryFn: () => api.get<RecurringTransaction>(`/recurring/${id}`),
    enabled: !!id,
  });
}

export function useCreateRecurringTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: RecurringTransactionCreateData) =>
      api.post<RecurringTransaction>('/recurring', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: recurringKeys.all }),
  });
}

export function useUpdateRecurringTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RecurringTransactionUpdateData }) =>
      api.patch<RecurringTransaction>(`/recurring/${id}`, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: recurringKeys.list() });
      qc.invalidateQueries({ queryKey: recurringKeys.detail(id) });
    },
  });
}

export function useDeleteRecurringTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/recurring/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: recurringKeys.all }),
  });
}
