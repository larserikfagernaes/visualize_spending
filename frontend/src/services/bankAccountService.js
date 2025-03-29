import { BankAccount } from '../types/models';
import { get, post, put, del } from './api';

const BASE_URL = '/bank-accounts';

/**
 * Fetch all bank accounts
 * @returns Promise with all bank accounts
 */
export const getAllBankAccounts = async () => {
  const response = await get(BASE_URL);
  return response.data;
};

/**
 * Get bank account by ID
 * @param id Bank account ID
 * @returns Promise with bank account data
 */
export const getBankAccountById = async (id) => {
  const response = await get(`${BASE_URL}/${id}`);
  return response.data;
};

/**
 * Create a new bank account
 * @param data Bank account data
 * @returns Promise with created bank account
 */
export const createBankAccount = async (data) => {
  const response = await post(BASE_URL, data);
  return response.data;
};

/**
 * Update bank account
 * @param id Bank account ID
 * @param data Updated bank account data
 * @returns Promise with updated bank account
 */
export const updateBankAccount = async (id, data) => {
  const response = await put(`${BASE_URL}/${id}`, data);
  return response.data;
};

/**
 * Delete bank account
 * @param id Bank account ID
 * @returns Promise with delete status
 */
export const deleteBankAccount = async (id) => {
  await del(`${BASE_URL}/${id}`);
}; 