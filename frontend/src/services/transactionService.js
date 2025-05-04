import { get, post, put, del } from './api';

const BASE_URL = '/transactions';

/**
 * Fetch paginated transactions with optional filters
 * @param page Page number to fetch
 * @param filters Optional filter criteria
 * @returns Promise with paginated transaction data
 */
export const getTransactions = async (page = 1, filters) => {
  const params = { page };
  
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
  
  const response = await get(BASE_URL, params);
  return response.data;
};

/**
 * Fetch all transactions (use with caution for large datasets)
 * @param filters Optional filter criteria
 * @returns Promise with all transactions
 */
export const getAllTransactions = async (filters) => {
  const params = { page_size: 1000 };
  
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
  
  const response = await get(BASE_URL, params);
  return response.data.results;
};

/**
 * Get transaction by ID
 * @param id Transaction ID
 * @returns Promise with transaction data
 */
export const getTransactionById = async (id) => {
  const response = await get(`${BASE_URL}/${id}`);
  return response.data;
};

/**
 * Get transaction with raw data
 * @param id Transaction ID
 * @returns Promise with transaction including raw data
 */
export const getTransactionWithRawData = async (id) => {
  const response = await get(`${BASE_URL}/${id}/detail_with_raw_data`);
  return response.data;
};

/**
 * Update transaction
 * @param id Transaction ID
 * @param data Updated transaction data
 * @returns Promise with updated transaction
 */
export const updateTransaction = async (id, data) => {
  const response = await put(`${BASE_URL}/${id}`, data);
  return response.data;
};

/**
 * Get transaction summary
 * @param filters Optional filter criteria
 * @returns Promise with transaction summary data
 */
export const getTransactionSummary = async (filters) => {
  const params = {};
  
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
  
  const response = await get(`${BASE_URL}/summary`, params);
  return response.data;
};

/**
 * Fetch all suppliers
 * @returns Promise with all suppliers
 */
export const getSuppliers = async () => {
  const response = await get('/suppliers');
  return response.data.results;
}; 