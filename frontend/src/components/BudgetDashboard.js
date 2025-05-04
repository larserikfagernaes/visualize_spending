import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  LinearProgress,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Paper,
  Skeleton,
  Chip,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  IconButton,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Divider
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import WarningIcon from '@mui/icons-material/Warning';
import SortIcon from '@mui/icons-material/Sort';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import MoneyIcon from '@mui/icons-material/Money';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import { format, parse, getYear, getMonth } from 'date-fns';
import axios from 'axios';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';

// API URL
const API_URL = 'http://localhost:8000/api/v1';

// Create encoded credentials (same as App.js)
const authCredentials = btoa('dev:dev');

const BudgetItem = ({ category, onEditBudget }) => {
  const { name, budget, spent, remaining, percentage } = category;
  
  // Format numbers with proper locale, rounded to nearest whole number
  const formattedBudget = Math.round(budget).toLocaleString('nb-NO');
  const formattedSpent = Math.round(spent).toLocaleString('nb-NO');
  const formattedRemaining = Math.round(Math.abs(remaining)).toLocaleString('nb-NO');
  const isOverBudget = remaining < 0;
  
  // Determine color based on percentage spent
  const getColor = (percent) => {
    if (percent > 100) return '#f44336'; // red for over budget
    if (percent >= 90) return '#ff9800'; // orange/warning for close to budget
    return '#5a9a5a'; // green for others
  };

  // Tooltip text with more details
  const tooltipText = isOverBudget
    ? `Overspent by NOK ${formattedRemaining}`
    : `NOK ${formattedRemaining} remaining`;

  return (
    <Box sx={{ 
      mb: 2, 
      position: 'relative',
      '&:hover .edit-button': {
        opacity: 1
      }
    }}>
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        mb: 0.75
      }}>
        <Tooltip title={tooltipText} placement="right" arrow>
          <Typography component="div" sx={{ 
            fontWeight: 400, 
            fontSize: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: 1
          }}>
            {name}
            {isOverBudget && 
              <WarningIcon 
                fontSize="small" 
                color="error" 
                sx={{ opacity: 0.8 }} 
              />
            }
          </Typography>
        </Tooltip>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Typography component="div" sx={{ fontWeight: 400, fontSize: '1rem' }}>
            NOK {formattedSpent} / {formattedBudget}
          </Typography>
          <IconButton 
            size="small" 
            onClick={() => onEditBudget(category)}
            className="edit-button"
            sx={{ 
              ml: 1, 
              opacity: 0, 
              transition: 'opacity 0.2s',
              '&:hover': { backgroundColor: 'rgba(0,0,0,0.05)' }
            }}
          >
            <EditIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>
      
      <Box sx={{
        display: 'flex', 
        alignItems: 'center',
        mt: 2
      }}>
        <LinearProgress 
          variant="determinate" 
          value={Math.min(Math.round(percentage), 100)} 
          sx={{
            height: 10,
            borderRadius: 5,
            width: '100%',
            backgroundColor: '#e0e0e0',
            '& .MuiLinearProgress-bar': {
              backgroundColor: getColor(percentage),
            }
          }}
        />
      </Box>
    </Box>
  );
};

const CategoryFilterSection = ({ categories, selectedCategories, onCategoryChange, onSelectAll, onClearAll}) => {
  return (
    <Paper sx={{ p: 3, mb: 3, borderRadius: 2, boxShadow: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0 }}>
          <Box component="span" sx={{ 
            backgroundColor: '#1976d2', 
            color: 'white', 
            width: 28, 
            height: 28, 
            borderRadius: '50%', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            fontSize: '0.8rem',
            fontWeight: 'bold'
          }}>
            {categories.length}
          </Box>
          Categories to Display
        </Typography>
        

      </Box>
      
      <Box sx={{ mt: 2 }}>
        <Grid container spacing={1}>
          {categories.map((category) => (
            <Grid item key={category.id}>
              <Chip
                label={category.name}
                clickable
                color={selectedCategories.includes(category.id) ? "primary" : "default"}
                variant={selectedCategories.includes(category.id) ? "filled" : "outlined"}
                onClick={() => onCategoryChange(category.id)}
                sx={{ 
                  fontWeight: selectedCategories.includes(category.id) ? 'bold' : 'normal',
                  transition: 'all 0.2s ease'
                }}
              />
            </Grid>
          ))}
        </Grid>
      </Box>
      
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between' }}>
        <Button 
          size="small" 
          variant="outlined" 
          onClick={onSelectAll}
        >
          Select All
        </Button>
        <Button 
          size="small" 
          variant="outlined" 
          color="secondary"
          onClick={onClearAll}
        >
          Clear All
        </Button>
      </Box>
    </Paper>
  );
};

