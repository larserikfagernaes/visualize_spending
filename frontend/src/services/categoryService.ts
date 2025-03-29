import { Category } from '../types/models';
import { get, post, put, del } from './api';

const BASE_URL = '/categories';

/**
 * Fetch all categories
 * @returns Promise with all categories
 */
export const getAllCategories = async (): Promise<Category[]> => {
  const response = await get<Category[]>(BASE_URL);
  return response.data;
};

/**
 * Get category by ID
 * @param id Category ID
 * @returns Promise with category data
 */
export const getCategoryById = async (id: number): Promise<Category> => {
  const response = await get<Category>(`${BASE_URL}/${id}`);
  return response.data;
};

/**
 * Create a new category
 * @param data Category data
 * @returns Promise with created category
 */
export const createCategory = async (data: Omit<Category, 'id' | 'created_at' | 'updated_at'>): Promise<Category> => {
  const response = await post<Category>(BASE_URL, data);
  return response.data;
};

/**
 * Update category
 * @param id Category ID
 * @param data Updated category data
 * @returns Promise with updated category
 */
export const updateCategory = async (
  id: number,
  data: Partial<Category>
): Promise<Category> => {
  const response = await put<Category>(`${BASE_URL}/${id}`, data);
  return response.data;
};

/**
 * Delete category
 * @param id Category ID
 * @returns Promise with delete status
 */
export const deleteCategory = async (id: number): Promise<void> => {
  await del<void>(`${BASE_URL}/${id}`);
}; 