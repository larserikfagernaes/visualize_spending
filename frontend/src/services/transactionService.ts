import { Transaction, PaginatedResponse, FilterState, TransactionSummary, Supplier } from '../types/models';
import { get, post, put, del } from './api';

const BASE_URL = '/transactions';

/**
 * Fetch paginated transactions with optional filters
 * @param page Page number to fetch
 * @param filters Optional filter criteria
 * @returns Promise with paginated transaction data
 */
export const getTransactions = async (
  page = 1,
  filters?: FilterState
): Promise<PaginatedResponse<Transaction>> => {
  const params: Record<string, any> = { page };
  
  if (filters) {
    // Add filters to params
    if (filters.searchTerm) params.search = filters.searchTerm;
    if (filters.categoryFilter) params.category = filters.categoryFilter;
    if (filters.bankAccountFilter) params.bank_account = filters.bankAccountFilter;
    if (filters.startDate) params.start_date = filters.startDate;
    if (filters.endDate) params.end_date = filters.endDate;
    if (filters.amountMin) params.min_amount = filters.amountMin;
    if (filters.amountMax) params.max_amount = filters.amountMax;
    if (filters.hideInternalTransfers) params.hide_internal = filters.hideInternalTransfers;
    if (filters.hideWageTransfers) params.hide_wage = filters.hideWageTransfers;
    if (filters.hideTaxTransfers) params.hide_tax = filters.hideTaxTransfers;
    if (filters.showOnlyProcessable) params.processable_only = filters.showOnlyProcessable;
    if (filters.accountIdFilter) params.account_id = filters.accountIdFilter;
  }
  
  const response = await get<PaginatedResponse<Transaction>>(BASE_URL, params);
  return response.data;
};

/**
 * Fetch all transactions (use with caution for large datasets)
 * @param filters Optional filter criteria
 * @returns Promise with all transactions
 */
export const getAllTransactions = async (
  filters?: FilterState
): Promise<Transaction[]> => {
  const params: Record<string, any> = { page_size: 1000 };
  
  if (filters) {
    // Add filters to params
    if (filters.searchTerm) params.search = filters.searchTerm;
    if (filters.categoryFilter) params.category = filters.categoryFilter;
    if (filters.bankAccountFilter) params.bank_account = filters.bankAccountFilter;
    if (filters.startDate) params.start_date = filters.startDate;
    if (filters.endDate) params.end_date = filters.endDate;
    if (filters.amountMin) params.min_amount = filters.amountMin;
    if (filters.amountMax) params.max_amount = filters.amountMax;
    if (filters.hideInternalTransfers) params.hide_internal = filters.hideInternalTransfers;
    if (filters.hideWageTransfers) params.hide_wage = filters.hideWageTransfers;
    if (filters.hideTaxTransfers) params.hide_tax = filters.hideTaxTransfers;
    if (filters.showOnlyProcessable) params.processable_only = filters.showOnlyProcessable;
    if (filters.accountIdFilter) params.account_id = filters.accountIdFilter;
  }
  
  const response = await get<PaginatedResponse<Transaction>>(BASE_URL, params);
  return response.data.results;
};

/**
 * Get transaction by ID
 * @param id Transaction ID
 * @returns Promise with transaction data
 */
export const getTransactionById = async (id: number): Promise<Transaction> => {
  const response = await get<Transaction>(`${BASE_URL}/${id}`);
  return response.data;
};

/**
 * Get transaction with raw data
 * @param id Transaction ID
 * @returns Promise with transaction including raw data
 */
export const getTransactionWithRawData = async (id: number): Promise<Transaction> => {
  const response = await get<Transaction>(`${BASE_URL}/${id}/detail_with_raw_data`);
  return response.data;
};

/**
 * Update transaction
 * @param id Transaction ID
 * @param data Updated transaction data
 * @returns Promise with updated transaction
 */
export const updateTransaction = async (
  id: number,
  data: Partial<Transaction>
): Promise<Transaction> => {
  const response = await put<Transaction>(`${BASE_URL}/${id}`, data);
  return response.data;
};

/**
 * Get transaction summary
 * @param filters Optional filter criteria
 * @returns Promise with transaction summary data
 */
export const getTransactionSummary = async (
  filters?: FilterState
): Promise<TransactionSummary> => {
  const params: Record<string, any> = {};
  
  if (filters) {
    // Add filters to params
    if (filters.searchTerm) params.search = filters.searchTerm;
    if (filters.categoryFilter) params.category = filters.categoryFilter;
    if (filters.bankAccountFilter) params.bank_account = filters.bankAccountFilter;
    if (filters.startDate) params.start_date = filters.startDate;
    if (filters.endDate) params.end_date = filters.endDate;
    if (filters.amountMin) params.min_amount = filters.amountMin;
    if (filters.amountMax) params.max_amount = filters.amountMax;
    if (filters.hideInternalTransfers) params.hide_internal = filters.hideInternalTransfers;
    if (filters.hideWageTransfers) params.hide_wage = filters.hideWageTransfers;
    if (filters.hideTaxTransfers) params.hide_tax = filters.hideTaxTransfers;
    if (filters.showOnlyProcessable) params.processable_only = filters.showOnlyProcessable;
    if (filters.accountIdFilter) params.account_id = filters.accountIdFilter;
  }
  
  const response = await get<TransactionSummary>(`${BASE_URL}/summary`, params);
  return response.data;
};

/**
 * Fetch all suppliers
 * @returns Promise with all suppliers
 */
export const getSuppliers = async (): Promise<Supplier[]> => {
  const response = await get<{ results: Supplier[] }>('/suppliers');
  return response.data.results;
}; 