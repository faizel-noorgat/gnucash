export interface Split {
  id: string;
  account: string;
  memo: string;
  action: string;
  reconcile_state: string;
  reconcile_date: string | null;
  value: string;
  quantity: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  guid: string;
  currency: string;
  num: string;
  post_date: string;
  enter_date: string;
  description: string;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  splits: Split[];
}

export interface TransactionListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Transaction[];
}

export interface SplitCreateData {
  account: string;
  value: string;
  quantity?: string;
  memo?: string;
}
