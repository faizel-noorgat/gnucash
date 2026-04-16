export type AccountType =
  | 'ASSET' | 'LIABILITY' | 'EQUITY' | 'INCOME' | 'EXPENSE'
  | 'BANK' | 'CASH' | 'CREDIT' | 'STOCK' | 'MUTUAL' | 'RECEIVABLE' | 'PAYABLE' | 'TRADING';

export interface Account {
  id: string;
  name: string;
  full_name: string;
  code: string | null;
  description: string | null;
  account_type: string;
  commodity: string;
  commodity_scu: number;
  hidden: boolean;
  placeholder: boolean;
  color: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Account[];
}
