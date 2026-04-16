// frontend/src/hooks/use-audit.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AuditLogListResponse } from '@/types/audit';

export const auditKeys = {
  all: ['audit-log'] as const,
  list: (params?: { action?: string; date_from?: string; date_to?: string; user?: string }) =>
    [...auditKeys.all, 'list', params] as const,
};

export function useAuditLog(params?: {
  action?: string;
  date_from?: string;
  date_to?: string;
  user?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.action) searchParams.set('search', params.action);
  if (params?.date_from) searchParams.set('date_from', params.date_from);
  if (params?.date_to) searchParams.set('date_to', params.date_to);
  if (params?.user) searchParams.set('user', params.user);

  const qs = searchParams.toString();
  return useQuery({
    queryKey: auditKeys.list(params),
    queryFn: () => api.get<AuditLogListResponse>(`/audit-log/${qs ? `?${qs}` : ''}`),
  });
}
