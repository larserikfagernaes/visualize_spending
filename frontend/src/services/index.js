// Import named groups for organized imports
import * as api from './api';
import * as transactionService from './transactionService';
import * as categoryService from './categoryService';
import * as bankAccountService from './bankAccountService';

// Re-export all services for easier imports
export * from './api';
export * from './transactionService';
export * from './categoryService';
export * from './bankAccountService';

export {
  api,
  transactionService,
  categoryService,
  bankAccountService
}; 