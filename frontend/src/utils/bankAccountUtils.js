/**
 * Utility functions for bank account-related operations
 */

/**
 * Get a bank account name from its ID
 * @param {string|number} bankAccountId - The bank account ID
 * @param {Array} bankAccounts - Array of bank account objects with id and name properties
 * @returns {string} The bank account name or a default string if not found
 */
export const getBankAccountName = (bankAccountId, bankAccounts) => {
  if (!bankAccountId) return 'Unknown';
  
  // Special handling for string IDs that are not numeric
  const isSpecialId = typeof bankAccountId === 'string' && isNaN(parseInt(bankAccountId));
  if (isSpecialId) {
    return bankAccountId;
  }
  
  if (!bankAccounts || !Array.isArray(bankAccounts) || bankAccounts.length === 0) {
    // Just return the ID as is instead of creating "Bank Account X" names
    return bankAccountId.toString();
  }
  
  const bankAccount = bankAccounts.find(account => 
    account.id === bankAccountId || account.id === parseInt(bankAccountId)
  );
  
  // If we found the account, use its name, otherwise use the ID directly
  return bankAccount && bankAccount.name 
    ? bankAccount.name 
    : (isSpecialId ? bankAccountId : bankAccountId.toString());
};

/**
 * Create a mapping of bank account IDs to their names
 * @param {Array} transactions - Array of transaction objects
 * @param {Array} bankAccounts - Array of bank account objects with id and name properties
 * @returns {Object} Mapping of bank account IDs to their names
 */
export const createBankAccountNameMap = (transactions, bankAccounts) => {
  const mapping = {};
  
  // Extract unique bank account IDs from transactions
  if (transactions && transactions.length > 0) {
    const uniqueIds = new Set();
    
    transactions.forEach(transaction => {
      if (transaction.bank_account_id) {
        uniqueIds.add(transaction.bank_account_id);
      }
    });
    
    // Create mapping for all transaction bank account IDs
    uniqueIds.forEach(id => {
      mapping[id] = getBankAccountName(id, bankAccounts);
    });
  }
  
  // Add all bank accounts from the bankAccounts array if available
  if (bankAccounts && bankAccounts.length > 0) {
    bankAccounts.forEach(account => {
      if (account.id) {
        // Use the name from the bank account or fall back to getBankAccountName
        mapping[account.id] = account.name || getBankAccountName(account.id, bankAccounts);
      }
    });
  }
  
  return mapping;
};

/**
 * Create a mapping of bank account IDs to their names from summary data
 * @param {Object} summaryData - Summary data object with bank_accounts property
 * @param {Array} bankAccounts - Array of bank account objects with id and name properties
 * @returns {Object} Mapping of bank account IDs to their names
 */
export const createBankAccountNameMapFromSummary = (summaryData, bankAccounts) => {
  const mapping = {};
  
  // First get any bank account IDs from the summary data
  if (summaryData?.bank_accounts) {
    Object.keys(summaryData.bank_accounts).forEach((id) => {
      // Use getBankAccountName to handle special IDs correctly
      mapping[id] = getBankAccountName(id, bankAccounts);
    });
  }
  
  // Then ensure all bank accounts from the array are included
  if (bankAccounts && bankAccounts.length > 0) {
    bankAccounts.forEach(account => {
      if (account.id) {
        // Use the name from the bank account or fall back to getBankAccountName
        mapping[account.id] = account.name || getBankAccountName(account.id, bankAccounts);
      }
    });
  }
  
  return mapping;
}; 