// frontend/src/hooks/use-accounts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Account, AccountListResponse } from '@/types/account';

export const accountKeys = {
  all: ['accounts'] as const,
  list: (params?: { search?: string }) => [...accountKeys.all, 'list', params] as const,
  detail: (id: string) => [...accountKeys.all, 'detail', id] as const,
};

export function useAccounts(params?: { search?: string }) {
  return useQuery({
    queryKey: accountKeys.list(params),
    queryFn: () => api.get<AccountListResponse>(`/accounts${params?.search ? `?search=${params.search}` : ''}`),
  });
}

export function useAccount(id: string) {
  return useQuery({
    queryKey: accountKeys.detail(id),
    queryFn: () => api.get<Account>(`/accounts/${id}`),
    enabled: !!id,
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Account>) => api.post<Account>('/accounts', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: accountKeys.all }),
  });
}
