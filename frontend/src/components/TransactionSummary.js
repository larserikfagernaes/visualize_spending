import React, { useMemo } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Divider,
  List,
  ListItem,
  ListItemText,
  Chip,
  Grid
} from '@mui/material';
import { createBankAccountNameMapFromSummary } from '../utils/bankAccountUtils';

const TransactionSummary = ({ data, activeFilters = {}, bankAccounts = [] }) => {
  // Create memoized mapping of bank account IDs to names
  const bankAccountNameMap = useMemo(() => 
    data ? createBankAccountNameMapFromSummary(data, bankAccounts) : {},
    [data, bankAccounts]
  );

  // Sort bank accounts by total amount and map IDs to names using our memoized mapping
  const sortedBankAccounts = useMemo(() => {
    if (!data) return [];
    
    const bankAccountsObj = data.bank_accounts && typeof data.bank_accounts === 'object' ? data.bank_accounts : {};
    
    return Object.entries(bankAccountsObj)
      .map(([id, data]) => ({
        id,
        name: bankAccountNameMap[id] || id,
        data
      }))
      .sort((a, b) => Math.abs(b.data.total) - Math.abs(a.data.total));
  }, [data, bankAccountNameMap]);

  if (!data) return null;

  // Debug bank accounts data (can be removed in production)
  console.log('TransactionSummary received bankAccounts:', bankAccounts.map(acc => ({ id: acc.id, name: acc.name })));

  const { total_transactions, total_amount, categories = {} } = data;

  // Ensure categories is an object
  const categoriesObj = categories && typeof categories === 'object' ? categories : {};

  // Sort categories by total amount
  const sortedCategories = Object.entries(categoriesObj)
    .sort((a, b) => Math.abs(b[1].total) - Math.abs(a[1].total));

  // Check if any filters are active
  const hasActiveFilters = Object.entries(activeFilters)
    .some(([key, value]) => {
      if (['amountMin', 'amountMax'].includes(key)) {
        return value !== '';
      }
      if (['startDate', 'endDate'].includes(key)) {
        return value !== null;
      }
      return value;
    });

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Typography variant="h6">
            Transaction Summary
          </Typography>
          
          {/* Active filters display */}
          {hasActiveFilters && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {activeFilters.hideInternalTransfers && (
                <Chip size="small" label="No Internal Transfers" color="primary" variant="outlined" />
              )}
              {activeFilters.hideWageTransfers && (
                <Chip size="small" label="No Wage Transfers" color="primary" variant="outlined" />
              )}
              {activeFilters.hideTaxTransfers && (
                <Chip size="small" label="No Tax Transfers" color="primary" variant="outlined" />
              )}
              {activeFilters.showOnlyProcessable && (
                <Chip size="small" label="Only Processable" color="primary" variant="outlined" />
              )}
              {activeFilters.amountMin !== '' && (
                <Chip size="small" label={`Min Amount: ${activeFilters.amountMin}`} color="primary" variant="outlined" />
              )}
              {activeFilters.amountMax !== '' && (
                <Chip size="small" label={`Max Amount: ${activeFilters.amountMax}`} color="primary" variant="outlined" />
              )}
              {activeFilters.startDate && (
                <Chip size="small" label={`From: ${activeFilters.startDate}`} color="primary" variant="outlined" />
              )}
              {activeFilters.endDate && (
                <Chip size="small" label={`To: ${activeFilters.endDate}`} color="primary" variant="outlined" />
              )}
            </Box>
          )}
        </Box>
        
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Overview
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">Total Transactions:</Typography>
            <Typography variant="body2" fontWeight="bold">
              {total_transactions || 0}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2">Total Amount:</Typography>
            <Chip
              label={new Intl.NumberFormat('nb-NO', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
              }).format(total_amount || 0)}
              color={(total_amount || 0) < 0 ? "error" : "success"}
              size="small"
            />
          </Box>
        </Box>
        
        <Divider sx={{ my: 2 }} />
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle1" gutterBottom>
              Spending by Category
            </Typography>
            
            <List dense>
              {sortedCategories.length > 0 ? (
                sortedCategories.map(([category, data]) => (
                  <ListItem key={category} disableGutters>
                    <ListItemText
                      primary={category}
                      secondary={`${data.count} transactions`}
                    />
                    <Chip
                      label={new Intl.NumberFormat('nb-NO', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      }).format(data.total)}
                      color={data.total < 0 ? "error" : "success"}
                      size="small"
                    />
                  </ListItem>
                ))
              ) : (
                <ListItem disableGutters>
                  <ListItemText primary="No categories found" />
                </ListItem>
              )}
            </List>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle1" gutterBottom>
              Spending by Bank Account
            </Typography>
            
            <List dense>
              {sortedBankAccounts.length > 0 ? (
                sortedBankAccounts.map(({ id, name, data }) => (
                  <ListItem key={id} disableGutters>
                    <ListItemText
                      primary={name}
                      secondary={`${data.count} transactions`}
                    />
                    <Chip
                      label={new Intl.NumberFormat('nb-NO', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      }).format(data.total)}
                      color={data.total < 0 ? "error" : "success"}
                      size="small"
                    />
                  </ListItem>
                ))
              ) : (
                <ListItem disableGutters>
                  <ListItemText primary="No bank accounts found" />
                </ListItem>
              )}
            </List>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default TransactionSummary; 