import axios from 'axios';

// Use /api/v1 as endpoint to match the API test file
const API_URL = 'http://localhost:8000/api/v1';

// For development only - use environment variables in production
const DEV_USERNAME = 'dev';
const DEV_PASSWORD = 'dev';

// Create encoded credentials only once
const encodedCredentials = btoa(`${DEV_USERNAME}:${DEV_PASSWORD}`);

// Check if the Basic Auth is working by logging the auth header
console.log('Setting up API with Basic Auth:', `Basic ${encodedCredentials}`);

// Create axios instance with default configurations
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    // Add explicit Authorization header
    'Authorization': `Basic ${encodedCredentials}`,
    // Add CORS-specific headers to increase compatibility
    'X-Requested-With': 'XMLHttpRequest'
  },
  // Ensure credentials are sent with cross-origin requests
  withCredentials: true,
  // Add a timeout to avoid hanging requests
  timeout: 10000,
  // Explicitly set CORS mode
  mode: 'cors'
});

// Log requests for debugging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`, {
      headers: config.headers,
      baseURL: config.baseURL,
      url: config.url,
      withCredentials: config.withCredentials,
      method: config.method,
      mode: config.mode
    });
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status}`, response.data);
    return response;
  },
  (error) => {
    // Create a more descriptive error message
    let errorMessage = 'Unknown error occurred';
    let errorData = null;
    
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      const status = error.response.status;
      errorMessage = `Server error: ${status}`;
      
      console.error('Response headers:', error.response.headers);
      console.error('Request config:', error.config);
      
      if (error.response.data) {
        if (typeof error.response.data === 'string') {
          errorMessage = error.response.data;
        } else if (error.response.data.message) {
          errorMessage = error.response.data.message;
        } else if (error.response.data.detail) {
          errorMessage = error.response.data.detail;
        }
        errorData = error.response.data;
      }
    } else if (error.request) {
      // The request was made but no response was received
      errorMessage = 'No response from server. Please check if the backend is running.';
      console.error('Request was made but no response received:', error.request);
      console.error('Request config:', error.config);
      
      // Check if it's a CORS issue
      if (error.message && error.message.includes("CORS")) {
        errorMessage = 'CORS error: Cross-Origin request blocked. Check CORS settings in the backend.';
        console.error('CORS Error Details:', error.message);
      }
    } else {
      // Something happened in setting up the request that triggered an Error
      errorMessage = error.message || 'Error setting up request';
      console.error('Error setting up request:', error.message);
    }
    
    console.error('API Error:', errorMessage, error);
    
    // Create a more structured error object
    const enhancedError = {
      message: errorMessage,
      status: error.response?.status || 0,
      data: errorData,
      originalError: error
    };
    
    return Promise.reject(enhancedError);
  }
);

/**
 * Generic GET request
 * @param url - Endpoint URL
 * @param params - Query parameters
 * @param config - Axios request config
 * @returns Promise with response data
 */
export const get = async (url, params, config) => {
  try {
    const response = await api.get(url, { params, ...config });
    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    throw error; // Using the enhanced error from the interceptor
  }
};

/**
 * Generic POST request
 * @param url - Endpoint URL
 * @param data - Request body
 * @param config - Axios request config
 * @returns Promise with response data
 */
export const post = async (url, data, config) => {
  try {
    const response = await api.post(url, data, config);
    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    throw error; // Using the enhanced error from the interceptor
  }
};

/**
 * Generic PUT request
 * @param url - Endpoint URL
 * @param data - Request body
 * @param config - Axios request config
 * @returns Promise with response data
 */
export const put = async (url, data, config) => {
  try {
    const response = await api.put(url, data, config);
    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    throw error; // Using the enhanced error from the interceptor
  }
};

/**
 * Generic DELETE request
 * @param url - Endpoint URL
 * @param config - Axios request config
 * @returns Promise with response data
 */
export const del = async (url, config) => {
  try {
    const response = await api.delete(url, config);
    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    throw error; // Using the enhanced error from the interceptor
  }
};

export const clearCache = async () => {
  try {
    const response = await api.post('/clear-cache/');
    return response.data;
  } catch (error) {
    console.error('Error clearing cache:', error);
    throw error;
  }
};

export default api; 