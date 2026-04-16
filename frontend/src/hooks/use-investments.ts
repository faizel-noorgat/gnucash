// frontend/src/hooks/use-investments.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  InvestmentAccount,
  InvestmentAccountListResponse,
  InvestmentLot,
  InvestmentLotListResponse,
  Price,
  PriceListResponse,
} from '@/types/investment';

export const investmentAccountKeys = {
  all: ['investment-accounts'] as const,
  list: () => [...investmentAccountKeys.all, 'list'] as const,
  detail: (id: string) => [...investmentAccountKeys.all, 'detail', id] as const,
  lots: (accountId: string) => [...investmentAccountKeys.all, 'lots', accountId] as const,
};

export const investmentLotKeys = {
  all: ['investment-lots'] as const,
  list: () => [...investmentLotKeys.all, 'list'] as const,
};

export const priceKeys = {
  all: ['prices'] as const,
  list: (params?: { commodity?: string }) => [...priceKeys.all, 'list', params] as const,
};

export function useInvestmentAccounts() {
  return useQuery({
    queryKey: investmentAccountKeys.list(),
    queryFn: () => api.get<InvestmentAccountListResponse>('/investments/'),
  });
}

export function useInvestmentAccount(id: string) {
  return useQuery({
    queryKey: investmentAccountKeys.detail(id),
    queryFn: () => api.get<InvestmentAccount>(`/investments/${id}/`),
    enabled: !!id,
  });
}

export function useInvestmentLots(accountId?: string) {
  const url = accountId ? `/investment-lots/?account=${accountId}` : '/investment-lots/';
  return useQuery({
    queryKey: accountId ? investmentAccountKeys.lots(accountId) : investmentLotKeys.list(),
    queryFn: () => api.get<InvestmentLotListResponse>(url),
    enabled: accountId !== undefined,
  });
}

export function usePrices(params?: { commodity?: string }) {
  const qs = params?.commodity ? `?commodity=${params.commodity}` : '';
  return useQuery({
    queryKey: priceKeys.list(params),
    queryFn: () => api.get<PriceListResponse>(`/prices/${qs}`),
  });
}

export function useCreateInvestmentAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<InvestmentAccount>) =>
      api.post<InvestmentAccount>('/investments/', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: investmentAccountKeys.all }),
  });
}

export function useCreateInvestmentLot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<InvestmentLot>) =>
      api.post<InvestmentLot>('/investment-lots/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: investmentLotKeys.all });
      qc.invalidateQueries({ queryKey: investmentAccountKeys.all });
    },
  });
}
