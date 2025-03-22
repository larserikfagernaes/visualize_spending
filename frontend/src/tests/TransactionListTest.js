import React from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

/**
 * This is a utility component to test if transactions are loading correctly.
 * It can be imported and used in App.js temporarily to diagnose issues.
 */
const TransactionListTest = () => {
  const [testStatus, setTestStatus] = React.useState('idle');
  const [testResults, setTestResults] = React.useState(null);
  const [error, setError] = React.useState(null);

  const runTest = async () => {
    setTestStatus('running');
    setTestResults(null);
    setError(null);
    
    try {
      // Test 1: Check if API is reachable
      console.log('Test 1: Checking if API is reachable...');
      let apiReachable = false;
      try {
        const response = await axios.get(`${API_URL}/`);
        apiReachable = true;
        console.log('API is reachable:', response.status);
      } catch (err) {
        console.error('API is not reachable:', err);
        apiReachable = false;
      }
      
      // Test 2: Try to fetch first page of transactions
      console.log('Test 2: Fetching first page of transactions...');
      let firstPageData = null;
      let transactionCount = 0;
      try {
        const response = await axios.get(`${API_URL}/transactions/`);
        firstPageData = response.data;
        transactionCount = response.data.count || 0;
        console.log('First page of transactions:', response.data);
      } catch (err) {
        console.error('Failed to fetch first page:', err);
      }
      
      // Test 3: Try to fetch multiple pages if available
      console.log('Test 3: Testing pagination...');
      let allTransactions = [];
      let pagesLoaded = 0;
      let paginationWorks = false;
      
      if (firstPageData && firstPageData.results) {
        allTransactions = [...firstPageData.results];
        pagesLoaded = 1;
        
        // Try to fetch second page if it exists
        if (firstPageData.next) {
          try {
            // Handle the URL - might be absolute or relative
            let nextUrl;
            try {
              const urlObj = new URL(firstPageData.next);
              if (urlObj.protocol && urlObj.host) {
                nextUrl = `${API_URL}${urlObj.pathname}${urlObj.search}`;
              } else {
                nextUrl = firstPageData.next;
              }
            } catch (err) {
              if (firstPageData.next.startsWith('/')) {
                const apiUrlObj = new URL(API_URL);
                nextUrl = `${apiUrlObj.origin}${firstPageData.next}`;
              } else {
                nextUrl = firstPageData.next;
              }
            }
            
            console.log('Fetching second page from:', nextUrl);
            const secondPageResponse = await axios.get(nextUrl);
            
            if (secondPageResponse.data && secondPageResponse.data.results) {
              allTransactions = [...allTransactions, ...secondPageResponse.data.results];
              pagesLoaded = 2;
              paginationWorks = true;
              console.log('Second page loaded successfully');
            }
          } catch (err) {
            console.error('Failed to fetch second page:', err);
          }
        } else {
          console.log('Only one page of results available');
          paginationWorks = true; // Only one page, but pagination technically "works"
        }
      }
      
      // Compile test results
      const results = {
        apiReachable,
        firstPageLoaded: firstPageData !== null,
        transactionCount,
        pagesLoaded,
        paginationWorks,
        totalTransactionsLoaded: allTransactions.length,
      };
      
      setTestResults(results);
      setTestStatus('complete');
      
    } catch (err) {
      console.error('Test failed:', err);
      setError(err.message || 'Unknown error');
      setTestStatus('error');
    }
  };

  return (
    <div style={{ 
      padding: '20px', 
      border: '1px solid #ccc', 
      borderRadius: '4px',
      marginBottom: '20px'
    }}>
      <h2>Transaction Loading Test</h2>
      
      <button 
        onClick={runTest}
        disabled={testStatus === 'running'}
        style={{
          padding: '8px 16px',
          backgroundColor: '#1976d2',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: testStatus === 'running' ? 'not-allowed' : 'pointer'
        }}
      >
        {testStatus === 'running' ? 'Running Test...' : 'Run Test'}
      </button>
      
      {testStatus === 'running' && (
        <p>Running tests, please wait...</p>
      )}
      
      {testStatus === 'error' && (
        <div style={{ color: 'red', marginTop: '10px' }}>
          <p><strong>Error:</strong> {error}</p>
        </div>
      )}
      
      {testStatus === 'complete' && testResults && (
        <div style={{ marginTop: '20px' }}>
          <h3>Test Results</h3>
          <ul style={{ listStyleType: 'none', padding: 0 }}>
            <li style={{ 
              padding: '8px',
              backgroundColor: testResults.apiReachable ? '#e8f5e9' : '#ffebee',
              marginBottom: '4px',
              borderRadius: '4px'
            }}>
              API Reachable: {testResults.apiReachable ? '✅ Yes' : '❌ No'}
            </li>
            <li style={{ 
              padding: '8px',
              backgroundColor: testResults.firstPageLoaded ? '#e8f5e9' : '#ffebee',
              marginBottom: '4px',
              borderRadius: '4px'
            }}>
              First Page Loaded: {testResults.firstPageLoaded ? '✅ Yes' : '❌ No'}
            </li>
            <li style={{ padding: '8px', backgroundColor: '#f5f5f5', marginBottom: '4px', borderRadius: '4px' }}>
              Total Transaction Count: {testResults.transactionCount}
            </li>
            <li style={{ padding: '8px', backgroundColor: '#f5f5f5', marginBottom: '4px', borderRadius: '4px' }}>
              Pages Loaded During Test: {testResults.pagesLoaded}
            </li>
            <li style={{ 
              padding: '8px',
              backgroundColor: testResults.paginationWorks ? '#e8f5e9' : '#ffebee',
              marginBottom: '4px',
              borderRadius: '4px'
            }}>
              Pagination Works: {testResults.paginationWorks ? '✅ Yes' : '❌ No'}
            </li>
            <li style={{ padding: '8px', backgroundColor: '#f5f5f5', marginBottom: '4px', borderRadius: '4px' }}>
              Transactions Loaded During Test: {testResults.totalTransactionsLoaded}
            </li>
          </ul>
          
          <div style={{ marginTop: '20px' }}>
            <p><strong>Diagnosis:</strong></p>
            {!testResults.apiReachable && (
              <p style={{ color: 'red' }}>
                The API is not reachable. Make sure the backend server is running at {API_URL}.
              </p>
            )}
            {testResults.apiReachable && !testResults.firstPageLoaded && (
              <p style={{ color: 'red' }}>
                The API is reachable but could not load transaction data. Check the server logs for errors.
              </p>
            )}
            {testResults.firstPageLoaded && !testResults.paginationWorks && testResults.transactionCount > 100 && (
              <p style={{ color: 'red' }}>
                Could not fetch multiple pages of transactions. This will cause only the first 100 transactions to display.
              </p>
            )}
            {testResults.firstPageLoaded && testResults.paginationWorks && (
              <p style={{ color: 'green' }}>
                Basic transaction loading is working correctly! If you're still having issues, check the browser console for errors.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TransactionListTest; 