/**
 * Direct API Connection Test
 * 
 * This script tests the API connection using different methods
 * to diagnose potential issues with CORS or authentication.
 */

const API_URL = 'http://localhost:8000/api/v1';
const AUTH_CREDENTIALS = 'dev:dev';
const ENCODED_AUTH = btoa(AUTH_CREDENTIALS);

/**
 * Test API connection using fetch API
 */
async function testWithFetch() {
  console.group('Testing API connection with fetch API');
  console.log('API URL:', API_URL);
  console.log('Auth credentials:', AUTH_CREDENTIALS);
  
  const endpoints = [
    { name: 'Bank Accounts', path: '/bank-accounts/' },
    { name: 'Categories', path: '/categories/' },
    { name: 'Transactions', path: '/transactions/' }
  ];
  
  // First test the OPTIONS/preflight request to one endpoint
  try {
    const preflightUrl = `${API_URL}${endpoints[0].path}`;
    console.log('Testing CORS preflight OPTIONS request to:', preflightUrl);
    
    const preflightResponse = await fetch(preflightUrl, {
      method: 'OPTIONS',
      mode: 'cors',
      credentials: 'include',
      headers: {
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'content-type,authorization',
        'Origin': window.location.origin
      }
    });
    
    console.log('Preflight Response status:', preflightResponse.status);
    console.log('Preflight Headers:', Object.fromEntries([...preflightResponse.headers.entries()]));
    console.log('CORS preflight successful ✅');
  } catch (preflightError) {
    console.error('CORS preflight failed ❌', preflightError);
  }
  
  for (const endpoint of endpoints) {
    console.group(`Testing ${endpoint.name} endpoint`);
    const url = `${API_URL}${endpoint.path}`;
    
    try {
      console.log('Sending request to:', url);
      console.log('Authorization:', `Basic ${ENCODED_AUTH}`);
      console.log('Origin:', window.location.origin);
      
      const response = await fetch(url, {
        method: 'GET',
        mode: 'cors',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Basic ${ENCODED_AUTH}`,
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      
      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries([...response.headers.entries()]));
      
      if (response.ok) {
        const data = await response.json();
        console.log('Response data:', data);
        console.log('Test successful ✅');
      } else {
        console.error('HTTP error:', response.status, response.statusText);
        console.log('Test failed ❌');
      }
    } catch (error) {
      console.error('Error:', error.message);
      if (error.message && error.message.includes('CORS')) {
        console.error('This appears to be a CORS issue. Check CORS settings in Django.');
      }
      console.log('Test failed ❌');
    }
    
    console.groupEnd();
  }
  
  console.groupEnd();
}

/**
 * Test API connection using XMLHttpRequest
 */
function testWithXHR() {
  console.group('Testing API connection with XMLHttpRequest');
  console.log('API URL:', API_URL);
  console.log('Auth credentials:', AUTH_CREDENTIALS);
  
  const endpoints = [
    { name: 'Bank Accounts', path: '/bank-accounts/' },
    { name: 'Categories', path: '/categories/' },
    { name: 'Transactions', path: '/transactions/' }
  ];
  
  endpoints.forEach(endpoint => {
    console.group(`Testing ${endpoint.name} endpoint`);
    const url = `${API_URL}${endpoint.path}`;
    
    const xhr = new XMLHttpRequest();
    xhr.withCredentials = true;
    
    xhr.onreadystatechange = function() {
      if (xhr.readyState === 4) {
        console.log('Response status:', xhr.status);
        console.log('Response headers:', xhr.getAllResponseHeaders());
        
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            console.log('Response data:', data);
            console.log('Test successful ✅');
          } catch (e) {
            console.error('Error parsing response:', e);
            console.log('Test failed ❌');
          }
        } else {
          console.error('HTTP error:', xhr.status, xhr.statusText);
          console.log('Test failed ❌');
        }
      }
    };
    
    xhr.onerror = function(e) {
      console.error('Network error occurred:', e);
      console.error('This may be a CORS issue. Check CORS settings in Django.');
      console.log('Test failed ❌');
    };
    
    console.log('Sending request to:', url);
    console.log('Authorization:', `Basic ${ENCODED_AUTH}`);
    console.log('Origin:', window.location.origin);
    
    xhr.open('GET', url, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('Authorization', `Basic ${ENCODED_AUTH}`);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.send();
    
    console.groupEnd();
  });
  
  console.groupEnd();
}

// Run the tests
export function runDirectTests() {
  console.log('%c==== Direct API Connection Tests ====', 'font-weight: bold; font-size: 16px');
  console.log('Running from origin:', window.location.origin);
  
  testWithFetch();
  
  // Run XHR test after a short delay to avoid console clutter
  setTimeout(() => {
    testWithXHR();
  }, 1000);
}

// Make it available in the browser console
window.runDirectTests = runDirectTests;

// Auto-run tests when the file is loaded
setTimeout(runDirectTests, 500);

export default { runDirectTests }; 