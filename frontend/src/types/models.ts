/**
 * TypeScript interfaces for the backend models
 */

export interface Category {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface BankAccount {
  id: number;
  name: string;
  account_number?: string;
  bank_name?: string;
  account_type?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: number;
  tripletex_id?: string;
  description: string;
  amount: number;
  date: string;
  bank_account?: number; // ForeignKey to BankAccount
  bank_account_name?: string; // Serialized field from BankAccount
  legacy_bank_account_id?: string; // Previously named bank_account_id
  account_id?: string;
  category?: number; // ForeignKey to Category
  category_name?: string; // Serialized field from Category
  is_internal_transfer: boolean;
  is_wage_transfer: boolean;
  is_tax_transfer: boolean;
  is_forbidden: boolean;
  should_process: boolean;
  raw_data?: any; // JSON field
  imported_at: string;
  created_at: string;
  updated_at: string;
}

export interface BankStatement {
  id: number;
  description: string;
  amount: number;
  date: string;
  source_file?: string;
  bank_account?: number; // ForeignKey to BankAccount
  category?: number; // ForeignKey to Category
  created_at: string;
  updated_at: string;
}

export interface TransactionSummary {
  categories?: {
    [key: string]: {
      total: number;
      count: number;
    };
  };
  bank_accounts?: {
    [key: string]: {
      total: number;
      count: number;
    };
  };
  by_category?: Array<{
    category: string;
    total: number;
    count: number;
  }>;
  total_amount?: number;
  transaction_count?: number;
  date_range?: {
    start_date: string;
    end_date: string;
  };
}

export interface FilterState {
  hideInternalTransfers: boolean;
  hideWageTransfers: boolean;
  hideTaxTransfers: boolean;
  showOnlyProcessable: boolean;
  amountMin: string;
  amountMax: string;
  startDate: string | null;
  endDate: string | null;
  categoryFilter: number | string;
  bankAccountFilter: string;
  accountIdFilter: string;
  searchTerm: string;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Supplier {
  id: number;
  tripletex_id: string;
  name?: string;
  organization_number?: string;
  email?: string;
  phone_number?: string;
  address?: string;
  url?: string;
  created_at: string;
  updated_at: string;
} 