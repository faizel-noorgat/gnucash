export type RecurringFrequency = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'YEARLY';

export interface RecurringTransaction {
  id: string;
  tenant: string;
  name: string;
  template: Record<string, unknown>;
  frequency: RecurringFrequency;
  start_date: string;
  end_date: string | null;
  last_run: string | null;
  next_run: string;
  enabled: boolean;
  advance_notice_days: number;
  auto_create: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecurringTransactionListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: RecurringTransaction[];
}

export interface RecurringTransactionCreateData {
  name: string;
  template: Record<string, unknown>;
  frequency: RecurringFrequency;
  start_date: string;
  end_date?: string | null;
  next_run: string;
  advance_notice_days?: number;
  auto_create?: boolean;
}

export interface RecurringTransactionUpdateData {
  name?: string;
  template?: Record<string, unknown>;
  frequency?: RecurringFrequency;
  start_date?: string;
  end_date?: string | null;
  next_run?: string;
  enabled?: boolean;
  advance_notice_days?: number;
  auto_create?: boolean;
}
