// frontend/src/hooks/use-users.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  TenantMembership,
  TenantMembershipListResponse,
  CreateMembershipInput,
  UpdateMembershipInput,
} from '@/types/tenant';

export const membershipKeys = {
  all: ['memberships'] as const,
  list: () => [...membershipKeys.all, 'list'] as const,
  detail: (id: string) => [...membershipKeys.all, 'detail', id] as const,
};

export function useTenantMemberships() {
  return useQuery({
    queryKey: membershipKeys.list(),
    queryFn: () => api.get<TenantMembershipListResponse>('/tenant-memberships/'),
  });
}

export function useCreateMembership() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateMembershipInput) =>
      api.post<TenantMembership>('/tenant-memberships/', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: membershipKeys.all }),
  });
}

export function useUpdateMembership() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role }: UpdateMembershipInput) =>
      api.patch<TenantMembership>(`/tenant-memberships/${id}/`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: membershipKeys.all }),
  });
}

export function useDeleteMembership() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<void>(`/tenant-memberships/${id}/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: membershipKeys.all }),
  });
}