// Master Budget Indicator component
const MasterBudgetIndicator = ({ budgetData, loading }) => {
  if (loading || !budgetData) {
    return (
      <Box sx={{ mb: 4 }}>
        <Skeleton variant="rectangular" height={100} sx={{ borderRadius: 2, mb: 1 }} />
      </Box>
    );
  }

  const { total_budget, total_spent, total_percentage, total_remaining } = budgetData;
  
  // Format numbers with proper locale, rounded to nearest whole number
  const formattedBudget = Math.round(total_budget).toLocaleString('nb-NO');
  const formattedSpent = Math.round(total_spent).toLocaleString('nb-NO');
  const formattedRemaining = Math.round(Math.abs(total_remaining)).toLocaleString('nb-NO');
  const isOverBudget = total_remaining < 0;
  
  // Determine color based on percentage spent
  const getColor = (percent) => {
    if (percent > 100) return '#f44336'; // red for over budget
    if (percent >= 90) return '#ff9800'; // orange/warning for close to budget
    return '#4caf50'; // green for others
  };
  
  return (
    <Paper 
      elevation={3} 
      sx={{ 
        p: 3, 
        mb: 4, 
        borderRadius: 2,
        background: 'linear-gradient(to right, #f8f9fa, #e3f2fd)'
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <AccountBalanceWalletIcon 
          fontSize="large" 
          color={isOverBudget ? "error" : "primary"} 
          sx={{ mr: 2 }} 
        />
        <Typography variant="h5" fontWeight="bold">
          Total Budget Overview
        </Typography>
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="body1" fontWeight="medium">
          {isOverBudget ? 
            `Overspent by NOK ${formattedRemaining}` : 
            `NOK ${formattedRemaining} remaining`}
        </Typography>
        <Typography variant="body1" fontWeight="medium">
          NOK {formattedSpent} / {formattedBudget}
        </Typography>
      </Box>
      
      <Box sx={{ width: '100%', mb: 1 }}>
        <LinearProgress 
          variant="determinate" 
          value={Math.min(Math.round(total_percentage), 100)} 
          sx={{ 
            height: 20, 
            borderRadius: 2,
            backgroundColor: '#e0e0e0',
            '& .MuiLinearProgress-bar': {
              backgroundColor: getColor(total_percentage),
              borderRadius: 2
            }
          }}
        />
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          {Math.round(total_percentage)}% of budget used
        </Typography>
        <Chip 
          label={isOverBudget ? "Over Budget" : total_percentage >= 90 ? "Near Limit" : "On Track"} 
          color={isOverBudget ? "error" : total_percentage >= 90 ? "warning" : "success"}
          size="small"
          sx={{ fontWeight: 'bold' }}
        />
      </Box>
    </Paper>
  );
};

const BudgetDashboard = () => {
  const [budgetData, setBudgetData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [allCategories, setAllCategories] = useState([]);
  const [salaryCategories, setSalaryCategories] = useState([]);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [currentCategory, setCurrentCategory] = useState(null);
  const [newBudgetAmount, setNewBudgetAmount] = useState('');
  const [selectedMonth, setSelectedMonth] = useState(new Date());
  const [sortOption, setSortOption] = useState('percentage');
  const [showSalaryCategories, setShowSalaryCategories] = useState(false);
  
  // Sort and filter categories
  const getSortedAndFilteredCategories = () => {
    if (!budgetData?.categories) return [];
    
    let filtered = budgetData.categories.filter(
      category => selectedCategories.includes(category.id)
    );
    
    switch (sortOption) {
      case 'name':
        return filtered.sort((a, b) => a.name.localeCompare(b.name));
      case 'budget':
        return filtered.sort((a, b) => b.budget - a.budget);
      case 'spent':
        return filtered.sort((a, b) => b.spent - a.spent);
      case 'percentage':
        return filtered.sort((a, b) => b.percentage - a.percentage);
      default:
        return filtered;
    }
  };
  
  const filteredCategories = getSortedAndFilteredCategories();
  
  // Fetch budget data
  const fetchBudgetData = async () => {
    setLoading(true);
    
    try {
      // Setup request configuration
      const requestConfig = {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Basic ${authCredentials}`
        },
        withCredentials: true
      };
      
      // Add month parameters
      const year = getYear(selectedMonth);
      const month = getMonth(selectedMonth) + 1; // JavaScript months are 0-indexed
      
      // Get all categories without filtering
      const response = await axios.get(
        `${API_URL}/categories/budget/?year=${year}&month=${month}`, 
        requestConfig
      );
      
      if (response.data) {
        setBudgetData(response.data);
        
        // Identify salary categories based on names
        const salaryKeywords = ['salary', 'wage', 'income', 'lønn', 'payroll'];
        
        const salaryRelatedIds = response.data.categories
          .filter(cat => {
            const nameLower = cat.name.toLowerCase();
            return salaryKeywords.some(keyword => nameLower.includes(keyword));
          })
          .map(cat => cat.id);
        
        setSalaryCategories(salaryRelatedIds);
        
        // Set all categories
        if (response.data.categories) {
          setAllCategories(response.data.categories);
          
          // Initialize selected categories if not set yet (excluding salary categories by default)
          if (selectedCategories.length === 0) {
            const nonSalaryCategories = response.data.categories
              .filter(cat => !salaryRelatedIds.includes(cat.id))
              .map(cat => cat.id);
            
            setSelectedCategories(nonSalaryCategories);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching budget data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // Toggle salary categories
  const toggleSalaryCategories = () => {
    if (showSalaryCategories) {
      // Hide salary categories
      setSelectedCategories(prev => prev.filter(id => !salaryCategories.includes(id)));
      setShowSalaryCategories(false);
    } else {
      // Show salary categories
      setSelectedCategories(prev => [...prev, ...salaryCategories]);
      setShowSalaryCategories(true);
    }
  };
  
  // Update category budget
  const updateCategoryBudget = async (categoryId, budgetAmount) => {
    try {
      // Setup request configuration
      const requestConfig = {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Basic ${authCredentials}`
        },
        withCredentials: true
      };
      
      const response = await axios.patch(
        `${API_URL}/categories/${categoryId}/`, 
        { budget: budgetAmount },
        requestConfig
      );
      
      if (response.status === 200) {
        // Refresh budget data
        fetchBudgetData();
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error updating category budget:', error);
      return false;
    }
  };
  
  // Handle edit budget
  const handleEditBudget = (category) => {
    setCurrentCategory(category);
    setNewBudgetAmount(category.budget.toString());
    setEditDialogOpen(true);
  };
  
  // Handle save budget
  const handleSaveBudget = async () => {
    if (currentCategory && !isNaN(parseFloat(newBudgetAmount))) {
      const budgetAmount = parseFloat(newBudgetAmount);
      
      const success = await updateCategoryBudget(
        currentCategory.id, 
        budgetAmount
      );
      
      if (success) {
        setEditDialogOpen(false);
      }
    }
  };
  
  // Handle category selection change
  const handleCategoryChange = (categoryId) => {
    setSelectedCategories(prev => {
      if (prev.includes(categoryId)) {
        return prev.filter(id => id !== categoryId);
      } else {
        return [...prev, categoryId];
      }
    });
    
    // Update salary toggle state if needed
    if (salaryCategories.includes(categoryId)) {
      const allSalarySelected = salaryCategories.every(id => 
        selectedCategories.includes(id) || id === categoryId
      );
      setShowSalaryCategories(allSalarySelected);
    }
  };
  
  // Select all categories
  const handleSelectAllCategories = () => {
    const allCategoryIds = allCategories.map(cat => cat.id);
    setSelectedCategories(allCategoryIds);
    setShowSalaryCategories(true);
  };
  
  // Clear all selected categories
  const handleClearAllCategories = () => {
    setSelectedCategories([]);
    setShowSalaryCategories(false);
  };
  
  // Handle month change
  const handleMonthChange = (newMonth) => {
    setSelectedMonth(newMonth);
  };
  
  // Format month for display
  const formatMonth = (date) => {
    return format(date, 'MMMM yyyy');
  };
  
  // Handle sort option change
  const handleSortChange = (event) => {
    setSortOption(event.target.value);
  };
  
  // Check if a category is a salary category
  const isSalaryCategory = (categoryId) => {
    return salaryCategories.includes(categoryId);
  };
  
  // Fetch budget data on component mount and when selectedMonth changes
  useEffect(() => {
    fetchBudgetData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMonth]);

  return (
    <Box>
      {!loading && allCategories.length > 0 && (
        <Paper sx={{ p: 3, mb: 3, borderRadius: 2, boxShadow: 2 }}>
          <Typography variant="h6" gutterBottom>Category Settings</Typography>
          
          {/* Salary Categories Toggle */}
          {salaryCategories.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Button
                variant={showSalaryCategories ? "contained" : "outlined"}
                color="warning"
                startIcon={<MoneyIcon />}
                onClick={toggleSalaryCategories}
                sx={{ mb: 1 }}
              >
                {showSalaryCategories ? "Hide Salary Categories" : "Show Salary Categories"}
              </Button>
              <Typography variant="caption" color="text.secondary" display="block">
                Salary categories are excluded by default for clearer expense visualization
              </Typography>
            </Box>
          )}
          
          <Divider sx={{ my: 2 }} />
          
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Regular Categories
            </Typography>
            <Grid container spacing={1} sx={{ mb: 2 }}>
              {allCategories
                .filter(cat => !isSalaryCategory(cat.id))
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((category) => {
                  const isSelected = selectedCategories.includes(category.id);
                  
                  return (
                    <Grid item key={category.id}>
                      <Chip
                        label={category.name}
                        clickable
                        color={isSelected ? "primary" : "default"}
                        variant={isSelected ? "filled" : "outlined"}
                        onClick={() => handleCategoryChange(category.id)}
                        sx={{ 
                          fontWeight: isSelected ? 'bold' : 'normal',
                          transition: 'all 0.2s ease',
                        }}
                      />
                    </Grid>
                  );
                })}
            </Grid>
            
            {salaryCategories.length > 0 && (
              <>
                <Typography variant="subtitle2" gutterBottom sx={{ mt: 3, color: 'warning.main' }}>
                  Salary Categories
                </Typography>
                <Grid container spacing={1}>
                  {allCategories
                    .filter(cat => isSalaryCategory(cat.id))
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map((category) => {
                      const isSelected = selectedCategories.includes(category.id);
                      
                      return (
                        <Grid item key={category.id}>
                          <Chip
                            label={category.name}
                            clickable
                            color={isSelected ? "warning" : "default"}
                            variant={isSelected ? "filled" : "outlined"}
                            onClick={() => handleCategoryChange(category.id)}
                            icon={<MoneyIcon />}
                            sx={{ 
                              fontWeight: isSelected ? 'bold' : 'normal',
                              transition: 'all 0.2s ease',
                              borderColor: isSelected ? undefined : 'warning.main',
                              color: isSelected ? undefined : 'warning.main',
                            }}
                          />
                        </Grid>
                      );
                    })}
                </Grid>
              </>
            )}
          </Box>
          
          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button 
              size="small" 
              variant="outlined" 
              onClick={handleSelectAllCategories}
            >
              Select All
            </Button>
            <Button 
              size="small" 
              variant="outlined" 
              color="secondary"
              onClick={handleClearAllCategories}
            >
              Clear All
            </Button>
          </Box>
        </Paper>
      )}
      
      <Paper sx={{ p: 5, mb: 4, borderRadius: 2, boxShadow: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 5 }}>
          <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
            Budget vs. Actual Spending
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel id="sort-select-label">Sort By</InputLabel>
              <Select
                labelId="sort-select-label"
                value={sortOption}
                label="Sort By"
                onChange={handleSortChange}
              >
                <MenuItem value="name">Name</MenuItem>
                <MenuItem value="budget">Budget Amount</MenuItem>
                <MenuItem value="spent">Spent Amount</MenuItem>
                <MenuItem value="percentage">Percentage Used</MenuItem>
              </Select>
            </FormControl>
            
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="Select Month"
                value={selectedMonth}
                onChange={handleMonthChange}
                views={['year', 'month']}
                format="MMMM yyyy"
                slotProps={{ 
                  textField: { 
                    size: "small",
                    sx: { minWidth: '200px' }
                  } 
                }}
              />
            </LocalizationProvider>
          </Box>
        </Box>
        
        {/* Master Budget Indicator */}
        <MasterBudgetIndicator budgetData={budgetData} loading={loading} />
        
        {loading ? (
          <Box>
            <Skeleton variant="rectangular" height={600} sx={{ borderRadius: 2 }} />
          </Box>
        ) : (
          <>
            {filteredCategories.length === 0 ? (
              <Box sx={{ py: 8, textAlign: 'center' }}>
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No budget data available for this period
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Try selecting a different month or add budget categories using the category manager.
                </Typography>
              </Box>
            ) : (
              <Box sx={{ px: 4 }}>
                {filteredCategories.map((category) => (
                  <BudgetItem key={category.id} category={category} onEditBudget={handleEditBudget} />
                ))}
              </Box>
            )}
          </>
        )}
      </Paper>
      
      {/* Edit Budget Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)}>
        <DialogTitle>Edit Budget for {currentCategory?.name}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Budget Amount"
            type="number"
            fullWidth
            variant="outlined"
            value={newBudgetAmount}
            onChange={(e) => setNewBudgetAmount(e.target.value)}
            InputProps={{ 
              inputProps: { min: 0, step: 100 },
              startAdornment: <Box component="span" sx={{ mr: 1 }}>NOK</Box>
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveBudget} variant="contained" color="primary">Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BudgetDashboard; 