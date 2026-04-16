// admin/src/hooks/useAdminUsers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AdminUser, PaginatedResponse } from '@/types/admin';

export const adminUserKeys = {
  all: ['admin', 'users'] as const,
  list: (params?: { search?: string; is_active?: boolean }) => [...adminUserKeys.all, 'list', params] as const,
};

export function useAdminUsers(params?: { search?: string; is_active?: boolean }) {
  const searchQ = params?.search ? `?search=${encodeURIComponent(params.search)}` : '';
  const activeQ = params?.is_active !== undefined ? `${searchQ ? '&' : '?'}is_active=${params.is_active}` : '';
  return useQuery({
    queryKey: adminUserKeys.list(params),
    queryFn: () => api.get<PaginatedResponse<AdminUser>>(`/users/${searchQ}${activeQ}`),
  });
}

export function useToggleUserActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.patch<{ id: string; is_active: boolean }>(`/users/${id}/toggle_active/`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminUserKeys.all }),
  });
}

export function useSetUserStaff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, is_staff }: { id: string; is_staff: boolean }) =>
      api.patch<{ id: string; is_staff: boolean }>(`/users/${id}/set_staff/`, { is_staff }),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminUserKeys.all }),
  });
}
