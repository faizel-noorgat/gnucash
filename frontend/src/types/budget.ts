export interface Budget {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  style: 'TRADITIONAL' | 'ENVELOPE';
  rollover: boolean;
  created_at: string;
  updated_at: string;
  categories: BudgetCategory[];
}

export interface BudgetCategory {
  id: string;
  budget: string;
  account: string;
  account_name: string;
  amount: string;
  notes: string;
}

export interface BudgetListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Budget[];
}
