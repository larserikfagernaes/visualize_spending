import React, { useState, useMemo, useCallback } from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  CircularProgress,
  Alert,
  Paper,
  Button
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { ResponsiveContainer, Treemap, Tooltip } from 'recharts';

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

const CustomTooltip = ({ active, payload, totalValue }) => {
  if (active && payload && payload.length > 0) {
    const data = payload[0].payload;
    const percentage = totalValue > 0 ? ((data.value / totalValue) * 100).toFixed(1) : 0;
    
    return (
      <Paper elevation={3} sx={{ p: 1, backgroundColor: 'rgba(255, 255, 255, 0.9)' }}>
        <Typography variant="subtitle2">{data.name}</Typography>
        <Typography variant="body2">Amount: {Math.abs(data.value).toFixed(2)}</Typography>
        <Typography variant="body2">Percentage: {percentage}%</Typography>
        {data.count && (
          <Typography variant="body2">Transactions: {data.count}</Typography>
        )}
      </Paper>
    );
  }
  return null;
};

const TransactionTreeMap = ({ data, transactions, summaryData }) => {
  // State to track selected category for drilling down
  const [selectedCategory, setSelectedCategory] = useState(null);
  
  // Define account numbers to exclude
  const excludedAccountNumbers = useMemo(() => ['232', '208', '1921', '8160', '1926'], []);
  
  // Prepare data for category treemap
  const categoryTreemapData = useMemo(() => {
    if (!summaryData || !summaryData.categories) return [];
    
    const categories = summaryData.categories;
    const categoryNames = Object.keys(categories);
    
    if (categoryNames.length === 0) return [];
    
    return categoryNames.map(name => ({
      name,
      value: Math.abs(categories[name].total),
      count: categories[name].count,
      children: []
    }));
  }, [summaryData]);
  
  // Prepare data for accounts within a category
  const accountsTreemapData = useMemo(() => {
    if (!selectedCategory || !transactions || transactions.length === 0) return [];
    
    // Filter transactions by selected category
    const categoryTransactions = transactions.filter(t => 
      t.category_name === selectedCategory
    );
    
    // Group by account and aggregate amounts
    const accountMap = {};
    
    categoryTransactions.forEach(transaction => {
      if (transaction.related_accounts && transaction.related_accounts.length > 0) {
        transaction.related_accounts.forEach(account => {
          // Skip excluded account numbers
          const accountNumber = account.account_number?.toString();
          const accountId = account.id?.toString();
          
          if (
            excludedAccountNumbers.includes(accountNumber) || 
            excludedAccountNumbers.includes(accountId)
          ) {
            return; // Skip this account
          }
          
          const accountName = account.name || account.account_number || `Account ${account.id}`;
          
          if (!accountMap[accountName]) {
            accountMap[accountName] = {
              name: accountName,
              value: 0,
              count: 0
            };
          }
          
          // Use the account-specific amount if available, otherwise use transaction amount
          const amount = account.amount ? Math.abs(parseFloat(account.amount)) : Math.abs(parseFloat(transaction.amount));
          accountMap[accountName].value += amount;
          accountMap[accountName].count += 1;
        });
      }
    });
    
    return Object.values(accountMap);
  }, [selectedCategory, transactions, excludedAccountNumbers]);

  // Handle treemap item click for drill down
  const handleTreemapClick = useCallback((data) => {
    if (!selectedCategory) {
      // First level click - drill down to account level
      setSelectedCategory(data.name);
    } else {
      // Second level click - go back to category view
      setSelectedCategory(null);
    }
  }, [selectedCategory]);
  
  // Determine which data to display based on selection
  const treemapData = useMemo(() => {
    if (selectedCategory) {
      return accountsTreemapData;
    } else {
      return categoryTreemapData;
    }
  }, [selectedCategory, categoryTreemapData, accountsTreemapData]);
  
  // Set colors based on data size
  const colors = useMemo(() => {
    return generateColors(treemapData.length || 1);
  }, [treemapData]);
  
  // Calculate total value for the current view
  const totalValue = useMemo(() => {
    if (selectedCategory) {
      // For account view - sum of all account values for the selected category
      return accountsTreemapData.reduce((sum, item) => sum + item.value, 0);
    } else {
      // For category view - total spending across all categories
      return categoryTreemapData.reduce((sum, item) => sum + item.value, 0);
    }
  }, [selectedCategory, categoryTreemapData, accountsTreemapData]);
  
  if (!summaryData) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    );
  }
  
  if (treemapData.length === 0) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
            <Alert severity="info">
              No data available{selectedCategory ? ` for category "${selectedCategory}"` : ''}
            </Alert>
          </Box>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {selectedCategory && (
              <Button 
                variant="outlined" 
                startIcon={<ArrowBackIcon />}
                onClick={() => setSelectedCategory(null)}
                size="small"
              >
                Back to Categories
              </Button>
            )}
            <Typography variant="h6" sx={{ ml: selectedCategory ? 2 : 0 }}>
              {selectedCategory 
                ? `Accounts for "${selectedCategory}"`
                : 'Transaction Categories (Click to view accounts)'}
            </Typography>
          </Box>
        </Box>
        
        <Box sx={{ height: 500 }}>
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={treemapData}
              dataKey="value"
              nameKey="name"
              onClick={handleTreemapClick}
              fill="#8884d8"
              isAnimationActive={false}
              content={
                ({ x, y, width, height, index, name, value }) => {
                  const colorIndex = index % colors.length;
                  const color = colors[colorIndex];
                  
                  // Skip rendering if the rectangle is too small
                  if (width < 20 || height < 20) return null;
                  
                  return (
                    <g>
                      <rect
                        x={x}
                        y={y}
                        width={width}
                        height={height}
                        style={{
                          fill: color,
                          stroke: '#fff',
                          strokeWidth: 2,
                          cursor: 'pointer'
                        }}
                      />
                      {width > 50 && height > 30 ? (
                        <text
                          x={x + width / 2}
                          y={y + height / 2}
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fill="#fff"
                          fontSize={width > 100 ? 14 : 10}
                          stroke="none"
                          style={{
                            pointerEvents: 'none',
                            userSelect: 'none'
                          }}
                        >
                          {name}
                        </text>
                      ) : null}
                    </g>
                  );
                }
              }
            >
              <Tooltip content={<CustomTooltip totalValue={totalValue} />} />
            </Treemap>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TransactionTreeMap; 