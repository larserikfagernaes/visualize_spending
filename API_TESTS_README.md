# API Testing Utilities

This directory contains utilities for testing the API connectivity between the frontend and backend.

## Command-Line Test Script

The `test_api_connection.js` script is a Node.js utility that can be run from the command line to verify connectivity to the backend API. It tests CORS preflight requests and actual data retrieval.

### Prerequisites

1. Make sure the backend server is running:
   ```bash
   cd backend
   python3 manage.py runserver
   ```

2. Install the required Node.js dependencies:
   ```bash
   npm install
   ```

### Running the test

```bash
npm test
# or 
node test_api_connection.js
```

The script will test connectivity to all configured API endpoints and provide detailed information about any issues encountered.

## Browser Console Test Utility

The `frontend/src/utils/api_test.js` file provides testing utilities that can be used directly in the browser console. This is useful for diagnosing issues while the application is running.

### Using in the browser console

1. Make sure the frontend application is running
2. Open your browser's developer tools (F12)
3. In the console, run:

```javascript
// Test all endpoints
apiTest.testAllEndpoints();

// Or test a specific endpoint
apiTest.testEndpoint('/bank-accounts/', 'Bank Accounts');
```

## Common Issues & Solutions

### 1. "No response from server"

- Make sure the Django server is running using Python 3: `python3 manage.py runserver`
- Check if the server is running on port 8000
- Verify that your backend isn't showing any error messages

### 2. CORS Issues

- Make sure `CORS_ALLOWED_ORIGINS` in Django settings includes your frontend origin (e.g., `http://localhost:3000`)
- Ensure `CORS_ALLOW_CREDENTIALS` is set to `True` in Django settings
- Check that the `corsheaders.middleware.CorsMiddleware` is included in MIDDLEWARE (before `CommonMiddleware`)

### 3. Authentication Issues

- Check if the API requires authentication
- Update the credentials in the test scripts if needed

### 4. Network or Firewall Issues

- Check if ports 8000 (backend) and 3000 (frontend) are open and accessible
- Try using `localhost` instead of `127.0.0.1` or vice versa

## Troubleshooting the Django Server

If you're having trouble starting the Django server:

1. Make sure you're using Python 3: `python3 --version`
2. Check for syntax errors in your Django settings or other Python files
3. Look for error messages when starting the server
4. Try running on a different port if 8000 is already in use: 
   ```bash
   python3 manage.py runserver 8001
   ```
   If using a different port, update the `API_URL` in the test scripts. 