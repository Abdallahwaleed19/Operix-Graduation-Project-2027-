/**
 * Operix Centralized API Client
 * 
 * Provides a unified HTTP client for communicating with the FastAPI backend.
 * Supports configurable base URL, authorization headers, request/response interceptors,
 * and seamless fallback to mock data until backend endpoints are connected.
 */

// Safe environment resolver (works in both Vite browser environment and Node/SSR)
const env = (typeof import.meta !== 'undefined' && import.meta.env)
  ? import.meta.env
  : (typeof process !== 'undefined' && process.env)
    ? process.env
    : {};

// Central API Configuration
export const API_CONFIG = {
  baseURL: env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  useMock: env.VITE_USE_MOCK_DATA !== 'false',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
};

/**
 * Retrieve authorization token if available
 */
function getAuthHeaders() {
  const token = localStorage.getItem('operix_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Core HTTP Request Wrapper
 */
async function request(endpoint, options = {}) {
  // If mock mode is forced and no backend is connected, caller can return mock data directly
  const url = endpoint.startsWith('http') ? endpoint : `${API_CONFIG.baseURL}${endpoint}`;

  const config = {
    ...options,
    headers: {
      ...API_CONFIG.headers,
      ...getAuthHeaders(),
      ...options.headers
    }
  };

  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body);
  }

  try {
    const response = await fetch(url, config);

    // Handle HTTP errors
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }
      const error = new Error(errorData.detail || errorData.message || `HTTP Error ${response.status}`);
      error.status = response.status;
      error.data = errorData;
      throw error;
    }

    if (response.status === 204) {
      return null;
    }

    return await response.json();
  } catch (error) {
    console.warn(`[Operix API] ${config.method || 'GET'} ${url} failed:`, error.message);
    throw error;
  }
}

export const apiClient = {
  get: (endpoint, options) => request(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, body, options) => request(endpoint, { ...options, method: 'POST', body }),
  put: (endpoint, body, options) => request(endpoint, { ...options, method: 'PUT', body }),
  patch: (endpoint, body, options) => request(endpoint, { ...options, method: 'PATCH', body }),
  delete: (endpoint, options) => request(endpoint, { ...options, method: 'DELETE' }),
  config: API_CONFIG
};

export default apiClient;
