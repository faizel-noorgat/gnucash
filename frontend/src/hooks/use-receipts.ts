import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  Receipt,
  ReceiptListResponse,
  ReceiptCreateData,
  ReceiptUpdateData,
} from '@/types/receipt';

export const receiptKeys = {
  all: ['receipts'] as const,
  list: () => [...receiptKeys.all, 'list'] as const,
  detail: (id: string) => [...receiptKeys.all, 'detail', id] as const,
};

export function useReceipts() {
  return useQuery({
    queryKey: receiptKeys.list(),
    queryFn: () => api.get<ReceiptListResponse>('/receipts'),
  });
}

export function useReceipt(id: string) {
  return useQuery({
    queryKey: receiptKeys.detail(id),
    queryFn: () => api.get<Receipt>(`/receipts/${id}`),
    enabled: !!id,
  });
}

export function useCreateReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ReceiptCreateData) => api.post<Receipt>('/receipts', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: receiptKeys.all }),
  });
}

export function useUpdateReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ReceiptUpdateData }) =>
      api.patch<Receipt>(`/receipts/${id}`, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: receiptKeys.list() });
      qc.invalidateQueries({ queryKey: receiptKeys.detail(id) });
    },
  });
}

export function useProcessReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<{ status: string }>(`/receipts/${id}/process/`, {}),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: receiptKeys.detail(id) });
    },
  });
}

export function useDeleteReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/receipts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: receiptKeys.all }),
  });
}
