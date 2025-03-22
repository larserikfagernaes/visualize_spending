const axios = require('axios');

const API_URL = 'http://localhost:8000/api';

async function testAPI() {
  console.log('Testing API endpoints...');
  
  try {
    // Test 1: API root
    console.log('\n1. Testing API root endpoint...');
    try {
      const rootResponse = await axios.get(API_URL);
      console.log('✅ API root endpoint accessible:', rootResponse.status);
    } catch (error) {
      console.error('❌ API root endpoint error:', error.message);
      if (error.code === 'ECONNREFUSED') {
        console.error('   Make sure the Django server is running on port 8000');
      }
    }
    
    // Test 2: Transactions endpoint
    console.log('\n2. Testing transactions endpoint...');
    try {
      const transactionsResponse = await axios.get(`${API_URL}/transactions/`);
      console.log('✅ Transactions endpoint accessible:', transactionsResponse.status);
      console.log(`   Total transactions: ${transactionsResponse.data.count}`);
      console.log(`   Results per page: ${transactionsResponse.data.results?.length || 0}`);
      
      if (transactionsResponse.data.next) {
        console.log(`   Next page available: ${transactionsResponse.data.next}`);
      } else {
        console.log('   No next page available');
      }
      
      // Print some sample data
      if (transactionsResponse.data.results?.length > 0) {
        console.log('\n   Sample transaction:');
        const sample = transactionsResponse.data.results[0];
        console.log(`     ID: ${sample.id}`);
        console.log(`     Description: ${sample.description}`);
        console.log(`     Amount: ${sample.amount}`);
        console.log(`     Date: ${sample.date}`);
        console.log(`     Bank Account: ${sample.bank_account_id}`);
        console.log(`     Account ID: ${sample.account_id}`);
      }
    } catch (error) {
      console.error('❌ Transactions endpoint error:', error.message);
      if (error.response) {
        console.error('   Response status:', error.response.status);
        console.error('   Response data:', error.response.data);
      }
    }
    
    // Test 3: Categories endpoint
    console.log('\n3. Testing categories endpoint...');
    try {
      const categoriesResponse = await axios.get(`${API_URL}/categories/`);
      console.log('✅ Categories endpoint accessible:', categoriesResponse.status);
      console.log(`   Total categories: ${categoriesResponse.data.length}`);
      
      // Print some sample data
      if (categoriesResponse.data.length > 0) {
        console.log('\n   Sample categories:');
        categoriesResponse.data.slice(0, 3).forEach(category => {
          console.log(`     - ${category.name}`);
        });
      }
    } catch (error) {
      console.error('❌ Categories endpoint error:', error.message);
      if (error.response) {
        console.error('   Response status:', error.response.status);
        console.error('   Response data:', error.response.data);
      }
    }
    
    // Test 4: Try transaction pagination
    console.log('\n4. Testing transaction pagination...');
    try {
      let page = 1;
      let nextUrl = `${API_URL}/transactions/`;
      let totalLoaded = 0;
      
      while (nextUrl && page <= 3) { // Limit to first 3 pages for the test
        const response = await axios.get(nextUrl);
        const pageCount = response.data.results?.length || 0;
        totalLoaded += pageCount;
        
        console.log(`✅ Page ${page} loaded: ${pageCount} transactions`);
        
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
          console.log(`   Next URL: ${nextUrl}`);
          page++;
        } else {
          console.log('   No more pages available');
          nextUrl = null;
        }
      }
      
      console.log(`   Total transactions loaded: ${totalLoaded}`);
      
    } catch (error) {
      console.error('❌ Pagination test error:', error.message);
    }
    
  } catch (error) {
    console.error('General error:', error.message);
  }
}

// Run the tests
testAPI(); 