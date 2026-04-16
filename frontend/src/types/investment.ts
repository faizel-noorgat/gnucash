// frontend/src/types/investment.ts
export interface InvestmentAccount {
  id: string;
  tenant: string;
  account: string;
  account_name: string;
  institution: string;
  account_number: string;
}

export interface InvestmentAccountListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: InvestmentAccount[];
}

export interface InvestmentLot {
  id: string;
  tenant: string;
  account: string;
  security_id: string;
  quantity: string;
  purchase_date: string;
  purchase_price: string;
  cost_basis: string;
  is_closed: boolean;
  created_at: string;
}

export interface InvestmentLotListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: InvestmentLot[];
}

export interface Price {
  id: string;
  commodity: string;
  commodity_mnemonic: string;
  currency: string;
  date: string;
  source: string;
  price_type: string;
  value: string;
}

export interface PriceListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Price[];
}
