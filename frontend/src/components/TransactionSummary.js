import React from 'react';
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

const TransactionSummary = ({ data }) => {
  if (!data) return null;

  const { total_transactions, total_amount, categories = {}, bank_accounts = {} } = data;

  // Ensure categories is an object
  const categoriesObj = categories && typeof categories === 'object' ? categories : {};

  // Ensure bank_accounts is an object
  const bankAccountsObj = bank_accounts && typeof bank_accounts === 'object' ? bank_accounts : {};

  // Sort categories by total amount
  const sortedCategories = Object.entries(categoriesObj)
    .sort((a, b) => Math.abs(b[1].total) - Math.abs(a[1].total));

  // Sort bank accounts by total amount
  const sortedBankAccounts = Object.entries(bankAccountsObj)
    .sort((a, b) => Math.abs(b[1].total) - Math.abs(a[1].total));

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Transaction Summary
        </Typography>
        
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
              label={new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
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
                      label={new Intl.NumberFormat('en-US', {
                        style: 'currency',
                        currency: 'USD'
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
                sortedBankAccounts.map(([account, data]) => (
                  <ListItem key={account} disableGutters>
                    <ListItemText
                      primary={account}
                      secondary={`${data.count} transactions`}
                    />
                    <Chip
                      label={new Intl.NumberFormat('en-US', {
                        style: 'currency',
                        currency: 'USD'
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