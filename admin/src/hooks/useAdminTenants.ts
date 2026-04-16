// admin/src/hooks/useAdminTenants.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AdminTenant, AdminTenantCreate, AdminTenantUpdate, PaginatedResponse } from '@/types/admin';

export const adminTenantKeys = {
  all: ['admin', 'tenants'] as const,
  list: (params?: { search?: string; status?: string }) => [...adminTenantKeys.all, 'list', params] as const,
  detail: (id: string) => [...adminTenantKeys.all, 'detail', id] as const,
};

export function useAdminTenants(params?: { search?: string; status?: string }) {
  const query = params?.search ? `?search=${encodeURIComponent(params.search)}` : '';
  const statusQ = params?.status ? `${query ? '&' : '?'}status=${encodeURIComponent(params.status)}` : '';
  return useQuery({
    queryKey: adminTenantKeys.list(params),
    queryFn: () => api.get<PaginatedResponse<AdminTenant>>(`/tenants/${query}${statusQ}`),
  });
}

export function useCreateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AdminTenantCreate) => api.post<AdminTenant>('/tenants/', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminTenantKeys.all }),
  });
}

export function useUpdateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AdminTenantUpdate }) =>
      api.put<AdminTenant>(`/tenants/${id}/`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminTenantKeys.all }),
  });
}

export function useExtendTrial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, days }: { id: string; days: number }) =>
      api.post<{ id: string; trial_ends_at: string }>(`/tenants/${id}/extend_trial/`, { days }),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminTenantKeys.all }),
  });
}
