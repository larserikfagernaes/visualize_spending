import React, { useState, useEffect } from 'react';
import { Container, Box, Tabs, Tab, AppBar, Typography, CssBaseline, ThemeProvider, createTheme, FormGroup, FormControlLabel, Checkbox, Paper, Chip, Stack, TextField, Grid, Button } from '@mui/material';
import axios from 'axios';
import ClearIcon from '@mui/icons-material/Clear';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import { format } from 'date-fns';

// Import components
import TransactionList from './components/TransactionList';
import TransactionSummary from './components/TransactionSummary';
import TransactionChart from './components/TransactionChart';
import CategoryManager from './components/CategoryManager';
import ImportTransactions from './components/ImportTransactions';
import TransactionListTest from './tests/TransactionListTest';
import ApiTest from './components/ApiTest';
import ApiTestDashboard from './components/ApiTestDashboard';
import TransactionTreeMap from './components/TransactionTreeMap';

// API URL - using the same endpoint as in services/api.js
const API_URL = 'http://localhost:8000/api/v1';

// Create encoded credentials only once
const authCredentials = btoa('dev:dev');

// Create theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

// Filter Status component
const FilterStatus = ({ filters }) => {
  // Count active filters
  const activeFilters = Object.entries(filters)
    .filter(([key, value]) => {
      if (['amountMin', 'amountMax'].includes(key)) {
        return value !== '';
      }
      if (['startDate', 'endDate'].includes(key)) {
        return value !== null;
      }
      return value;
    }).length;
  
  if (activeFilters === 0) {
    return <Typography variant="body2" color="text.secondary">No filters active</Typography>;
  }
  
  // Format date for display
  const formatDate = (date) => {
    if (!date) return '';
    return format(new Date(date), 'MMM dd, yyyy');
  };
  
  return (
    <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
      <Typography variant="body2" color="text.secondary">Active filters:</Typography>
      {filters.hideInternalTransfers && <Chip size="small" label="Hiding Internal Transfers" color="primary" variant="outlined" />}
      {filters.hideWageTransfers && <Chip size="small" label="Hiding Wage Transfers" color="primary" variant="outlined" />}
      {filters.hideTaxTransfers && <Chip size="small" label="Hiding Tax Transfers" color="primary" variant="outlined" />}
      {filters.showOnlyProcessable && <Chip size="small" label="Showing Only Processable" color="primary" variant="outlined" />}
      {filters.amountMin !== '' && (
        <Chip size="small" label={`Min Amount: ${filters.amountMin}`} color="primary" variant="outlined" />
      )}
      {filters.amountMax !== '' && (
        <Chip size="small" label={`Max Amount: ${filters.amountMax}`} color="primary" variant="outlined" />
      )}
      {filters.startDate && (
        <Chip size="small" label={`From: ${formatDate(filters.startDate)}`} color="primary" variant="outlined" />
      )}
      {filters.endDate && (
        <Chip size="small" label={`To: ${formatDate(filters.endDate)}`} color="primary" variant="outlined" />
      )}
    </Stack>
  );
};

