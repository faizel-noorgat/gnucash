// admin/src/hooks/useAdminDashboard.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { DashboardStats } from '@/types/admin';

export const adminDashboardKeys = {
  all: ['admin', 'dashboard'] as const,
  stats: () => [...adminDashboardKeys.all, 'stats'] as const,
};

export function useDashboardStats() {
  return useQuery({
    queryKey: adminDashboardKeys.stats(),
    queryFn: () => api.get<DashboardStats>('/dashboard/stats/'),
    refetchInterval: 1000 * 60,
  });
}
