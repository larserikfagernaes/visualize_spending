import React from 'react';
import { Box, Typography, CircularProgress, Paper, List, ListItem, ListItemText, Alert } from '@mui/material';
import { useBankAccounts } from '../hooks/useBankAccounts';
import { useCategories } from '../hooks/useCategories';
import { useTransactions } from '../hooks/useTransactions';

/**
 * Component for testing API connections
 */
const ApiTest = () => {
  // Test bank accounts API
  const { 
    data: bankAccountsData, 
    isLoading: bankAccountsLoading, 
    error: bankAccountsError 
  } = useBankAccounts();

  // Test categories API
  const { 
    data: categoriesData, 
    isLoading: categoriesLoading, 
    error: categoriesError 
  } = useCategories();

  // Test transactions API
  const {
    data: transactionsData,
    isLoading: transactionsLoading,
    error: transactionsError
  } = useTransactions(1);

  // Determine overall status
  const isLoading = bankAccountsLoading || categoriesLoading || transactionsLoading;
  const hasError = bankAccountsError || categoriesError || transactionsError;
  const isSuccess = !isLoading && !hasError;

  // Format error message
  const formatError = (error) => {
    if (!error) return 'Unknown error';
    if (typeof error === 'string') return error;
    if (error.message) return error.message;
    if (error.status) return `Status: ${error.status} - ${error.message || 'Unknown error'}`;
    return JSON.stringify(error);
  };

  // Get the primary error message
  const getErrorMessage = () => {
    const error = bankAccountsError || categoriesError || transactionsError;
    return formatError(error);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        API Connection Test
      </Typography>

      {isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading data from API...</Typography>
        </Box>
      )}

      {hasError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error connecting to API: {getErrorMessage()}
        </Alert>
      )}

      {isSuccess && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Successfully connected to API!
        </Alert>
      )}

      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 2 }}>
        {/* Bank Accounts */}
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Bank Accounts
          </Typography>
          
          {bankAccountsLoading ? (
            <CircularProgress size={20} />
          ) : bankAccountsError ? (
            <Typography color="error">Error loading bank accounts: {formatError(bankAccountsError)}</Typography>
          ) : (
            <List dense>
              {bankAccountsData?.map(account => (
                <ListItem key={account.id}>
                  <ListItemText 
                    primary={account.name} 
                    secondary={account.account_number || 'No account number'} 
                  />
                </ListItem>
              ))}
              {bankAccountsData?.length === 0 && (
                <ListItem>
                  <ListItemText primary="No bank accounts found" />
                </ListItem>
              )}
            </List>
          )}
        </Paper>

        {/* Categories */}
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Categories
          </Typography>
          
          {categoriesLoading ? (
            <CircularProgress size={20} />
          ) : categoriesError ? (
            <Typography color="error">Error loading categories: {formatError(categoriesError)}</Typography>
          ) : (
            <List dense>
              {categoriesData?.map(category => (
                <ListItem key={category.id}>
                  <ListItemText 
                    primary={category.name} 
                    secondary={category.description || 'No description'} 
                  />
                </ListItem>
              ))}
              {categoriesData?.length === 0 && (
                <ListItem>
                  <ListItemText primary="No categories found" />
                </ListItem>
              )}
            </List>
          )}
        </Paper>

        {/* Transactions */}
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Transactions (First Page)
          </Typography>
          
          {transactionsLoading ? (
            <CircularProgress size={20} />
          ) : transactionsError ? (
            <Typography color="error">Error loading transactions: {formatError(transactionsError)}</Typography>
          ) : (
            <>
              <Typography variant="body2" gutterBottom>
                Total: {transactionsData?.count || 0} transactions
              </Typography>
              <List dense>
                {transactionsData?.results?.slice(0, 5).map(transaction => (
                  <ListItem key={transaction.id}>
                    <ListItemText 
                      primary={`${transaction.description.slice(0, 30)}${transaction.description.length > 30 ? '...' : ''}`} 
                      secondary={`${new Date(transaction.date).toLocaleDateString()} - ${transaction.amount.toLocaleString('nb-NO')} kr`}
                    />
                  </ListItem>
                ))}
                {transactionsData?.results?.length === 0 && (
                  <ListItem>
                    <ListItemText primary="No transactions found" />
                  </ListItem>
                )}
              </List>
            </>
          )}
        </Paper>
      </Box>
    </Box>
  );
};

export default ApiTest; 