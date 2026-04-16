// frontend/src/hooks/use-budgets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Budget, BudgetListResponse } from '@/types/budget';

export const budgetKeys = {
  all: ['budgets'] as const,
  list: () => [...budgetKeys.all, 'list'] as const,
  detail: (id: string) => [...budgetKeys.all, 'detail', id] as const,
};

export function useBudgets() {
  return useQuery({
    queryKey: budgetKeys.list(),
    queryFn: () => api.get<BudgetListResponse>('/budgets/'),
  });
}

export function useBudget(id: string) {
  return useQuery({
    queryKey: budgetKeys.detail(id),
    queryFn: () => api.get<Budget>(`/budgets/${id}`),
    enabled: !!id,
  });
}

export function useDeleteBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/budgets/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: budgetKeys.all }),
  });
}