function App() {
  // State
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [summaryData, setSummaryData] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadAllTransactions, setLoadAllTransactions] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState({
    loaded: 0,
    total: 0,
    page: 0
  });
  
  // Universal filters state
  const [universalFilters, setUniversalFilters] = useState({
    hideInternalTransfers: false,
    hideWageTransfers: false,
    hideTaxTransfers: false,
    showOnlyProcessable: false,
    amountMin: '',
    amountMax: '',
    startDate: null,
    endDate: null
  });
  
  // Filtered transactions based on universal filters
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  
  // Apply universal filters to transactions
  useEffect(() => {
    if (!Array.isArray(transactions) || transactions.length === 0) {
      setFilteredTransactions([]);
      return;
    }
    
    let filtered = [...transactions];
    
    // Apply universal filters
    if (universalFilters.hideInternalTransfers) {
      filtered = filtered.filter(t => !t.is_internal_transfer);
    }
    
    if (universalFilters.hideWageTransfers) {
      filtered = filtered.filter(t => !t.is_wage_transfer);
    }
    
    if (universalFilters.hideTaxTransfers) {
      filtered = filtered.filter(t => !t.is_tax_transfer);
    }
    
    if (universalFilters.showOnlyProcessable) {
      filtered = filtered.filter(t => t.should_process);
    }
    
    // Apply amount filters
    if (universalFilters.amountMin !== '') {
      const minAmount = parseFloat(universalFilters.amountMin);
      if (!isNaN(minAmount)) {
        filtered = filtered.filter(t => t.amount >= minAmount);
      }
    }
    
    if (universalFilters.amountMax !== '') {
      const maxAmount = parseFloat(universalFilters.amountMax);
      if (!isNaN(maxAmount)) {
        filtered = filtered.filter(t => t.amount <= maxAmount);
      }
    }
    
    // Apply date filters
    if (universalFilters.startDate) {
      const startDate = new Date(universalFilters.startDate);
      startDate.setHours(0, 0, 0, 0); // Start of day
      filtered = filtered.filter(t => {
        const transactionDate = new Date(t.date);
        return transactionDate >= startDate;
      });
    }
    
    if (universalFilters.endDate) {
      const endDate = new Date(universalFilters.endDate);
      endDate.setHours(23, 59, 59, 999); // End of day
      filtered = filtered.filter(t => {
        const transactionDate = new Date(t.date);
        return transactionDate <= endDate;
      });
    }
    
    setFilteredTransactions(filtered);
    
    // Update summary data with the same filters if available
    if (summaryData) {
      fetchSummaryWithFilters(filtered);
    }
  }, [transactions, universalFilters]);
  
  // Handle universal filter changes for checkboxes
  const handleFilterChange = (event) => {
    const { name, checked } = event.target;
    
    // Only process boolean filters with this handler
    if (name !== 'amountMin' && name !== 'amountMax') {
      setUniversalFilters({
        ...universalFilters,
        [name]: checked
      });
    }
  };
  
  // Handle amount filter changes
  const handleAmountFilterChange = (event) => {
    const { name, value } = event.target;
    // Allow only numeric input, empty string, minus sign for the minimum value
    const isValidInput = 
      name === 'amountMin' 
        ? (value === '' || value === '-' || /^-?\d*\.?\d*$/.test(value))
        : (value === '' || /^\d*\.?\d*$/.test(value));
        
    if (isValidInput) {
      setUniversalFilters({
        ...universalFilters,
        [name]: value
      });
    }
  };
  
  // Handle date filter changes
  const handleDateChange = (name, date) => {
    setUniversalFilters({
      ...universalFilters,
      [name]: date
    });
  };
  
  // Clear all filters
  const clearFilters = () => {
    setUniversalFilters({
      hideInternalTransfers: false,
      hideWageTransfers: false,
      hideTaxTransfers: false,
      showOnlyProcessable: false,
      amountMin: '',
      amountMax: '',
      startDate: null,
      endDate: null
    });
  };
  
  // Get summary data with filtered transactions
  const fetchSummaryWithFilters = (filteredTrans) => {
    if (!filteredTrans || filteredTrans.length === 0) return;
    
    // If we have filtered transactions already, calculate summary client-side
    try {
      // Group by category
      const categorySummary = {};
      const bankAccountSummary = {};
      
      filteredTrans.forEach(transaction => {
        // Process categories
        if (transaction.amount && transaction.amount < 0 && transaction.category_name) {
          const category = transaction.category_name;
          
          if (!categorySummary[category]) {
            categorySummary[category] = {
              total: 0,
              count: 0
            };
          }
          
          categorySummary[category].total += Math.abs(transaction.amount);
          categorySummary[category].count += 1;
        }
        
        // Process bank accounts
        if (transaction.amount !== undefined && transaction.amount !== null && transaction.bank_account_id) {
          const bankAccount = transaction.bank_account_id;
          
          if (!bankAccountSummary[bankAccount]) {
            bankAccountSummary[bankAccount] = {
              total: 0,
              count: 0
            };
          }
          
          // Convert amount to a number if it's not already
          const amount = typeof transaction.amount === 'number' ? 
            transaction.amount : 
            parseFloat(transaction.amount);
            
          // Only add if it's a valid number
          if (!isNaN(amount)) {
            bankAccountSummary[bankAccount].total += amount;
            bankAccountSummary[bankAccount].count += 1;
          }
        }
      });
      
      // Create summary object that matches the expected structure
      const calculatedSummary = {
        total_spending: Object.values(categorySummary).reduce((sum, cat) => sum + cat.total, 0),
        total_transactions: Object.values(categorySummary).reduce((sum, cat) => sum + cat.count, 0),
        total_amount: filteredTrans.reduce((sum, t) => sum + (parseFloat(t.amount) || 0), 0),
        categories: categorySummary,
        bank_accounts: bankAccountSummary,
        by_category: Object.entries(categorySummary).map(([name, data]) => ({
          category: name,
          total: data.total,
          count: data.count
        })).sort((a, b) => b.total - a.total)
      };
      
      console.log('Client-side calculated summary:', calculatedSummary);
      setSummaryData(calculatedSummary);
    } catch (error) {
      console.error('Error calculating summary data:', error);
    }
  };

  // Fetch transactions
  const fetchTransactions = async (loadAll = loadAllTransactions) => {
    setLoading(true);
    setLoadingProgress({ loaded: 0, total: 0, page: 0 });
    
    // Setup common request configuration
    const requestConfig = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Basic ${authCredentials}`
      },
      withCredentials: true
    };
    
    try {
      if (loadAll) {
        // Initialize variables for pagination
        let allTransactions = [];
        let nextUrl = `${API_URL}/transactions/`;
        let pageCount = 0;
        let totalCount = 0;
        
        // Loop until we've fetched all pages
        while (nextUrl) {
          pageCount++;
          console.log(`Fetching transactions page ${pageCount} from: ${nextUrl} (500 per page)`);
          
          // Fetch the current page with proper authentication
          const response = await axios.get(nextUrl, requestConfig);
          console.log('Response status:', response.status);
          
          // Skip processing if the response is invalid
          if (!response.data || !response.data.results || !Array.isArray(response.data.results)) {
            console.error('Invalid response format:', response.data);
            break;
          }
          
          // Add this page's transactions to our collection
          const pageTransactions = response.data.results;
          allTransactions = [...allTransactions, ...pageTransactions];
          
          // Update total count if available
          totalCount = response.data.count || totalCount;
          
          // Update progress
          setLoadingProgress({
            loaded: allTransactions.length,
            total: totalCount,
            page: pageCount
          });
          
          console.log(`Loaded ${allTransactions.length} of ${totalCount} transactions (page ${pageCount})`);
          
          // Determine if there's another page to fetch
          if (response.data.next) {
            // Handle the next URL correctly
            if (response.data.next.startsWith('http')) {
              // It's an absolute URL, use it directly
              nextUrl = response.data.next;
            } else {
              // It's a relative URL, could be just "/transactions/?page=2" or "/api/transactions/?page=2"
              if (response.data.next.includes('/api/')) {
                // Already has /api/ prefix, just use API server domain
                const apiBase = API_URL.split('/api')[0]; // Get just http://localhost:8000
                nextUrl = `${apiBase}${response.data.next}`;
              } else {
                // Doesn't include /api/, add it
                nextUrl = `${API_URL}${response.data.next}`;
              }
            }
            console.log(`Next URL resolved to: ${nextUrl}`);
          } else {
            nextUrl = null; // No more pages
          }
        }
        
        // Update state with all fetched transactions
        console.log(`Finished loading ${allTransactions.length} total transactions`);
        setTransactions(allTransactions);
      } else {
        // Fetch only the first page of transactions
        const url = `${API_URL}/transactions/`;
        console.log(`Fetching first page of transactions from: ${url}`);
        
        const response = await axios.get(url, requestConfig);
        console.log('Response status:', response.status);
        
        // Skip processing if the response is invalid
        if (!response.data || !response.data.results || !Array.isArray(response.data.results)) {
          console.error('Invalid response format:', response.data);
          setTransactions([]);
          return;
        }
        
        // Get transactions from the first page only
        const pageTransactions = response.data.results;
        const totalCount = response.data.count || 0;
        
        // Update progress
        setLoadingProgress({
          loaded: pageTransactions.length,
          total: totalCount,
          page: 1
        });
        
        console.log(`Loaded ${pageTransactions.length} transactions (first page only). Total available: ${totalCount}`);
        
        // Update state with fetched transactions
        setTransactions(pageTransactions);
      }
      
      // Fetch summary data
      fetchSummary();
      
    } catch (error) {
      console.error('Error fetching transactions:', error);
      console.error('Error details:', error.response ? error.response.data : 'No response data');
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch transactions and categories on component mount
  useEffect(() => {
    // Define this wrapper function to make the linter happy
    const loadInitialData = async () => {
      await fetchTransactions();
      await fetchCategories();
      // Fetch bank accounts after transactions and summary data to ensure we have data to create mock accounts if needed
      await fetchBankAccounts();
    };
    
    loadInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update bank accounts whenever transactions or summary data changes
  useEffect(() => {
    // Don't run on initial render when both are empty
    if ((transactions && transactions.length > 0) || (summaryData && summaryData.bank_accounts)) {
      fetchBankAccounts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transactions, summaryData]);

  // Fetch categories
  const fetchCategories = async () => {
    try {
      console.log('Fetching categories...');
      const response = await axios.get(`${API_URL}/categories/`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Basic ${authCredentials}`
        },
        withCredentials: true
      });
      if (response.data && Array.isArray(response.data.results)) {
        console.log(`Successfully fetched ${response.data.results.length} categories`);
        setCategories(response.data.results);
      } else {
        console.error('Invalid categories data format:', response.data);
        setCategories([]);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
      setCategories([]);
    }
  };

  // Fetch bank accounts
  const fetchBankAccounts = async () => {
    // Use the same request config for consistency
    const requestConfig = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Basic ${authCredentials}`
      },
      withCredentials: true
    };
    
    try {
      const response = await axios.get(`${API_URL}/bank-accounts/`, requestConfig);
      if (Array.isArray(response.data) && response.data.length > 0) {
        setBankAccounts(response.data);
        console.log('Fetched bank accounts:', response.data);
      } else {
        console.warn('Empty bank accounts data from API, using mock data');
        
        // If the API returns empty bank accounts, create mock data from transactions
        let mockBankAccounts = [];
        
        // Extract unique bank account IDs from transactions
        if (transactions && transactions.length > 0) {
          const uniqueBankAccountIds = new Set();
          
          transactions.forEach(transaction => {
            if (transaction.bank_account_id) {
              uniqueBankAccountIds.add(transaction.bank_account_id);
            }
          });
          
          // Create mock bank account objects
          mockBankAccounts = Array.from(uniqueBankAccountIds).map(id => {
            // For special IDs with text/string format, use the ID directly as the name
            const isSpecialId = typeof id === 'string' && isNaN(parseInt(id));
            return {
              id: id,
              name: isSpecialId ? id : id.toString(),
              account_number: `${id}`,
              bank_name: 'Bank',
              account_type: 'Checking',
              is_active: true
            };
          });
        }
        
        // If we also have summary data, ensure all bank accounts from there are represented
        if (summaryData && summaryData.bank_accounts) {
          const summaryBankIds = Object.keys(summaryData.bank_accounts);
          
          summaryBankIds.forEach(id => {
            // Check if this bank account is already in our mock data
            if (!mockBankAccounts.some(account => account.id.toString() === id.toString())) {
              // For special IDs with text/string format, use the ID directly as the name
              const isSpecialId = typeof id === 'string' && isNaN(parseInt(id));
              mockBankAccounts.push({
                id: id,
                name: isSpecialId ? id : id.toString(),
                account_number: `${id}`,
                bank_name: 'Bank',
                account_type: 'Checking',
                is_active: true
              });
            }
          });
        }
        
        console.log('Created mock bank accounts:', mockBankAccounts);
        setBankAccounts(mockBankAccounts);
      }
    } catch (error) {
      console.error('Error fetching bank accounts:', error);
      console.error('Error details:', error.response ? error.response.data : 'No response data');
      
      // If there's an error, still try to create mock data from transactions
      const mockBankAccounts = [];
      
      // Extract unique bank account IDs from transactions
      if (transactions && transactions.length > 0) {
        const uniqueBankAccountIds = new Set();
        
        transactions.forEach(transaction => {
          if (transaction.bank_account_id) {
            uniqueBankAccountIds.add(transaction.bank_account_id);
          }
        });
        
        // Create mock bank account objects
        uniqueBankAccountIds.forEach(id => {
          // For special IDs with text/string format, use the ID directly as the name
          const isSpecialId = typeof id === 'string' && isNaN(parseInt(id));
          mockBankAccounts.push({
            id: id,
            name: isSpecialId ? id : id.toString(),
            account_number: `${id}`,
            bank_name: 'Bank',
            account_type: 'Checking',
            is_active: true
          });
        });
      }
      
      // If we also have summary data, add bank accounts from there
      if (summaryData && summaryData.bank_accounts) {
        const summaryBankIds = Object.keys(summaryData.bank_accounts);
        
        summaryBankIds.forEach(id => {
          // Check if this bank account is already in our mock data
          if (!mockBankAccounts.some(account => account.id.toString() === id.toString())) {
            // For special IDs with text/string format, use the ID directly as the name
            const isSpecialId = typeof id === 'string' && isNaN(parseInt(id));
            mockBankAccounts.push({
              id: id,
              name: isSpecialId ? id : id.toString(),
              account_number: `${id}`,
              bank_name: 'Bank',
              account_type: 'Checking',
              is_active: true
            });
          }
        });
      }
      
      console.log('Created mock bank accounts after API error:', mockBankAccounts);
      setBankAccounts(mockBankAccounts.length > 0 ? mockBankAccounts : []);
    }
  };

  // Fetch summary data
  const fetchSummary = async () => {
    // Use the same request config for consistency
    const requestConfig = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Basic ${authCredentials}`
      },
      withCredentials: true
    };
    
    try {
      const response = await axios.get(`${API_URL}/transactions/summary/`, requestConfig);
      console.log('Summary API response:', response.data);
      
      // Verify that the summary data has the expected structure
      if (!response.data) {
        console.error('Summary API returned empty data');
        setSummaryData(null);
        return;
      }
      
      setSummaryData(response.data);
      
      // If there are filtered transactions but no summary data from API, 
      // calculate the summary client-side
      if (filteredTransactions && filteredTransactions.length > 0 && 
          (!response.data.categories || Object.keys(response.data.categories).length === 0)) {
        console.log('Summary API returned empty categories, using client-side calculation');
        fetchSummaryWithFilters(filteredTransactions);
      }
    } catch (error) {
      console.error('Error fetching summary:', error);
      console.error('Error details:', error.response ? error.response.data : 'No response data');
      setSummaryData(null);
    }
  };

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Handle transaction update
  const handleTransactionUpdate = () => {
    fetchTransactions();
    fetchBankAccounts(); // Also refresh bank accounts when transactions are updated
  };

  // Handle category update
  const handleCategoryUpdate = () => {
    fetchCategories();
  };

  // Handle loading all transactions
  const handleLoadAllTransactions = () => {
    setLoadAllTransactions(true);
    fetchTransactions(true);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="xl">
        <Box sx={{ my: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Finance Visualizer
          </Typography>

          <AppBar position="static" color="default" sx={{ mb: 3 }}>
            <Tabs
              value={tabValue}
              onChange={handleTabChange}
              indicatorColor="primary"
              textColor="primary"
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab label="Transactions" />
              <Tab label="Summary" />
              <Tab label="Categories" />
              <Tab label="Import Data" />
              <Tab label="API Test" />
              <Tab label="API Test Dashboard" />
              <Tab label="TreeMap" />
            </Tabs>
          </AppBar>

          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>Filters</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={8}>
                <FormGroup row>
                  <FormControlLabel
                    control={
                      <Checkbox 
                        checked={universalFilters.hideInternalTransfers} 
                        onChange={handleFilterChange}
                        name="hideInternalTransfers"
                      />
                    }
                    label="Hide Internal Transfers"
                  />
                  <FormControlLabel
                    control={
                      <Checkbox 
                        checked={universalFilters.hideWageTransfers} 
                        onChange={handleFilterChange}
                        name="hideWageTransfers"
                      />
                    }
                    label="Hide Wage Transfers"
                  />
                  <FormControlLabel
                    control={
                      <Checkbox 
                        checked={universalFilters.hideTaxTransfers} 
                        onChange={handleFilterChange}
                        name="hideTaxTransfers"
                      />
                    }
                    label="Hide Tax Transfers"
                  />
                  <FormControlLabel
                    control={
                      <Checkbox 
                        checked={universalFilters.showOnlyProcessable} 
                        onChange={handleFilterChange}
                        name="showOnlyProcessable"
                      />
                    }
                    label="Show Only Processable"
                  />
                </FormGroup>
              </Grid>
              <Grid item xs={12} md={4}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    label="Min Amount"
                    variant="outlined"
                    size="small"
                    name="amountMin"
                    value={universalFilters.amountMin}
                    onChange={handleAmountFilterChange}
                    sx={{ width: '50%' }}
                  />
                  <TextField
                    label="Max Amount"
                    variant="outlined"
                    size="small"
                    name="amountMax"
                    value={universalFilters.amountMax}
                    onChange={handleAmountFilterChange}
                    sx={{ width: '50%' }}
                  />
                </Box>
              </Grid>
              <Grid item xs={12}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <DatePicker
                      label="Start Date"
                      value={universalFilters.startDate}
                      onChange={(newValue) => handleDateChange('startDate', newValue)}
                      slotProps={{ textField: { size: 'small', sx: { width: '100%' } } }}
                    />
                    <DatePicker
                      label="End Date"
                      value={universalFilters.endDate}
                      onChange={(newValue) => handleDateChange('endDate', newValue)}
                      slotProps={{ textField: { size: 'small', sx: { width: '100%' } } }}
                    />
                  </Box>
                </LocalizationProvider>
              </Grid>
            </Grid>
            <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <FilterStatus filters={universalFilters} />
              <Button 
                variant="outlined" 
                startIcon={<ClearIcon />}
                onClick={clearFilters}
                size="small"
              >
                Clear All Filters
              </Button>
            </Box>
          </Paper>

          {tabValue === 0 && (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h5">Transactions</Typography>
                <FormControlLabel
                  control={
                    <Checkbox 
                      checked={loadAllTransactions} 
                      onChange={handleLoadAllTransactions}
                    />
                  }
                  label="Load All Transactions (500 per page)"
                />
              </Box>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <TransactionList 
                    transactions={filteredTransactions} 
                    categories={categories}
                    loading={loading}
                    onTransactionUpdate={handleTransactionUpdate}
                    loadingProgress={loadingProgress}
                  />
                </Grid>
              </Grid>
            </>
          )}

          {tabValue === 1 && (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h5">Transaction Summary</Typography>
              </Box>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <TransactionSummary data={summaryData} activeFilters={universalFilters} bankAccounts={bankAccounts} />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TransactionChart data={summaryData} transactions={filteredTransactions} bankAccounts={bankAccounts} />
                </Grid>
              </Grid>
            </>
          )}

          {tabValue === 2 && (
            <CategoryManager 
              categories={categories} 
              onCategoryUpdate={handleCategoryUpdate} 
            />
          )}

          {tabValue === 3 && (
            <ImportTransactions 
              onImportComplete={handleTransactionUpdate} 
            />
          )}

          {tabValue === 4 && (
            <ApiTest />
          )}
          
          {tabValue === 5 && (
            <>
              <Box sx={{ mb: 3 }}>
                <Button 
                  variant="contained" 
                  color="secondary" 
                  onClick={() => window.runDirectTests && window.runDirectTests()}
                  sx={{ mr: 2 }}
                >
                  Run Direct API Tests
                </Button>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  This button runs direct API tests using both fetch and XMLHttpRequest. 
                  Check your browser console for detailed results.
                </Typography>
              </Box>
              <ApiTestDashboard />
            </>
          )}

          {tabValue === 6 && (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h5">TreeMap Visualization</Typography>
              </Box>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <TransactionTreeMap 
                    data={summaryData} 
                    transactions={filteredTransactions} 
                    summaryData={summaryData}
                  />
                </Grid>
              </Grid>
            </>
          )}
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;
