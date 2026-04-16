export type ReceiptStatus = 'PENDING' | 'PROCESSED' | 'MANUAL_REVIEW';

export interface Receipt {
  id: string;
  tenant: string;
  transaction: string | null;
  file_url: string;
  ocr_text: string;
  vendor: string;
  total_amount: string | null;
  receipt_date: string | null;
  status: ReceiptStatus;
  auto_category: string | null;
  auto_category_name: string | null;
  user_category: string | null;
  user_category_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReceiptListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Receipt[];
}

export interface ReceiptCreateData {
  file_url: string;
  vendor?: string;
  receipt_date?: string;
}

export interface ReceiptUpdateData {
  user_category?: string | null;
  transaction?: string | null;
  status?: ReceiptStatus;
}
