import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Category } from '../types/models';
import { categoryService } from '../services';

/**
 * Hook for fetching all categories
 * @returns Query result for all categories
 */
export const useCategories = () => {
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => categoryService.getAllCategories(),
  });
};

/**
 * Hook for fetching a single category by ID
 * @param id Category ID
 * @returns Query result for a single category
 */
export const useCategory = (id?: number) => {
  return useQuery({
    queryKey: ['category', id],
    queryFn: () => categoryService.getCategoryById(id!),
    enabled: !!id, // Only run if id is provided
  });
};

/**
 * Hook for creating a new category
 * @returns Mutation object for creating categories
 */
export const useCreateCategory = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Omit<Category, 'id' | 'created_at' | 'updated_at'>) => 
      categoryService.createCategory(data),
    onSuccess: () => {
      // Invalidate categories query to refetch
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
  });
};

/**
 * Hook for updating a category
 * @returns Mutation object for updating categories
 */
export const useUpdateCategory = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Category> }) => 
      categoryService.updateCategory(id, data),
    onSuccess: (updatedCategory) => {
      // Invalidate categories queries to refetch
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['category', updatedCategory.id] });
    },
  });
};

/**
 * Hook for deleting a category
 * @returns Mutation object for deleting categories
 */
export const useDeleteCategory = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => categoryService.deleteCategory(id),
    onSuccess: (_, deletedId) => {
      // Invalidate categories queries to refetch
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['category', deletedId] });
    },
  });
}; 