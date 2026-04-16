export type ReconcileState = 'n' | 'c' | 'y' | 'f' | 'v';

export interface RegisterEntry {
  id: string;
  post_date: string;
  description: string;
  num: string;
  split_value: string;
  split_memo: string;
  other_accounts: string[];
  reconcile_state: ReconcileState;
  created_at: string;
}

export interface RegisterResponse {
  account: {
    id: string;
    name: string;
    full_name: string;
    account_type: string;
    commodity: string;
  };
  transactions: RegisterEntry[];
  running_balance: string;
}
