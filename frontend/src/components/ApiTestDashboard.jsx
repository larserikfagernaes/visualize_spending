import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Button, 
  Divider, 
  List, 
  ListItem, 
  ListItemText,
  ListItemIcon,
  Chip,
  Grid,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import { 
  CheckCircle as CheckIcon, 
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  DataObject as DataIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';

import { testAllEndpoints, testEndpoint, ENDPOINTS } from '../utils/api_test';

const ApiTestDashboard = () => {
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState(null);

  const runAllTests = async () => {
    setIsLoading(true);
    try {
      const testResults = await testAllEndpoints();
      setResults(testResults);
      
      // Calculate summary
      const successful = testResults.filter(r => r.success).length;
      const failed = testResults.length - successful;
      setSummary({
        total: testResults.length,
        successful,
        failed
      });
    } catch (error) {
      console.error('Test error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const runSingleTest = async (endpoint) => {
    setIsLoading(true);
    try {
      const result = await testEndpoint(endpoint.path, endpoint.name);
      
      // Update results by replacing the existing entry or adding a new one
      setResults(prevResults => {
        const index = prevResults.findIndex(r => r.path === endpoint.path);
        if (index >= 0) {
          return [
            ...prevResults.slice(0, index),
            result,
            ...prevResults.slice(index + 1)
          ];
        } else {
          return [...prevResults, result];
        }
      });
      
      // Update summary
      if (results.length > 0) {
        const successful = [...results.filter(r => r.success && r.path !== endpoint.path), result.success ? result : null].filter(Boolean).length;
        const total = results.length;
        setSummary({
          total,
          successful,
          failed: total - successful
        });
      }
      
      return result;
    } catch (error) {
      console.error('Test error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        API Connection Test Dashboard
      </Typography>
      
      <Typography variant="body1" color="text.secondary" paragraph>
        This dashboard helps you test connectivity between the frontend and backend API endpoints.
        Use these tests to diagnose connection problems or verify that your setup is working correctly.
      </Typography>
      
      <Box sx={{ mb: 4, display: 'flex', gap: 2 }}>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={runAllTests}
          disabled={isLoading}
        >
          {isLoading ? <CircularProgress size={24} sx={{ mr: 1 }} /> : null}
          Test All Endpoints
        </Button>
      </Box>
      
      {summary && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>Test Summary</Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Chip 
              label={`Total: ${summary.total}`} 
              color="default" 
              variant="outlined" 
            />
            <Chip 
              label={`Passed: ${summary.successful}`} 
              color="success" 
              variant={summary.successful > 0 ? "default" : "outlined"} 
              icon={<CheckIcon />} 
            />
            <Chip 
              label={`Failed: ${summary.failed}`} 
              color="error" 
              variant={summary.failed > 0 ? "default" : "outlined"} 
              icon={<ErrorIcon />} 
            />
          </Box>
          
          {summary.failed > 0 && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Some tests failed. Check the details below for more information.
            </Alert>
          )}
          
          {summary.successful === summary.total && (
            <Alert severity="success" sx={{ mt: 2 }}>
              All tests passed! Your API connection is working correctly.
            </Alert>
          )}
        </Paper>
      )}
      
      {summary && summary.failed > 0 && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: 'info.light' }}>
          <Typography variant="h6" gutterBottom>Troubleshooting Tips</Typography>
          <List>
            <ListItem>
              <ListItemIcon>
                <ScheduleIcon />
              </ListItemIcon>
              <ListItemText 
                primary="Backend Server Not Running" 
                secondary="Make sure the Django server is running with: python3 manage.py runserver" 
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <ScheduleIcon />
              </ListItemIcon>
              <ListItemText 
                primary="CORS Configuration Issue" 
                secondary="Check CORS_ALLOWED_ORIGINS and CORS_ALLOW_CREDENTIALS in Django settings" 
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <ScheduleIcon />
              </ListItemIcon>
              <ListItemText 
                primary="Authentication Required" 
                secondary="Verify if API endpoints require authentication" 
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <ScheduleIcon />
              </ListItemIcon>
              <ListItemText 
                primary="Network/Firewall Issues" 
                secondary="Ensure ports 8000 (backend) and 3000 (frontend) are accessible" 
              />
            </ListItem>
          </List>
        </Paper>
      )}
      
      <Grid container spacing={2}>
        {ENDPOINTS.map((endpoint) => {
          const result = results.find(r => r.path === endpoint.path);
          
          return (
            <Grid item xs={12} md={6} lg={4} key={endpoint.path}>
              <Paper sx={{ p: 2, height: '100%' }}>
                <Typography variant="h6" gutterBottom>{endpoint.name}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Endpoint: <code>{endpoint.path}</code>
                </Typography>
                
                <Button 
                  variant="outlined" 
                  size="small" 
                  onClick={() => runSingleTest(endpoint)}
                  disabled={isLoading}
                  sx={{ mb: 2 }}
                >
                  Test Endpoint
                </Button>
                
                {result && (
                  <Box sx={{ mt: 2 }}>
                    <Divider sx={{ my: 2 }} />
                    
                    <Box sx={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      mb: 1,
                      color: result.success ? 'success.main' : 'error.main'
                    }}>
                      {result.success ? <CheckIcon color="success" /> : <ErrorIcon color="error" />}
                      <Typography variant="body1" sx={{ ml: 1, fontWeight: 'bold' }}>
                        {result.success ? 'Success' : 'Failed'}
                      </Typography>
                      
                      {result.duration && (
                        <Chip 
                          size="small" 
                          icon={<ScheduleIcon />} 
                          label={`${result.duration}ms`} 
                          variant="outlined"
                          sx={{ ml: 'auto' }}
                        />
                      )}
                    </Box>
                    
                    {!result.success && (
                      <Alert severity="error" sx={{ mb: 2 }}>
                        {result.error}
                      </Alert>
                    )}
                    
                    {result.success && result.data && (
                      <Accordion>
                        <AccordionSummary
                          expandIcon={<ExpandMoreIcon />}
                          aria-controls="response-data-content"
                          id="response-data-header"
                        >
                          <DataIcon sx={{ mr: 1 }} />
                          <Typography>
                            {Array.isArray(result.data) 
                              ? `${result.data.length} items` 
                              : Array.isArray(result.data.results)
                                ? `${result.data.results.length} items (of ${result.data.count})`
                                : 'Response Data'}
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          {Array.isArray(result.data) && result.data.length > 0 && (
                            <List dense>
                              {result.data.slice(0, 5).map((item, index) => (
                                <ListItem key={item.id || index}>
                                  <ListItemText
                                    primary={item.name || item.description || `Item ${index + 1}`}
                                    secondary={
                                      item.id 
                                        ? `ID: ${item.id}` 
                                        : null
                                    }
                                  />
                                </ListItem>
                              ))}
                              {result.data.length > 5 && (
                                <ListItem>
                                  <ListItemText
                                    primary={`... and ${result.data.length - 5} more items`}
                                  />
                                </ListItem>
                              )}
                            </List>
                          )}
                          
                          {result.data && result.data.results && (
                            <List dense>
                              {result.data.results.slice(0, 5).map((item, index) => (
                                <ListItem key={item.id || index}>
                                  <ListItemText
                                    primary={item.name || item.description || `Item ${index + 1}`}
                                    secondary={
                                      item.id 
                                        ? `ID: ${item.id}` 
                                        : null
                                    }
                                  />
                                </ListItem>
                              ))}
                              {result.data.results.length > 5 && (
                                <ListItem>
                                  <ListItemText
                                    primary={`... and ${result.data.results.length - 5} more items`}
                                  />
                                </ListItem>
                              )}
                            </List>
                          )}
                          
                          {(!Array.isArray(result.data) && !result.data.results) && (
                            <Typography variant="body2" component="pre" sx={{ 
                              whiteSpace: 'pre-wrap', 
                              bgcolor: 'grey.50',
                              p: 1,
                              borderRadius: 1
                            }}>
                              {JSON.stringify(result.data, null, 2)}
                            </Typography>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    )}
                  </Box>
                )}
                
                {!result && !isLoading && (
                  <Typography variant="body2" color="text.secondary">
                    No test has been run yet.
                  </Typography>
                )}
                
                {isLoading && !result && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={20} />
                    <Typography variant="body2">Testing...</Typography>
                  </Box>
                )}
              </Paper>
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
};

export default ApiTestDashboard; 