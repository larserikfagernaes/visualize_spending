#!/usr/bin/env node

// Simple Node.js script to test backend API connections
const axios = require('axios');
const colors = require('colors/safe');

// Configuration
const API_URL = 'http://localhost:8000/api/v1';
const endpoints = [
  { name: 'Bank Accounts', path: '/bank-accounts/' },
  { name: 'Categories', path: '/categories/' },
  { name: 'Transactions', path: '/transactions/' }
];

// Basic auth for development
const authConfig = {
  auth: {
    username: 'dev',
    password: 'dev'
  },
  withCredentials: true
};

// Helper function to format response data for display
function formatResponseSummary(data) {
  if (Array.isArray(data)) {
    return `${data.length} items received`;
  } else if (data && typeof data === 'object' && data.results) {
    return `${data.results.length} items received (${data.count} total)`;
  } else {
    return 'Response data structure unknown';
  }
}

// Helper function to format item display
function formatItemDisplay(item) {
  if (!item) return 'N/A';
  
  if (item.name) {
    return `${item.name}${item.id ? ` (ID: ${item.id})` : ''}`;
  } else if (item.description) {
    return `${item.description.slice(0, 30)}...${item.id ? ` (ID: ${item.id})` : ''}`;
  } else {
    return JSON.stringify(item).slice(0, 50) + '...';
  }
}

// Test an endpoint and show response
async function testEndpoint(name, path) {
  console.log(`\n${colors.cyan('Testing:')} ${colors.yellow(name)} - ${API_URL}${path}`);
  
  try {
    console.log(colors.gray('Sending request...'));
    
    // First make an OPTIONS request to check CORS
    try {
      const corsResponse = await axios({
        method: 'OPTIONS',
        url: `${API_URL}${path}`,
        ...authConfig
      });
      
      console.log(colors.green('✓ CORS preflight successful'));
      console.log(colors.gray('CORS Headers:'));
      console.log(colors.gray('  Access-Control-Allow-Origin:'), 
        corsResponse.headers['access-control-allow-origin'] || 'Not set');
      console.log(colors.gray('  Access-Control-Allow-Credentials:'), 
        corsResponse.headers['access-control-allow-credentials'] || 'Not set');
      console.log(colors.gray('  Access-Control-Allow-Methods:'), 
        corsResponse.headers['access-control-allow-methods'] || 'Not set');
    } catch (corsError) {
      console.log(colors.red('✗ CORS preflight failed:'), corsError.message);
    }
    
    // Then make the actual GET request
    const startTime = Date.now();
    const response = await axios.get(`${API_URL}${path}`, authConfig);
    const duration = Date.now() - startTime;
    
    console.log(colors.green(`✓ Success (${duration}ms): ${response.status} ${response.statusText}`));
    console.log(colors.gray('Response summary:'), formatResponseSummary(response.data));
    
    // Display some items from the response
    if (Array.isArray(response.data) && response.data.length > 0) {
      console.log(colors.gray('Sample items:'));
      response.data.slice(0, 3).forEach((item, index) => {
        console.log(`  ${index + 1}. ${formatItemDisplay(item)}`);
      });
    } else if (response.data && Array.isArray(response.data.results) && response.data.results.length > 0) {
      console.log(colors.gray('Sample items:'));
      response.data.results.slice(0, 3).forEach((item, index) => {
        console.log(`  ${index + 1}. ${formatItemDisplay(item)}`);
      });
    }
    
    return { success: true, name, path };
  } catch (error) {
    console.log(colors.red(`✗ Error: ${error.message}`));
    
    if (error.response) {
      // The request was made and the server responded with a status code
      // outside the range of 2xx
      console.log(colors.red(`  Status: ${error.response.status}`));
      console.log(colors.red(`  Response: ${JSON.stringify(error.response.data, null, 2).slice(0, 200)}...`));
    } else if (error.request) {
      // The request was made but no response was received
      console.log(colors.red('  No response received'));
      console.log(colors.yellow('  Check if your backend server is running'));
    } else {
      // Something happened in setting up the request
      console.log(colors.red(`  Error setting up request: ${error.message}`));
    }
    
    return { success: false, name, path, error: error.message };
  }
}

// Main function to run all tests
async function runTests() {
  console.log(colors.bold.white('\n===== API Connection Test ====='));
  console.log(colors.gray(`Testing API at: ${API_URL}`));
  
  const results = [];
  
  // Test each endpoint
  for (const endpoint of endpoints) {
    const result = await testEndpoint(endpoint.name, endpoint.path);
    results.push(result);
  }
  
  // Show summary
  console.log(colors.bold.white('\n===== Test Summary ====='));
  const successful = results.filter(r => r.success).length;
  const failed = results.length - successful;
  
  console.log(colors.bold(
    successful === results.length
      ? colors.green(`All tests passed (${successful}/${results.length})`)
      : colors.yellow(`${successful}/${results.length} tests passed, ${failed} failed`)
  ));
  
  // List any failures
  if (failed > 0) {
    console.log(colors.red('\nFailed tests:'));
    results.filter(r => !r.success).forEach(result => {
      console.log(colors.red(`  - ${result.name}: ${result.error}`));
    });
    
    // Troubleshooting tips
    console.log(colors.yellow('\nTroubleshooting tips:'));
    console.log(colors.yellow('1. Check if the Django server is running with: python3 manage.py runserver'));
    console.log(colors.yellow('2. Ensure CORS is properly configured in Django settings'));
    console.log(colors.yellow('3. Check your Django permission settings (if using authentication)'));
    console.log(colors.yellow('4. Verify that port 8000 is not blocked by a firewall'));
  }
}

// Run the tests
runTests().catch(err => {
  console.error(colors.red('Test script failed:'), err);
}); 