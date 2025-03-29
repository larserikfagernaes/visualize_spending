import React, { useState, useMemo, useCallback } from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Grid, 
  FormControl, 
  Select, 
  MenuItem, 
  ToggleButtonGroup, 
  ToggleButton, 
  FormControlLabel, 
  Switch,
  Divider
} from '@mui/material';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
} from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

// Array of month names
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

// Helper function to generate colors
const generateColors = (count) => {
  const colors = [];
  // Generate evenly spaced hues around the color wheel
  const hueStep = 360 / count;
  let hue = 0;
  
  for (let i = 0; i < count; i++) {
    hue = (hue + hueStep) % 360;
    colors.push(`hsl(${hue}, 70%, 60%)`);
  }
  
  return colors;
};

const TransactionChart = ({ data, transactions = [], bankAccounts = [] }) => {
  // State for monthly bank chart
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [chartType, setChartType] = useState('stacked');
  const [showNegativeOnly, setShowNegativeOnly] = useState(false);
  
  // Create memoized mapping of bank account IDs to names
  const bankAccountNameMap = useMemo(() => {
    // Create a fresh mapping object
    const mapping = {};
    
    // First, add all bank accounts from the bankAccounts array
    if (bankAccounts && bankAccounts.length > 0) {
      bankAccounts.forEach(account => {
        if (account.id !== undefined && account.id !== null) {
          // Use the actual name from the bank account directly
          mapping[account.id] = account.name;
        }
      });
    }
    
    // Add any additional bank accounts from transactions that might not be in the bankAccounts array
    if (transactions && transactions.length > 0) {
      const uniqueIds = new Set();
      
      transactions.forEach(transaction => {
        if (transaction.bank_account_id) {
          uniqueIds.add(transaction.bank_account_id);
        }
      });
      
      uniqueIds.forEach(id => {
        if (mapping[id] === undefined) {
          // Special handling for string IDs that are not numeric (like "SP-Tech")
          const isSpecialId = typeof id === 'string' && isNaN(parseInt(id));
          mapping[id] = isSpecialId ? id : `Bank Account ${id}`;
        }
      });
    }
    
    // Add any bank accounts from summary data
    if (data && data.bank_accounts) {
      Object.keys(data.bank_accounts).forEach(id => {
        if (mapping[id] === undefined) {
          // Special handling for string IDs that are not numeric (like "SP-Tech")
          const isSpecialId = typeof id === 'string' && isNaN(parseInt(id));
          mapping[id] = isSpecialId ? id : `Bank Account ${id}`;
        }
      });
    }
    
    console.log("Final bank account mapping:", mapping);
    return mapping;
  }, [transactions, bankAccounts, data]);
  
  // Debug bank accounts data
  console.log('TransactionChart received bankAccounts:', bankAccounts.map(acc => ({ id: acc.id, name: acc.name })));
  
  // Handle year change - moved to top level before any returns
  const handleYearChange = useCallback((event) => {
    setSelectedYear(event.target.value);
  }, []);
  
  // Handle chart type change - moved to top level before any returns
  const handleChartTypeChange = useCallback((event, newType) => {
    if (newType !== null) {
      setChartType(newType);
    }
  }, []);
  
  // ===== Monthly Bank Account Chart =====
  // Derive available years from transactions
  const availableYears = useMemo(() => {
    if (!transactions || transactions.length === 0) {
      // Default to current year if no transactions
      return [new Date().getFullYear()];
    }
    
    // Extract years from transactions
    const years = transactions
      .filter(transaction => transaction.date) // Ensure date exists
      .map(transaction => new Date(transaction.date).getFullYear())
      .filter((year, index, self) => self.indexOf(year) === index)
      .sort((a, b) => b - a); // Sort descending
    
    return years.length > 0 ? years : [new Date().getFullYear()];
  }, [transactions]);
  
  // Filter and process transactions by month and bank account
  const monthlyBankData = useMemo(() => {
    if (!transactions || transactions.length === 0) {
      console.log('No transactions data available');
      return null;
    }
    
    // Debug log for bank accounts
    console.log('Bank accounts available:', bankAccounts);
    
    // Filter transactions for the selected year
    const filteredTransactions = transactions.filter(transaction => {
      // Ensure transaction has a valid date
      if (!transaction.date) return false;
      
      const transactionYear = new Date(transaction.date).getFullYear();
      return transactionYear === selectedYear;
    });
    
    // Log the filtered transactions for debugging
    console.log(`Filtered transactions for year ${selectedYear}:`, filteredTransactions.length);
    
    // If no transactions for selected year, return null early
    if (filteredTransactions.length === 0) {
      return null;
    }
    
    // Filter further if showNegativeOnly is enabled
    const finalFilteredTransactions = showNegativeOnly
      ? filteredTransactions.filter(t => t.amount < 0)
      : filteredTransactions;
    
    // Group by month and bank account
    const monthlyData = {};
    const bankAccountsUsed = new Map(); // Use Map to maintain insertion order and store both ID and name
    
    // Initialize all months to ensure we have data for each month
    MONTHS.forEach((_, index) => {
      monthlyData[index] = {};
    });
    
    // Process each transaction
    finalFilteredTransactions.forEach(transaction => {
      const date = new Date(transaction.date);
      const month = date.getMonth(); // 0-11
      const bankAccountId = transaction.bank_account_id || 'Unknown';
      
      // Use the proper name from the bank account mapping
      const bankAccountName = bankAccountNameMap[bankAccountId] || bankAccountId;
      
      // Store both ID and display name
      bankAccountsUsed.set(bankAccountId, bankAccountName);
      
      const amount = parseFloat(transaction.amount);
      
      // Skip if amount is NaN
      if (isNaN(amount)) return;
      
      // Initialize bank account in monthly data if needed
      if (!monthlyData[month][bankAccountName]) {
        monthlyData[month][bankAccountName] = 0;
      }
      
      // Add amount
      monthlyData[month][bankAccountName] += amount;
    });
    
    // Log the used bank accounts to verify they're correct
    console.log('Bank accounts used in monthly chart:', Object.fromEntries(bankAccountsUsed));
    
    // Convert Map to array of bank account names
    const bankAccountNames = Array.from(bankAccountsUsed.values());
    
    // Prepare data for chart
    const datasets = bankAccountNames.map((bankName, index) => {
      const color = generateColors(bankAccountNames.length)[index];
      
      return {
        label: bankName,
        data: MONTHS.map((_, monthIndex) => 
          Math.abs(monthlyData[monthIndex][bankName] || 0)
        ),
        backgroundColor: color,
        // Use negative for expenses for stacked view
        stack: chartType === 'stacked' ? 'stack1' : bankName,
      };
    });
    
    return {
      labels: MONTHS,
      datasets
    };
  }, [transactions, selectedYear, chartType, showNegativeOnly, bankAccounts, bankAccountNameMap]);
  
  // Prepare data for category pie chart and bar chart
  const categoryData = useMemo(() => {
    if (!data) return { categoryPieData: null, categoryBarData: null };
    
    // Check for existence of required data
    const hasCategories = data.categories && typeof data.categories === 'object' && Object.keys(data.categories).length > 0;
    const hasByCategoryArray = data.by_category && Array.isArray(data.by_category) && data.by_category.length > 0;
    
    let categoryPieData = null;
    let categoryBarData = null;
    
    // Process category data (handle both formats)
    if (hasCategories) {
      const categories = data.categories;
      const categoryNames = Object.keys(categories);
      const categoryTotals = categoryNames.map(name => Math.abs(categories[name].total));
      const categoryColors = generateColors(categoryNames.length);
      
      // Pie chart data
      categoryPieData = {
        labels: categoryNames,
        datasets: [
          {
            data: categoryTotals,
            backgroundColor: categoryColors,
            borderWidth: 1,
          },
        ],
      };

      // Bar chart data - top 5 categories by amount
      const topCategories = [...categoryNames]
        .sort((a, b) => Math.abs(categories[b].total) - Math.abs(categories[a].total))
        .slice(0, 5);
      
      const topCategoryTotals = topCategories.map(name => Math.abs(categories[name].total));

      categoryBarData = {
        labels: topCategories,
        datasets: [
          {
            label: 'Amount',
            data: topCategoryTotals,
            backgroundColor: categoryColors.slice(0, 5),
            borderWidth: 1,
          },
        ],
      };
    } else if (hasByCategoryArray) {
      // Handle by_category array format
      const byCategory = data.by_category;
      const categoryNames = byCategory.map(cat => cat.category);
      const categoryTotals = byCategory.map(cat => Math.abs(cat.total));
      const categoryColors = generateColors(categoryNames.length);
      
      // Pie chart data
      categoryPieData = {
        labels: categoryNames,
        datasets: [
          {
            data: categoryTotals,
            backgroundColor: categoryColors,
            borderWidth: 1,
          },
        ],
      };

      // Bar chart data - top 5 categories by amount
      const topCategories = [...byCategory]
        .sort((a, b) => Math.abs(b.total) - Math.abs(a.total))
        .slice(0, 5);
      
      const topCategoryNames = topCategories.map(cat => cat.category);
      const topCategoryTotals = topCategories.map(cat => Math.abs(cat.total));

      categoryBarData = {
        labels: topCategoryNames,
        datasets: [
          {
            label: 'Amount',
            data: topCategoryTotals,
            backgroundColor: categoryColors.slice(0, 5),
            borderWidth: 1,
          },
        ],
      };
    }
    
    return { categoryPieData, categoryBarData };
  }, [data]);

  // Prepare data for bank account bar chart
  const bankAccountBarData = useMemo(() => {
    if (!data) return null;
    
    const hasBankAccounts = data.bank_accounts && typeof data.bank_accounts === 'object' && Object.keys(data.bank_accounts).length > 0;
    
    if (!hasBankAccounts) return null;
    
    const bankAccountData = data.bank_accounts;
    const accountIds = Object.keys(bankAccountData);
    
    // Filter out any accounts with invalid totals and ensure all values are numbers
    const validAccountIds = accountIds.filter(id => {
      const total = bankAccountData[id]?.total;
      return total !== undefined && total !== null && !isNaN(parseFloat(total));
    });
    
    if (validAccountIds.length === 0) return null;
    
    // Map IDs to names and ensure all values are valid numbers
    const validAccounts = validAccountIds.map(id => {
      const total = bankAccountData[id].total;
      const name = bankAccountNameMap[id] || id;
      return {
        id,
        name,
        total: Math.abs(typeof total === 'number' ? total : parseFloat(total))
      };
    });
    
    // Sort bank accounts by total amount
    const sortedAccounts = validAccounts.sort((a, b) => b.total - a.total);
    const sortedAccountNames = sortedAccounts.map(account => account.name);
    const sortedAccountTotals = sortedAccounts.map(account => account.total);
    
    console.log('Sorted account data:', { 
      sortedAccountNames, 
      sortedAccountTotals,
      rawAccounts: sortedAccounts
    });
    
    const accountColors = generateColors(sortedAccounts.length);
    
    return {
      labels: sortedAccountNames,
      datasets: [
        {
          label: 'Amount',
          data: sortedAccountTotals,
          backgroundColor: accountColors,
          borderWidth: 1,
        },
      ],
    };
  }, [data, bankAccountNameMap]);

  if (!data) return null;
  
  console.log('Chart data received:', data);
  
  // Check for existence of required data
  // We need either categories or by_category data
  const hasCategories = data.categories && typeof data.categories === 'object' && Object.keys(data.categories).length > 0;
  const hasByCategoryArray = data.by_category && Array.isArray(data.by_category) && data.by_category.length > 0;
  const hasBankAccounts = data.bank_accounts && typeof data.bank_accounts === 'object' && Object.keys(data.bank_accounts).length > 0;
  
  // Return message if we don't have visualization data
  if (!hasCategories && !hasByCategoryArray && !hasBankAccounts) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Spending Visualization
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 5 }}>
            No data available for visualization
          </Typography>
        </CardContent>
      </Card>
    );
  }

  // Extract prepared chart data
  const { categoryPieData, categoryBarData } = categoryData;

  // Chart options
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Top Categories by Amount',
      },
    },
  };

  const bankAccountOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Spending by Bank Account',
      },
    },
  };
  
  // Monthly bank chart options
  const monthlyBankOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        stacked: chartType === 'stacked',
      },
      y: {
        stacked: chartType === 'stacked',
        beginAtZero: true,
      },
    },
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: `Monthly Bank Account Summary for ${selectedYear}`,
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += new Intl.NumberFormat('nb-NO', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
              }).format(context.parsed.y);
            }
            return label;
          }
        }
      }
    },
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Spending Visualization
        </Typography>
        
        <Grid container spacing={3}>
          {categoryPieData && (
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle1" gutterBottom align="center">
                Distribution by Category
              </Typography>
              <Box sx={{ height: 300, mb: 4 }}>
                <Pie data={categoryPieData} options={{ maintainAspectRatio: false }} />
              </Box>
            </Grid>
          )}
          
          {categoryBarData && (
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle1" gutterBottom align="center">
                Top 5 Categories
              </Typography>
              <Box sx={{ height: 300, mb: 4 }}>
                <Bar data={categoryBarData} options={chartOptions} />
              </Box>
            </Grid>
          )}
          
          {bankAccountBarData && (
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom align="center">
                Spending by Bank Account
              </Typography>
              <Box sx={{ height: 300, mb: 4 }}>
                <Bar data={bankAccountBarData} options={bankAccountOptions} />
              </Box>
            </Grid>
          )}
          
          {/* Monthly Bank Account Chart */}
          <Grid item xs={12}>
            <Divider sx={{ mb: 3 }} />
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              flexWrap: 'wrap',
              mb: 2 
            }}>
              <Typography variant="subtitle1">
                Monthly Bank Account Summary
              </Typography>
              
              <Box sx={{ 
                display: 'flex', 
                gap: 2, 
                alignItems: 'center',
                flexWrap: 'wrap'
              }}>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <Select
                    value={selectedYear}
                    onChange={handleYearChange}
                    displayEmpty
                  >
                    {availableYears.map(year => (
                      <MenuItem key={year} value={year}>
                        {year}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                
                <ToggleButtonGroup
                  value={chartType}
                  exclusive
                  onChange={handleChartTypeChange}
                  size="small"
                >
                  <ToggleButton value="stacked">
                    Stacked
                  </ToggleButton>
                  <ToggleButton value="grouped">
                    Grouped
                  </ToggleButton>
                </ToggleButtonGroup>
                
                <FormControlLabel
                  control={
                    <Switch 
                      checked={showNegativeOnly}
                      onChange={(e) => setShowNegativeOnly(e.target.checked)}
                      size="small"
                    />
                  }
                  label="Expenses only"
                />
              </Box>
            </Box>
            
            {monthlyBankData ? (
              <Box sx={{ height: 400 }}>
                <Bar data={monthlyBankData} options={monthlyBankOptions} />
              </Box>
            ) : (
              <>
                <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 5 }}>
                  No data available for the selected year
                </Typography>
                <Typography variant="caption" color="text.secondary" align="center" display="block">
                  Try selecting a different year or check that transactions have been imported.
                </Typography>
              </>
            )}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default TransactionChart; 