// frontend/src/types/tenant.ts
export interface Tenant {
  id: string;
  name: string;
  slug: string;
  trial_ends_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TenantListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Tenant[];
}

export type MembershipRole = 'OWNER' | 'ADMIN' | 'MEMBER';

export interface TenantMembership {
  id: string;
  tenant: string;
  user: string;
  user_email: string;
  role: MembershipRole;
  joined_at: string;
}

export interface TenantMembershipListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: TenantMembership[];
}

export type MembershipAction = 'create' | 'update' | 'delete';

export interface CreateMembershipInput {
  user_email: string;
  role: MembershipRole;
}

export interface UpdateMembershipInput {
  id: string;
  role: MembershipRole;
}
