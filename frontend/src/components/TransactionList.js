import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  MenuItem,
  IconButton,
  Box,
  Chip,
  CircularProgress,
  TablePagination,
  InputAdornment
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import SaveIcon from '@mui/icons-material/Save';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const TransactionList = ({ transactions = [], categories = [], onUpdate, loading, loadingProgress }) => {
  // State
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [bankAccountFilter, setBankAccountFilter] = useState('');
  const [accountIdFilter, setAccountIdFilter] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [editingTransaction, setEditingTransaction] = useState(null);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [accountIds, setAccountIds] = useState([]);

  // Ensure transactions and categories are always arrays
  const transactionData = Array.isArray(transactions) ? transactions : [];
  const categoriesList = Array.isArray(categories) ? categories : [];
  
  console.log('TransactionList received props:', { 
    transactionsCount: transactions?.length || 0,
    categoriesCount: categories?.length || 0,
    loading
  });

  // Extract unique bank accounts and account IDs from transactions
  useEffect(() => {
    if (Array.isArray(transactions) && transactions.length > 0) {
      // Extract bank accounts
      const accounts = transactions
        .map(transaction => transaction.bank_account_id)
        .filter((account, index, self) => 
          account && self.indexOf(account) === index
        )
        .sort();
      
      setBankAccounts(accounts);
      
      // Extract account IDs
      const ids = transactions
        .map(transaction => transaction.account_id)
        .filter((id, index, self) => 
          id && self.indexOf(id) === index
        )
        .sort();
      
      setAccountIds(ids);
      
      console.log(`Extracted ${accounts.length} bank accounts and ${ids.length} account IDs`);
    }
  }, [transactions]);

  // Filter transactions when transactions, searchTerm, categoryFilter, or bankAccountFilter changes
  useEffect(() => {
    // Make sure we have transactions before attempting to filter
    if (!Array.isArray(transactions) || transactions.length === 0) {
      console.log('No transactions to filter');
      setFilteredTransactions([]);
      return;
    }
    
    console.log(`Filtering ${transactions.length} transactions`);
    let filtered = [...transactions];
    
    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(transaction => {
        const descMatch = transaction.description && 
          transaction.description.toLowerCase().includes(searchTerm.toLowerCase());
        const amountMatch = transaction.amount !== undefined && 
          transaction.amount.toString().includes(searchTerm);
        return descMatch || amountMatch;
      });
      console.log(`After search term filtering: ${filtered.length} transactions`);
    }
    
    // Filter by category
    if (categoryFilter) {
      filtered = filtered.filter(transaction => {
        // Check both category ID and category_name for flexibility
        return (
          transaction.category === categoryFilter || 
          transaction.category === parseInt(categoryFilter) ||
          (transaction.category_name && 
           transaction.category_name.toLowerCase() === categoryFilter.toLowerCase())
        );
      });
      console.log(`After category filtering: ${filtered.length} transactions`);
    }
    
    // Filter by bank account
    if (bankAccountFilter) {
      filtered = filtered.filter(transaction => 
        transaction.bank_account_id === bankAccountFilter
      );
      console.log(`After bank account filtering: ${filtered.length} transactions`);
    }
    
    // Filter by account ID
    if (accountIdFilter) {
      filtered = filtered.filter(transaction => 
        transaction.account_id === accountIdFilter
      );
      console.log(`After account ID filtering: ${filtered.length} transactions`);
    }
    
    console.log(`Final filtered transactions: ${filtered.length}`);
    setFilteredTransactions(filtered);
    setPage(0); // Reset to first page when filters change
  }, [transactions, searchTerm, categoryFilter, bankAccountFilter, accountIdFilter]);

  // Handle search term change
  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  // Handle category filter change
  const handleCategoryFilterChange = (event) => {
    setCategoryFilter(event.target.value);
  };
  
  // Handle bank account filter change
  const handleBankAccountFilterChange = (event) => {
    setBankAccountFilter(event.target.value);
  };

  // Handle account ID filter change
  const handleAccountIdFilterChange = (event) => {
    setAccountIdFilter(event.target.value);
  };

  // Handle page change
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  // Handle rows per page change
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Handle category change for a transaction
  const handleCategoryChange = (transactionId, categoryId) => {
    setEditingTransaction(transactionId);
  };

  // Save category change
  const handleSaveCategory = async (transactionId, categoryId) => {
    try {
      await axios.post(`${API_URL}/categorize/${transactionId}/`, {
        category_id: categoryId
      });
      setEditingTransaction(null);
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Error updating category:', error);
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch (error) {
      console.error('Error formatting date:', error);
      return '';
    }
  };

  // Format amount
  const formatAmount = (amount) => {
    if (amount === undefined || amount === null) return '0.00';
    try {
      return new Intl.NumberFormat('nb-NO', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount);
    } catch (error) {
      console.error('Error formatting amount:', error);
      return '0.00';
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Transactions
        </Typography>
        
        {/* Debug section - only visible during development */}
        {process.env.NODE_ENV === 'development' && (
          <Box sx={{ mb: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>Debug Info:</Typography>
            <Typography variant="body2">
              Transactions count: {Array.isArray(transactions) ? transactions.length : 0}<br />
              Filtered count: {filteredTransactions.length}<br />
              Categories count: {categoriesList.length}<br />
              Bank accounts count: {bankAccounts.length}<br />
              Account IDs count: {accountIds.length}
            </Typography>
            {Array.isArray(transactions) && transactions.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2">First transaction:</Typography>
                <pre style={{ fontSize: '0.75rem', overflow: 'auto', maxHeight: '100px' }}>
                  {JSON.stringify(transactions[0], null, 2)}
                </pre>
              </Box>
            )}
          </Box>
        )}
        
        <Box sx={{ display: 'flex', mb: 2, gap: 2, flexWrap: 'wrap' }}>
          <TextField
            label="Search"
            variant="outlined"
            size="small"
            value={searchTerm}
            onChange={handleSearchChange}
            sx={{ flexGrow: 1, minWidth: '200px' }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
          <TextField
            select
            label="Category"
            variant="outlined"
            size="small"
            value={categoryFilter}
            onChange={handleCategoryFilterChange}
            sx={{ minWidth: '150px' }}
          >
            <MenuItem value="">All Categories</MenuItem>
            {categoriesList.map((category) => (
              <MenuItem key={category.id} value={category.id}>
                {category.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Bank Account"
            variant="outlined"
            size="small"
            value={bankAccountFilter}
            onChange={handleBankAccountFilterChange}
            sx={{ minWidth: '150px' }}
          >
            <MenuItem value="">All Bank Accounts</MenuItem>
            {bankAccounts.map((account) => (
              <MenuItem key={account} value={account}>
                {account}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Account ID"
            variant="outlined"
            size="small"
            value={accountIdFilter}
            onChange={handleAccountIdFilterChange}
            sx={{ minWidth: '150px' }}
          >
            <MenuItem value="">All Account IDs</MenuItem>
            {accountIds.map((id) => (
              <MenuItem key={id} value={id}>
                {id}
              </MenuItem>
            ))}
          </TextField>
        </Box>
        
        {loading ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', p: 3 }}>
            <CircularProgress />
            <Typography variant="body2" sx={{ mt: 2 }}>
              {loadingProgress?.total > 0 ? 
                `Loading ${loadingProgress.loaded} of ${loadingProgress.total} transactions (Page ${loadingProgress.page})` : 
                'Loading transactions...'}
            </Typography>
          </Box>
        ) : (
          <>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell align="right">Amount</TableCell>
                    <TableCell>Bank Account</TableCell>
                    <TableCell>Account ID</TableCell>
                    <TableCell>Category</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredTransactions.length > 0 ? (
                    filteredTransactions
                      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                      .map((transaction) => (
                        <TableRow key={transaction.id || Math.random()}>
                          <TableCell>{formatDate(transaction.date)}</TableCell>
                          <TableCell>{transaction.description || ''}</TableCell>
                          <TableCell align="right">
                            <Chip
                              label={formatAmount(transaction.amount)}
                              color={(transaction.amount || 0) < 0 ? "error" : "success"}
                              variant="outlined"
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            {transaction.bank_account_id || 'Unknown'}
                          </TableCell>
                          <TableCell>
                            {transaction.account_id || 'N/A'}
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <TextField
                                select
                                size="small"
                                value={transaction.category || ''}
                                onChange={(e) => handleCategoryChange(transaction.id, e.target.value)}
                                variant="outlined"
                                sx={{ minWidth: 150 }}
                              >
                                <MenuItem value="">Uncategorized</MenuItem>
                                {categoriesList.map((category) => (
                                  <MenuItem key={category.id} value={category.id}>
                                    {category.name}
                                  </MenuItem>
                                ))}
                              </TextField>
                              {editingTransaction === transaction.id && (
                                <IconButton 
                                  size="small" 
                                  color="primary"
                                  onClick={() => handleSaveCategory(transaction.id, transaction.category)}
                                >
                                  <SaveIcon />
                                </IconButton>
                              )}
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        {transactionData.length > 0 ? 'No matching transactions found' : 'No transactions available'}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              rowsPerPageOptions={[5, 10, 25, 50, 100]}
              component="div"
              count={filteredTransactions.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
            />
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default TransactionList; 