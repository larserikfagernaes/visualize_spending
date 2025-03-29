import { Category } from '../types/models';
import { get, post, put, del } from './api';

const BASE_URL = '/categories';

/**
 * Fetch all categories
 * @returns Promise with all categories
 */
export const getAllCategories = async () => {
  const response = await get(BASE_URL);
  return response.data;
};

/**
 * Get category by ID
 * @param id Category ID
 * @returns Promise with category data
 */
export const getCategoryById = async (id) => {
  const response = await get(`${BASE_URL}/${id}`);
  return response.data;
};

/**
 * Create a new category
 * @param data Category data
 * @returns Promise with created category
 */
export const createCategory = async (data) => {
  const response = await post(BASE_URL, data);
  return response.data;
};

/**
 * Update category
 * @param id Category ID
 * @param data Updated category data
 * @returns Promise with updated category
 */
export const updateCategory = async (id, data) => {
  const response = await put(`${BASE_URL}/${id}`, data);
  return response.data;
};

/**
 * Delete category
 * @param id Category ID
 * @returns Promise with delete status
 */
export const deleteCategory = async (id) => {
  await del(`${BASE_URL}/${id}`);
}; 