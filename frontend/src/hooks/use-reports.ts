// frontend/src/hooks/use-reports.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { BalanceSheetResponse, CashFlowResponse, IncomeStatementResponse } from '@/types/report';

export function useBalanceSheet(asOf: string) {
  return useQuery({
    queryKey: ['reports', 'balance-sheet', asOf],
    queryFn: () => api.get<BalanceSheetResponse>(`/reports/balance-sheet?as_of=${asOf}`),
    enabled: !!asOf,
  });
}

export function useIncomeStatement(start: string, end: string) {
  return useQuery({
    queryKey: ['reports', 'income-statement', start, end],
    queryFn: () => api.get<IncomeStatementResponse>(`/reports/income-statement?start_date=${start}&end_date=${end}`),
    enabled: !!start && !!end,
  });
}

export function useCashFlow(start: string, end: string) {
  return useQuery({
    queryKey: ['reports', 'cash-flow', start, end],
    queryFn: () => api.get<CashFlowResponse>(`/reports/cash-flow?start_date=${start}&end_date=${end}`),
    enabled: !!start && !!end,
  });
}
