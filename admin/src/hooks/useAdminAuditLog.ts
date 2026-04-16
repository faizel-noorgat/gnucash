// admin/src/hooks/useAdminAuditLog.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AdminAuditLog, PaginatedResponse } from '@/types/admin';

export const adminAuditLogKeys = {
  all: ['admin', 'audit-log'] as const,
  list: (params?: AuditLogFilters) => [...adminAuditLogKeys.all, 'list', params] as const,
};

export interface AuditLogFilters {
  tenant_id?: string;
  action?: string;
  model?: string;
  date_from?: string;
  date_to?: string;
  user_email?: string;
}

export function useAdminAuditLog(filters?: AuditLogFilters) {
  const buildQuery = (): string => {
    if (!filters) return '';
    const parts: string[] = [];
    if (filters.tenant_id) parts.push(`tenant_id=${encodeURIComponent(filters.tenant_id)}`);
    if (filters.action) parts.push(`action=${encodeURIComponent(filters.action)}`);
    if (filters.model) parts.push(`model=${encodeURIComponent(filters.model)}`);
    if (filters.date_from) parts.push(`date_from=${encodeURIComponent(filters.date_from)}`);
    if (filters.date_to) parts.push(`date_to=${encodeURIComponent(filters.date_to)}`);
    if (filters.user_email) parts.push(`user_email=${encodeURIComponent(filters.user_email)}`);
    return parts.length ? `?${parts.join('&')}` : '';
  };

  return useQuery({
    queryKey: adminAuditLogKeys.list(filters),
    queryFn: () => api.get<PaginatedResponse<AdminAuditLog>>(`/audit-log/${buildQuery()}`),
  });
}
