export interface BalanceSheetResponse {
  assets: string;
  liabilities: string;
  equity: string;
  retained_earnings: string;
  balanced: boolean;
}

export interface IncomeStatementResponse {
  revenue: string;
  expenses: string;
  net_income: string;
}

export interface CashFlowResponse {
  money_in: string;
  money_out: string;
  net_cash_flow: string;
}

export interface NetWorthResponse {
  assets: string;
  liabilities: string;
  net_worth: string;
}
