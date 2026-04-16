import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { RegisterResponse } from '@/types/register';

export const registerKeys = {
  all: ['account-register'] as const,
  detail: (id: string, params?: { start_date?: string; end_date?: string }) =>
    [...registerKeys.all, id, params] as const,
};

export function useAccountRegister(
  accountId: string,
  filters?: { start_date?: string; end_date?: string },
) {
  const params = new URLSearchParams();
  if (filters?.start_date) params.set('start_date', filters.start_date);
  if (filters?.end_date) params.set('end_date', filters.end_date);
  const queryString = params.toString();

  return useQuery({
    queryKey: registerKeys.detail(accountId, filters),
    queryFn: () =>
      api.get<RegisterResponse>(
        `/accounts/${accountId}/register${queryString ? `?${queryString}` : ''}`,
      ),
    enabled: !!accountId,
  });
}
