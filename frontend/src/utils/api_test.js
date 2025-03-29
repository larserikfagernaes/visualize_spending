/**
 * API Test Utility
 * 
 * This file provides utility functions for testing API connectivity
 * that can be run from the browser console or used programmatically.
 */

// API base URL
const API_URL = 'http://localhost:8000/api/v1';

// Available endpoints to test
const ENDPOINTS = [
  { name: 'Bank Accounts', path: '/bank-accounts/' },
  { name: 'Categories', path: '/categories/' },
  { name: 'Transactions', path: '/transactions/' }
];

/**
 * Test a specific API endpoint
 * @param {string} path - The API endpoint path
 * @param {string} name - Display name for the endpoint
 * @returns {Promise<Object>} - The test result
 */
async function testEndpoint(path, name) {
  console.group(`Testing ${name} endpoint`);
  const fullUrl = `${API_URL}${path}`;
  console.log(`URL: ${fullUrl}`);
  
  try {
    // First test CORS OPTIONS request
    try {
      console.log('Testing CORS preflight...');
      console.log('OPTIONS request headers:', {
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'content-type,authorization'
      });
      
      const corsResponse = await fetch(fullUrl, {
        method: 'OPTIONS',
        credentials: 'include',
        headers: {
          'Access-Control-Request-Method': 'GET',
          'Access-Control-Request-Headers': 'content-type,authorization'
        }
      });
      
      console.log('CORS preflight response status:', corsResponse.status);
      console.log('CORS Headers:', {
        'Allow-Origin': corsResponse.headers.get('access-control-allow-origin'),
        'Allow-Credentials': corsResponse.headers.get('access-control-allow-credentials'),
        'Allow-Methods': corsResponse.headers.get('access-control-allow-methods')
      });
      console.log('All response headers:', Object.fromEntries([...corsResponse.headers.entries()]));
      
      console.log('CORS preflight successful ✅');
    } catch (corsError) {
      console.error('CORS preflight failed ❌', corsError);
      console.error('Error type:', corsError.name);
      console.error('Error message:', corsError.message);
      console.error('Error stack:', corsError.stack);
    }
    
    // Now test the actual GET request
    console.log('Sending GET request...');
    console.log('Using credentials: dev:dev');
    console.log('Authorization header:', `Basic ${btoa('dev:dev')}`);
    
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Basic ${btoa('dev:dev')}`
    };
    console.log('Request headers:', headers);
    
    const startTime = performance.now();
    
    const response = await fetch(fullUrl, {
      method: 'GET',
      credentials: 'include',
      headers: headers
    });
    
    const duration = Math.round(performance.now() - startTime);
    
    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries([...response.headers.entries()]));
    
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error(`Authentication error: ${response.status} - ${response.statusText}. Check your credentials.`);
      }
      throw new Error(`HTTP error! Status: ${response.status} - ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Success output
    console.log(`Request successful ✅ (${duration}ms)`, { status: response.status });
    
    // Display result summary
    if (Array.isArray(data)) {
      console.log(`Received ${data.length} items`);
      console.log('Sample items:', data.slice(0, 3));
    } else if (data && typeof data === 'object') {
      if (Array.isArray(data.results)) {
        console.log(`Received ${data.results.length} items (${data.count} total)`);
        console.log('Sample items:', data.results.slice(0, 3));
      } else {
        console.log('Response data:', data);
      }
    }
    
    console.groupEnd();
    return { 
      success: true, 
      name, 
      path, 
      duration,
      data
    };
  } catch (error) {
    console.error(`Request failed ❌: ${error.message}`);
    console.error('Error type:', error.name);
    console.error('Error stack:', error.stack);
    console.groupEnd();
    return { 
      success: false, 
      name, 
      path, 
      error: error.message 
    };
  }
}

/**
 * Test all available API endpoints
 * @returns {Promise<Array>} Test results for all endpoints
 */
async function testAllEndpoints() {
  console.log('%c==== Testing API Connections ====', 'font-weight: bold; font-size: 16px');
  console.log(`API URL: ${API_URL}`);
  
  const results = [];
  
  for (const endpoint of ENDPOINTS) {
    const result = await testEndpoint(endpoint.path, endpoint.name);
    results.push(result);
  }
  
  // Display summary
  const successful = results.filter(r => r.success).length;
  const failed = results.length - successful;
  
  console.log('%c==== Test Summary ====', 'font-weight: bold; font-size: 16px');
  if (successful === results.length) {
    console.log(`%c✅ All tests passed (${successful}/${results.length})`, 'color: green; font-weight: bold');
  } else {
    console.log(`%c⚠️ ${successful}/${results.length} tests passed, ${failed} failed`, 'color: orange; font-weight: bold');
    
    // List failures
    console.log('%cFailed tests:', 'color: red');
    results.filter(r => !r.success).forEach(result => {
      console.log(`- ${result.name}: ${result.error}`);
    });
    
    // Troubleshooting tips
    console.log('%cTroubleshooting Tips:', 'font-weight: bold');
    console.log('1. Check if Django server is running (python3 manage.py runserver)');
    console.log('2. Check CORS settings in Django');
    console.log('3. Check authentication requirements');
    console.log('4. Open browser devtools to see network requests');
  }
  
  return results;
}

// Export functions for use in browser console or imports
window.apiTest = {
  testEndpoint,
  testAllEndpoints,
  API_URL,
  ENDPOINTS
};

export {
  testEndpoint,
  testAllEndpoints,
  API_URL,
  ENDPOINTS
}; 