import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BankAccount } from '../types/models';
import { bankAccountService } from '../services';

/**
 * Hook for fetching all bank accounts
 * @returns Query result for all bank accounts
 */
export const useBankAccounts = () => {
  return useQuery({
    queryKey: ['bankAccounts'],
    queryFn: () => bankAccountService.getAllBankAccounts(),
  });
};

/**
 * Hook for fetching a single bank account by ID
 * @param id Bank account ID
 * @returns Query result for a single bank account
 */
export const useBankAccount = (id?: number) => {
  return useQuery({
    queryKey: ['bankAccount', id],
    queryFn: () => bankAccountService.getBankAccountById(id!),
    enabled: !!id, // Only run if id is provided
  });
};

/**
 * Hook for creating a new bank account
 * @returns Mutation object for creating bank accounts
 */
export const useCreateBankAccount = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Omit<BankAccount, 'id' | 'created_at' | 'updated_at'>) => 
      bankAccountService.createBankAccount(data),
    onSuccess: () => {
      // Invalidate bank accounts query to refetch
      queryClient.invalidateQueries({ queryKey: ['bankAccounts'] });
    },
  });
};

/**
 * Hook for updating a bank account
 * @returns Mutation object for updating bank accounts
 */
export const useUpdateBankAccount = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<BankAccount> }) => 
      bankAccountService.updateBankAccount(id, data),
    onSuccess: (updatedBankAccount) => {
      // Invalidate bank accounts queries to refetch
      queryClient.invalidateQueries({ queryKey: ['bankAccounts'] });
      queryClient.invalidateQueries({ queryKey: ['bankAccount', updatedBankAccount.id] });
    },
  });
};

/**
 * Hook for deleting a bank account
 * @returns Mutation object for deleting bank accounts
 */
export const useDeleteBankAccount = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => bankAccountService.deleteBankAccount(id),
    onSuccess: (_, deletedId) => {
      // Invalidate bank accounts queries to refetch
      queryClient.invalidateQueries({ queryKey: ['bankAccounts'] });
      queryClient.invalidateQueries({ queryKey: ['bankAccount', deletedId] });
    },
  });
}; 