import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Transaction, FilterState, PaginatedResponse } from '../types/models';
import { transactionService } from '../services';

/**
 * Hook for fetching paginated transactions
 * @param page Current page number
 * @param filters Optional filtering criteria
 * @returns Query result for paginated transactions
 */
export const useTransactions = (page = 1, filters) => {
  const queryClient = useQueryClient();
  
  return useQuery({
    queryKey: ['transactions', page, filters],
    queryFn: () => transactionService.getTransactions(page, filters),
    // Use placeholderData to show previous data while fetching new data
    placeholderData: (prev) => prev,
  });
};

/**
 * Hook for fetching all transactions (use with caution)
 * @param filters Optional filtering criteria
 * @returns Query result for all transactions
 */
export const useAllTransactions = (filters) => {
  return useQuery({
    queryKey: ['allTransactions', filters],
    queryFn: () => transactionService.getAllTransactions(filters),
  });
};

/**
 * Hook for fetching transaction summary
 * @param filters Optional filtering criteria
 * @returns Query result for transaction summary
 */
export const useTransactionSummary = (filters) => {
  return useQuery({
    queryKey: ['transactionSummary', filters],
    queryFn: () => transactionService.getTransactionSummary(filters),
  });
};

/**
 * Hook for fetching a single transaction by ID
 * @param id Transaction ID
 * @returns Query result for single transaction
 */
export const useTransaction = (id) => {
  return useQuery({
    queryKey: ['transaction', id],
    queryFn: () => transactionService.getTransactionById(id),
    enabled: !!id, // Only run query if id is provided
  });
};

/**
 * Hook for fetching a transaction with raw data
 * @param id Transaction ID
 * @returns Query result for transaction with raw data
 */
export const useTransactionWithRawData = (id) => {
  return useQuery({
    queryKey: ['transactionWithRawData', id],
    queryFn: () => transactionService.getTransactionWithRawData(id),
    enabled: !!id, // Only run query if id is provided
  });
};

/**
 * Hook for updating a transaction
 * @returns Mutation object for updating transactions
 */
export const useUpdateTransaction = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => 
      transactionService.updateTransaction(id, data),
    onSuccess: (updatedTransaction) => {
      // Invalidate and refetch transactions queries
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['allTransactions'] });
      queryClient.invalidateQueries({ queryKey: ['transaction', updatedTransaction.id] });
      queryClient.invalidateQueries({ queryKey: ['transactionWithRawData', updatedTransaction.id] });
      queryClient.invalidateQueries({ queryKey: ['transactionSummary'] });
    },
  });
}; 