// frontend/src/types/audit.ts
export type AuditAction = 'CREATE' | 'UPDATE' | 'DELETE' | 'LOGIN' | 'LOGOUT' | 'EXPORT';

export interface AuditLog {
  id: string;
  tenant: string;
  user: string | null;
  user_email: string | null;
  action: AuditAction;
  model: string;
  object_id: string;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string;
  timestamp: string;
}

export interface AuditLogListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditLog[];
}
