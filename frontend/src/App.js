import React, { useState, useEffect } from 'react';
import { Container, Box, Tabs, Tab, AppBar, Typography, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import axios from 'axios';

// Import components
import TransactionList from './components/TransactionList';
import TransactionSummary from './components/TransactionSummary';
import TransactionChart from './components/TransactionChart';
import CategoryManager from './components/CategoryManager';
import ImportTransactions from './components/ImportTransactions';
import TransactionListTest from './tests/TransactionListTest';

// API URL
const API_URL = 'http://localhost:8000/api';

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

function App() {
  // State
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [summaryData, setSummaryData] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState({
    loaded: 0,
    total: 0,
    page: 0
  });

  // Fetch transactions
  const fetchTransactions = async () => {
    setLoading(true);
    setLoadingProgress({ loaded: 0, total: 0, page: 0 });
    
    try {
      // Initialize variables for pagination
      let allTransactions = [];
      let nextUrl = `${API_URL}/transactions/`;
      let pageCount = 0;
      let totalCount = 0;
      
      // Loop until we've fetched all pages
      while (nextUrl) {
        pageCount++;
        console.log(`Fetching transactions page ${pageCount} from: ${nextUrl}`);
        
        // Fetch the current page
        const response = await axios.get(nextUrl);
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
    };
    
    loadInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch categories
  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_URL}/categories/`);
      setCategories(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Error fetching categories:', error);
      setCategories([]);
    }
  };

  // Fetch summary data
  const fetchSummary = async () => {
    try {
      const response = await axios.get(`${API_URL}/transactions/summary/`);
      console.log('Summary API response:', response.data);
      setSummaryData(response.data || null);
    } catch (error) {
      console.error('Error fetching summary:', error);
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
  };

  // Handle category update
  const handleCategoryUpdate = () => {
    fetchCategories();
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="lg">
        <Box sx={{ my: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Finance Visualizer
          </Typography>
          
          <AppBar position="static" color="default" sx={{ mt: 3 }}>
            <Tabs
              value={tabValue}
              onChange={handleTabChange}
              indicatorColor="primary"
              textColor="primary"
              variant="fullWidth"
            >
              <Tab label="Transactions" />
              <Tab label="Summary" />
              <Tab label="Categories" />
            </Tabs>
          </AppBar>
          
          {/* Transactions Tab */}
          {tabValue === 0 && (
            <Box sx={{ mt: 3 }}>
              <TransactionListTest />
              <ImportTransactions onImport={handleTransactionUpdate} />
              <TransactionList 
                transactions={transactions} 
                categories={categories} 
                onUpdate={handleTransactionUpdate}
                loading={loading}
                loadingProgress={loadingProgress}
              />
            </Box>
          )}
          
          {/* Summary Tab */}
          {tabValue === 1 && (
            <Box sx={{ mt: 3 }}>
              <Box sx={{ mb: 3 }}>
                <TransactionSummary data={summaryData} />
              </Box>
              <Box>
                <TransactionChart data={summaryData} />
              </Box>
            </Box>
          )}
          
          {/* Categories Tab */}
          {tabValue === 2 && (
            <Box sx={{ mt: 3 }}>
              <CategoryManager 
                categories={categories} 
                onUpdate={handleCategoryUpdate} 
              />
            </Box>
          )}
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;
