// admin/src/types/admin.ts

export interface AdminTenant {
  id: string;
  name: string;
  slug: string;
  trial_ends_at: string | null;
  stripe_customer_id: string;
  created_at: string;
  updated_at: string;
  member_count: number;
  owner_email: string | null;
}

export interface AdminTenantCreate {
  name: string;
  slug: string;
  trial_ends_at?: string;
}

export interface AdminTenantUpdate {
  name?: string;
  slug?: string;
  trial_ends_at?: string;
  stripe_customer_id?: string;
}

export interface AdminUser {
  id: string;
  email: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  created_at: string;
  last_login_at: string | null;
  tenant_count: number;
  tenant_names: string[];
}

export interface AdminAuditLog {
  id: string;
  tenant: string;
  tenant_name: string;
  user: string | null;
  user_email: string | null;
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'LOGIN' | 'LOGOUT' | 'EXPORT';
  model: string;
  object_id: string;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string;
  timestamp: string;
}

export interface DashboardStats {
  total_tenants: number;
  total_users: number;
  total_audit_events: number;
  active_tenants_30d: number;
  recent_signups: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
