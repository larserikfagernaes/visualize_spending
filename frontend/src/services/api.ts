import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import { ApiResponse, PaginatedResponse } from '../types/models';

const API_URL = 'http://localhost:8000/api/v1';

// For development only - use environment variables in production
const DEV_USERNAME = 'dev';
const DEV_PASSWORD = 'dev';

// Create axios instance with default configurations
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // For development only - add basic auth
  auth: {
    username: DEV_USERNAME,
    password: DEV_PASSWORD
  }
});

// Response interceptor for handling errors
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    const message = error.response?.data && typeof error.response.data === 'object' && 'message' in error.response.data 
      ? (error.response.data as any).message 
      : error.message;
    console.error('API Error:', message);
    return Promise.reject(error);
  }
);

/**
 * Generic GET request
 * @param url - Endpoint URL
 * @param params - Query parameters
 * @param config - Axios request config
 * @returns Promise with response data
 */
export const get = async <T>(
  url: string,
  params?: Record<string, any>,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> => {
  try {
    const response = await api.get<T>(url, { params, ...config });
    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const axiosError = error as AxiosError;
    throw {
      status: axiosError.response?.status || 500,
      message: axiosError.message,
      data: null,
    };
  }
};

/**
 * Generic POST request
 * @param url - Endpoint URL
 * @param data - Request body
 * @param config - Axios request config
 * @returns Promise with response data
 */
export const post = async <T>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> => {
  try {
    const response = await api.post<T>(url, data, config);
    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const axiosError = error as AxiosError;
    throw {
      status: axiosError.response?.status || 500,
      message: axiosError.message,
      data: null,
    };
  }
};

/**
 * Generic PUT request
 * @param url - Endpoint URL
 * @param data - Request body
 * @param config - Axios request config
 * @returns Promise with response data
 */
export const put = async <T>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> => {
  try {
    const response = await api.put<T>(url, data, config);
    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const axiosError = error as AxiosError;
    throw {
      status: axiosError.response?.status || 500,
      message: axiosError.message,
      data: null,
    };
  }
};

/**
 * Generic DELETE request
 * @param url - Endpoint URL
 * @param config - Axios request config
 * @returns Promise with response data
 */
export const del = async <T>(
  url: string,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> => {
  try {
    const response = await api.delete<T>(url, config);
    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const axiosError = error as AxiosError;
    throw {
      status: axiosError.response?.status || 500,
      message: axiosError.message,
      data: null,
    };
  }
};

export default api; 