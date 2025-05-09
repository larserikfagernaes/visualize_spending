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
  InputAdornment,
  TableSortLabel,
  Button
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import GetAppIcon from '@mui/icons-material/GetApp';
import axios from 'axios';
import TransactionDetailModal from './TransactionDetailModal';
import { getSuppliers, updateTransaction } from '../services/transactionService';

const API_URL = 'http://localhost:8000/api/v1';

const TransactionList = ({ 
  transactions = [], 
  categories = [], 
  onUpdate, 
  loading, 
  loadingProgress, 
  showingAllTransactions = false,
  activeFilters = {}
}) => {
  // State
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [bankAccountFilter, setBankAccountFilter] = useState('');
  const [associatedAccountFilter, setAssociatedAccountFilter] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(100);
  const [editingTransaction, setEditingTransaction] = useState(null);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [associatedAccounts, setAssociatedAccounts] = useState([]);
  // Add sort state
  const [sortConfig, setSortConfig] = useState({
    key: null,
    direction: 'asc'
  });

  // State for transaction detail modal
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState(null);

  // Add new state for suppliers
  const [suppliers, setSuppliers] = useState([]);
  const [editingSupplierTransaction, setEditingSupplierTransaction] = useState(null);

  // Ensure transactions and categories are always arrays
  const transactionData = Array.isArray(transactions) ? transactions : [];
  const categoriesList = Array.isArray(categories) ? categories : [];
  
  console.log('TransactionList received props:', { 
    transactionsCount: transactions?.length || 0,
    categoriesCount: categories?.length || 0,
    loading
  });

  // Extract unique bank accounts and associated accounts from transactions
  useEffect(() => {
    if (Array.isArray(transactions) && transactions.length > 0) {
      // Extract bank accounts - use account_id if bank_account fields are not available
      const accounts = transactions
        .map(transaction => 
          transaction.bank_account_name || 
          transaction.bank_account_id || 
          (transaction.account_id ? `Account: ${transaction.account_id}` : null)
        )
        .filter((account, index, self) => 
          account && self.indexOf(account) === index
        )
        .sort();
      
      setBankAccounts(accounts);
      
      // Extract associated accounts (from related_accounts array)
      const associatedAccountsList = new Set();
      
      transactions.forEach(transaction => {
        if (transaction.related_accounts && Array.isArray(transaction.related_accounts)) {
          transaction.related_accounts.forEach(account => {
            if (account && account.name) {
              associatedAccountsList.add(account.name);
            }
          });
        }
      });
      
      // Convert to array and sort
      const associatedAccountsArray = Array.from(associatedAccountsList).sort();
      setAssociatedAccounts(associatedAccountsArray);
      
      console.log(`Extracted ${accounts.length} bank accounts and ${associatedAccountsArray.length} associated accounts`);
    }
  }, [transactions]);

  // Filter transactions when transactions, searchTerm, categoryFilter, bankAccountFilter, or associatedAccountFilter changes
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
        // Convert categoryFilter to string for comparison if it's a number
        const categoryFilterStr = typeof categoryFilter === 'string' ? categoryFilter : String(categoryFilter);
        
        return (
          transaction.category === categoryFilter || 
          transaction.category === parseInt(categoryFilter) ||
          (transaction.category_name && 
           typeof categoryFilter === 'string' && 
           transaction.category_name.toLowerCase() === categoryFilter.toLowerCase())
        );
      });
      console.log(`After category filtering: ${filtered.length} transactions`);
    }
    
    // Filter by bank account
    if (bankAccountFilter) {
      filtered = filtered.filter(transaction => 
        transaction.bank_account_name === bankAccountFilter || 
        transaction.bank_account_id === bankAccountFilter ||
        (bankAccountFilter.startsWith('Account: ') && 
         `Account: ${transaction.account_id}` === bankAccountFilter)
      );
      console.log(`After bank account filtering: ${filtered.length} transactions`);
    }
    
    // Filter by associated account
    if (associatedAccountFilter) {
      filtered = filtered.filter(transaction => {
        // Check if transaction has related_accounts array
        if (!transaction.related_accounts || !Array.isArray(transaction.related_accounts)) {
          return false;
        }
        
        // Check if any of the related accounts match the filter
        return transaction.related_accounts.some(account => 
          account && account.name === associatedAccountFilter
        );
      });
      console.log(`After associated account filtering: ${filtered.length} transactions`);
    }
    
    console.log(`Final filtered transactions: ${filtered.length}`);
    setFilteredTransactions(filtered);
    setPage(0); // Reset to first page when filters change
  }, [transactions, searchTerm, categoryFilter, bankAccountFilter, associatedAccountFilter]);

  // Debug effect to inspect category data structure
  useEffect(() => {
    if (filteredTransactions.length > 0) {
      const sample = filteredTransactions[0];
      console.log('Sample transaction category data:', {
        id: sample.id,
        category: sample.category,
        category_type: typeof sample.category,
        category_name: sample.category_name
      });
      
      // Also log the categories list format
      if (categoriesList.length > 0) {
        console.log('First category in categoriesList:', {
          id: categoriesList[0].id,
          id_type: typeof categoriesList[0].id,
          name: categoriesList[0].name
        });
      }
    }
  }, [filteredTransactions, categoriesList]);

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

  // Handle associated account filter change
  const handleAssociatedAccountFilterChange = (event) => {
    setAssociatedAccountFilter(event.target.value);
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
  const handleCategoryChange = async (transactionId, categoryId) => {
    // Set editing for visual feedback
    setEditingTransaction(transactionId);
    
    try {
      // Find the category name for the selected category ID (categoryId is a string)
      const selectedCategory = categoriesList.find(cat => String(cat.id) === categoryId);
      const categoryName = selectedCategory ? selectedCategory.name : null;
      
      // Convert empty string to null for the API
      const apiCategoryId = categoryId === '' ? null : categoryId;
      
      // Log the category change for debugging
      console.log('Changing category:', {
        transactionId,
        categoryId,
        apiCategoryId,
        categoryName,
        selectedCategory
      });
      
      // Save immediately when category is changed
      const response = await axios.post(`${API_URL}/categorize/${transactionId}/`, {
        category_id: apiCategoryId
      });
      
      // Update the transaction in the UI regardless of batch update
      const updateTransaction = (tx) => {
        if (tx.id === transactionId) {
          return {
            ...tx,
            category: categoryId ? parseInt(categoryId) : null,
            category_name: categoryName
          };
        }
        
        // If batch updating (same supplier), update other transactions from same supplier
        if (response.data.updated_transactions_count && 
            response.data.transaction?.supplier &&
            tx.supplier === response.data.transaction.supplier) {
          return {
            ...tx,
            category: categoryId ? parseInt(categoryId) : null,
            category_name: categoryName
          };
        }
        
        return tx;
      };
      
      // Always update filtered transactions for immediate UI feedback
      setFilteredTransactions(prevTransactions => 
        prevTransactions.map(updateTransaction)
      );
      
      // If there was a batch update, we should refresh the entire list
      if (response.data.updated_transactions_count && onUpdate) {
        console.log(`Updated ${response.data.updated_transactions_count} transactions with the same supplier`);
        onUpdate();
      }
      
      // Clear editing status after a short delay for visual feedback
      setTimeout(() => {
        setEditingTransaction(null);
      }, 500);
      
    } catch (error) {
      console.error('Error updating category:', error);
      // Clear editing status
      setEditingTransaction(null);
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

  // Handler for row click
  const handleRowClick = async (transaction) => {
    let transactionWithData = transaction;
    
    // If transaction doesn't have raw_data, fetch it from the API
    if (!transaction.raw_data) {
      console.log(`Transaction ${transaction.id} has no raw_data, fetching from API`);
      
      // Set loading state for the modal
      setSelectedTransaction({
        ...transaction,
        _loading: true,
        _error: null
      });
      setModalOpen(true);
      
      try {
        console.log(`Fetching raw data for transaction ${transaction.id} (tripletex_id: ${transaction.tripletex_id || 'none'})`);
        const response = await axios.get(`${API_URL}/transactions/${transaction.id}/detail_with_raw_data/`);
        
        if (response.data && response.data.raw_data) {
          console.log(`Successfully fetched raw_data for transaction ${transaction.id}`);
          transactionWithData = response.data;
          
          // Update the transaction in filtered transactions to cache the raw_data
          setFilteredTransactions(prevTransactions => 
            prevTransactions.map(t => 
              t.id === transaction.id ? transactionWithData : t
            )
          );
          
          setSelectedTransaction(transactionWithData);
        } else {
          console.warn(`Received response but no raw_data for transaction ${transaction.id}`);
          setSelectedTransaction({
            ...transaction,
            _loading: false,
            _error: 'Transaction details could not be loaded. The data may be unavailable.'
          });
        }
      } catch (error) {
        console.error('Error fetching transaction details:', error);
        setSelectedTransaction({
          ...transaction,
          _loading: false,
          _error: error.response?.data?.error || 'Failed to load transaction details. Please try again.'
        });
      }
    } else {
      console.log(`Transaction ${transaction.id} already has raw_data`);
      setSelectedTransaction(transaction);
      setModalOpen(true);
    }
  };

  // Handler for closing the modal
  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedTransaction(null);
  };

  // Add sorting handler
  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
    
    // Reset to first page when sorting changes
    setPage(0);
  };

  // Sort transactions based on sort configuration
  const sortedTransactions = React.useMemo(() => {
    if (!sortConfig.key) return filteredTransactions;
    
    return [...filteredTransactions].sort((a, b) => {
      // Handle numeric sorting for amount
      if (sortConfig.key === 'amount') {
        const aValue = parseFloat(a[sortConfig.key]) || 0;
        const bValue = parseFloat(b[sortConfig.key]) || 0;
        
        return sortConfig.direction === 'asc' 
          ? aValue - bValue 
          : bValue - aValue;
      }
      
      // Default string sorting for other fields
      if (a[sortConfig.key] < b[sortConfig.key]) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (a[sortConfig.key] > b[sortConfig.key]) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
  }, [filteredTransactions, sortConfig]);

  // Calculate the total sum of all filtered transactions
  const totalAmount = React.useMemo(() => {
    if (!filteredTransactions || filteredTransactions.length === 0) return 0;
    
    return filteredTransactions.reduce((sum, transaction) => {
      const amount = parseFloat(transaction.amount) || 0;
      return sum + amount;
    }, 0);
  }, [filteredTransactions]);

  // Export transactions to CSV
  const exportToCSV = () => {
    if (!filteredTransactions || filteredTransactions.length === 0) {
      console.warn('No transactions to export');
      return;
    }
    
    // Define CSV columns
    const headers = ['Date', 'Description', 'Amount', 'Bank Account', 'Supplier', 'Category'];
    
    // Convert filtered transactions to CSV rows
    const rows = filteredTransactions.map(transaction => [
      formatDate(transaction.date),
      // Escape quotes in description by doubling them
      `"${(transaction.description || '').replace(/"/g, '""')}"`,
      transaction.amount,
      transaction.bank_account_name || transaction.bank_account_id || 'Unknown',
      transaction.supplier_name || 'No Supplier',
      transaction.category_name || 'Uncategorized'
    ]);
    
    // Create CSV content
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    // Create a blob and download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `transactions_export_${new Date().toISOString().slice(0, 10)}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Fetch suppliers on mount
  useEffect(() => {
    getSuppliers()
      .then(data => {
        console.log('Suppliers loaded:', data);
        setSuppliers(data);
      })
      .catch((e) => console.error('Failed to fetch suppliers:', e));
  }, []);

  // Handle supplier change
  const handleSupplierChange = async (transactionId, supplierId) => {
    setEditingSupplierTransaction(transactionId);
    try {
      await updateTransaction(transactionId, { supplier: supplierId || null });
      setFilteredTransactions((prev) => prev.map((tx) =>
        tx.id === transactionId ? { ...tx, supplier: supplierId ? parseInt(supplierId) : null, supplier_name: suppliers.find(s => String(s.id) === supplierId)?.name || 'No Supplier' } : tx
      ));
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Error updating supplier:', error);
    } finally {
      setTimeout(() => setEditingSupplierTransaction(null), 500);
    }
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Transactions
          </Typography>
          
          {/* Active filters display */}
          {Object.values(activeFilters).some(value => value) && (
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
            </Box>
          )}
        </Box>

        {/* Display total sum */}
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          mb: 3, 
          p: 2, 
          bgcolor: totalAmount < 0 ? 'rgba(255, 0, 0, 0.04)' : 'rgba(0, 128, 0, 0.04)', 
          borderRadius: 1,
          border: '1px solid rgba(0, 0, 0, 0.12)'
        }}>
          <Box>
            <Typography variant="subtitle1" fontWeight="medium">
              Total Amount
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {filteredTransactions.length} transactions
            </Typography>
          </Box>
          <Chip
            label={new Intl.NumberFormat('nb-NO', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2
            }).format(totalAmount)}
            color={totalAmount < 0 ? "error" : "success"}
            size="medium"
            sx={{ fontWeight: 'bold', fontSize: '1.1rem', py: 0.5, px: 0.5 }}
          />
        </Box>
        
        {/* Debug section - only visible during development */}
        {process.env.NODE_ENV === 'development' && (
          <Box sx={{ mb: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>Debug Info:</Typography>
            <Typography variant="body2">
              Transactions count: {Array.isArray(transactions) ? transactions.length : 0}<br />
              Filtered count: {filteredTransactions.length}<br />
              Categories count: {categoriesList.length}<br />
              Bank accounts count: {bankAccounts.length}<br />
              Associated accounts count: {associatedAccounts.length}<br />
              All transactions loaded: {showingAllTransactions ? 'Yes' : 'No (first page only)'}<br />
              Universal filters active: Yes (applied from App component)
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
        
        <Box sx={{ display: 'flex', mb: 2, gap: 2, flexWrap: 'wrap', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', flexGrow: 1 }}>
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
              label="Associated Account"
              variant="outlined"
              size="small"
              value={associatedAccountFilter}
              onChange={handleAssociatedAccountFilterChange}
              sx={{ minWidth: '200px' }}
            >
              <MenuItem value="">All Associated Accounts</MenuItem>
              {associatedAccounts.map((account) => (
                <MenuItem key={account} value={account}>
                  {account}
                </MenuItem>
              ))}
            </TextField>
          </Box>
          <Button
            variant="outlined"
            startIcon={<GetAppIcon />}
            onClick={exportToCSV}
            disabled={filteredTransactions.length === 0}
            size="small"
            sx={{ height: 40 }}
          >
            Download CSV
          </Button>
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
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortConfig.key === 'amount'}
                        direction={sortConfig.key === 'amount' ? sortConfig.direction : 'asc'}
                        onClick={() => handleSort('amount')}
                      >
                        Amount
                      </TableSortLabel>
                    </TableCell>
                    <TableCell>Bank Account</TableCell>
                    <TableCell>Supplier</TableCell>
                    <TableCell>Category</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredTransactions.length > 0 ? (
                    sortedTransactions
                      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                      .map((transaction) => (
                        <TableRow 
                          key={transaction.id || Math.random()}
                          onClick={() => handleRowClick(transaction)}
                          sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' } }}
                        >
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
                            {transaction.bank_account_name || 
                             transaction.bank_account_id || 
                             (transaction.account_id ? `Account: ${transaction.account_id}` : 'Unknown')}
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <TextField
                                select
                                size="small"
                                value={transaction.supplier ? String(transaction.supplier) : ''}
                                onChange={(e) => { e.stopPropagation(); handleSupplierChange(transaction.id, e.target.value); }}
                                variant="outlined"
                                sx={{ minWidth: 180 }}
                                SelectProps={{
                                  renderValue: (value) => {
                                    if (!value) return 'No Supplier';
                                    const sup = suppliers.find(s => String(s.id) === value);
                                    return sup ? sup.name : 'No Supplier';
                                  },
                                }}
                              >
                                <MenuItem value="">No Supplier</MenuItem>
                                {suppliers.map((supplier) => (
                                  <MenuItem key={supplier.id} value={String(supplier.id)}>
                                    {supplier.name || supplier.tripletex_id}
                                  </MenuItem>
                                ))}
                              </TextField>
                              {editingSupplierTransaction === transaction.id && (
                                <CircularProgress size={20} sx={{ ml: 1 }} />
                              )}
                            </Box>
                          </TableCell>
                          <TableCell onClick={(e) => e.stopPropagation()}>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <TextField
                                select
                                size="small"
                                value={transaction.category ? String(transaction.category) : ''}
                                onChange={(e) => handleCategoryChange(transaction.id, e.target.value)}
                                variant="outlined"
                                sx={{ minWidth: 150 }}
                                SelectProps={{
                                  renderValue: (value) => {
                                    if (!value) return "Uncategorized";
                                    const cat = categoriesList.find(c => String(c.id) === value);
                                    return cat ? cat.name : "Uncategorized";
                                  },
                                }}
                              >
                                <MenuItem value="">Uncategorized</MenuItem>
                                {categoriesList.map((category) => (
                                  <MenuItem key={category.id} value={String(category.id)}>
                                    {category.name}
                                  </MenuItem>
                                ))}
                              </TextField>
                              {editingTransaction === transaction.id && (
                                <CircularProgress size={20} sx={{ ml: 1 }} />
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
              rowsPerPageOptions={[100, 5, 10, 25, 50, 200]}
              component="div"
              count={filteredTransactions.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
              labelDisplayedRows={({ from, to, count }) => 
                showingAllTransactions 
                  ? `${from}-${to} of ${count}`                  : `${from}-${to} of ${count} (showing only first page from API)`
              }
            />
          </>
        )}
      </CardContent>

      {/* Transaction Detail Modal */}
      <TransactionDetailModal
        open={modalOpen}
        onClose={handleCloseModal}
        transaction={selectedTransaction}
      />
    </Card>
  );
};

export default TransactionList; 
