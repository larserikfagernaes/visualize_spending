import React from 'react';
import { Card, CardContent, Typography, Box, Grid } from '@mui/material';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
} from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
);

const TransactionChart = ({ data }) => {
  if (!data) return null;
  
  // Ensure categories and bank_accounts are objects
  const categories = data.categories && typeof data.categories === 'object' ? data.categories : {};
  const bankAccounts = data.bank_accounts && typeof data.bank_accounts === 'object' ? data.bank_accounts : {};
  
  // Check if categories is empty
  if (Object.keys(categories).length === 0 && Object.keys(bankAccounts).length === 0) {
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

  // Generate colors using golden angle approximation for even distribution
  const generateColors = (count) => {
    const colors = [];
    const hueStep = 137.508; // golden angle approximation
    let hue = 0;
    
    for (let i = 0; i < count; i++) {
      hue = (hue + hueStep) % 360;
      colors.push(`hsl(${hue}, 70%, 60%)`);
    }
    
    return colors;
  };

  // ===== Category Charts =====
  // Prepare data for category pie chart
  let categoryPieData = null;
  let categoryBarData = null;
  
  if (Object.keys(categories).length > 0) {
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
  }

  // ===== Bank Account Charts =====
  // Prepare data for bank account bar chart
  let bankAccountBarData = null;
  
  if (Object.keys(bankAccounts).length > 0) {
    const accountNames = Object.keys(bankAccounts);
    const accountTotals = accountNames.map(name => Math.abs(bankAccounts[name].total));
    const accountColors = generateColors(accountNames.length);
    
    // Sort bank accounts by total amount
    const sortedAccounts = [...accountNames]
      .sort((a, b) => Math.abs(bankAccounts[b].total) - Math.abs(bankAccounts[a].total));
    
    const sortedAccountTotals = sortedAccounts.map(name => Math.abs(bankAccounts[name].total));
    
    bankAccountBarData = {
      labels: sortedAccounts,
      datasets: [
        {
          label: 'Amount',
          data: sortedAccountTotals,
          backgroundColor: accountColors,
          borderWidth: 1,
        },
      ],
    };
  }

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
              <Box sx={{ height: 300 }}>
                <Bar data={bankAccountBarData} options={bankAccountOptions} />
              </Box>
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default TransactionChart; 