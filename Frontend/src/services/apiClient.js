/**
 * Operix Centralized API Client
 * 
 * Provides a unified HTTP client for communicating with the FastAPI backend.
 * Fully supports the official Operix API v1 specification:
 * - Standardized envelope unwrapping: extracts payload.data from { status: "success", data, meta }
 * - Uniform error handling: extracts status, error_code, message, details from { status: "error" }
 * - Automatic Authorization: Bearer <token> and X-Factory-Id header injection
 * - Dual-mode architecture: configurable base URL and transparent mock fallback
 * - Protected binary blob downloads (for PDF/Excel reports and evidence snapshots/clips)
 */

// Safe environment resolver (works in both Vite browser environment and Node/SSR)
const env = (typeof import.meta !== 'undefined' && import.meta.env)
  ? import.meta.env
  : (typeof process !== 'undefined' && process.env)
    ? process.env
    : {};

const globalUseMock = env.VITE_USE_MOCK_DATA !== 'false';

// Central API Configuration
export const API_CONFIG = {
  baseURL: env.VITE_API_BASE_URL || 'http://localhost:8000',
  wsURL: env.VITE_WS_URL || 'ws://localhost:8000',
  useMock: globalUseMock,
  modules: {
    // Connected FastAPI modules: follow VITE_USE_MOCK_DATA (false in live mode)
    analytics: env.VITE_USE_MOCK_ANALYTICS !== undefined ? env.VITE_USE_MOCK_ANALYTICS !== 'false' : globalUseMock,
    assistant: env.VITE_USE_MOCK_ASSISTANT !== undefined ? env.VITE_USE_MOCK_ASSISTANT !== 'false' : globalUseMock,
    reports: env.VITE_USE_MOCK_REPORTS !== undefined ? env.VITE_USE_MOCK_REPORTS !== 'false' : globalUseMock,
    evidence: env.VITE_USE_MOCK_EVIDENCE !== undefined ? env.VITE_USE_MOCK_EVIDENCE !== 'false' : globalUseMock,
    rules: env.VITE_USE_MOCK_RULES !== undefined ? env.VITE_USE_MOCK_RULES !== 'false' : globalUseMock,
    websockets: env.VITE_USE_MOCK_WEBSOCKETS !== undefined ? env.VITE_USE_MOCK_WEBSOCKETS !== 'false' : globalUseMock,
    // Pending Backend Dependency modules (S-1 through S-4): stay in UI-only mock mode unless explicitly overridden
    auth: env.VITE_USE_MOCK_AUTH !== undefined ? env.VITE_USE_MOCK_AUTH !== 'false' : true,
    incidents: env.VITE_USE_MOCK_INCIDENTS !== undefined ? env.VITE_USE_MOCK_INCIDENTS !== 'false' : true,
    cameras: env.VITE_USE_MOCK_CAMERAS !== undefined ? env.VITE_USE_MOCK_CAMERAS !== 'false' : true,
    sensors: env.VITE_USE_MOCK_SENSORS !== undefined ? env.VITE_USE_MOCK_SENSORS !== 'false' : true,
    users: env.VITE_USE_MOCK_USERS !== undefined ? env.VITE_USE_MOCK_USERS !== 'false' : true,
    factory: env.VITE_USE_MOCK_FACTORY !== undefined ? env.VITE_USE_MOCK_FACTORY !== 'false' : true,
  },
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
};

/**
 * Resolves whether mock mode should be used for a specific module.
 * Ensures VITE_USE_MOCK_DATA=false only disables mocks for verified connected modules.
 */
export function isMockEnabled(moduleName) {
  if (moduleName && API_CONFIG.modules && moduleName in API_CONFIG.modules) {
    const modFlag = API_CONFIG.modules[moduleName];
    if (['auth', 'incidents', 'cameras', 'sensors', 'users', 'factory'].includes(moduleName)) {
      return modFlag;
    }
    return API_CONFIG.useMock && modFlag;
  }
  return API_CONFIG.useMock;
}

/**
 * Retrieve authorization and tenant context headers
 */
function getAuthHeaders() {
  const headers = {};
  const token = localStorage.getItem('operix_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const sessionStr = localStorage.getItem('operix_auth_session') || sessionStorage.getItem('operix_auth_session');
    if (sessionStr) {
      const session = JSON.parse(sessionStr);
      if (session?.user?.factory_id) {
        headers['X-Factory-Id'] = session.user.factory_id;
      }
    }
  } catch {}

  return headers;
}

/**
 * Build clean URL handling base URL and /api/v1 prefixes cleanly
 */
export function buildUrl(endpoint) {
  if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
    return endpoint;
  }

  const base = (API_CONFIG.baseURL || 'http://localhost:8000').replace(/\/+$/, '');
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

  // If base already contains /api/v1 and endpoint starts with /api/v1, prevent duplication
  if (base.endsWith('/api/v1') && cleanEndpoint.startsWith('/api/v1')) {
    return `${base.slice(0, -7)}${cleanEndpoint}`;
  }

  // If neither base nor endpoint has /api/v1, inject /api/v1 prefix
  if (!base.endsWith('/api/v1') && !cleanEndpoint.startsWith('/api/v1')) {
    return `${base}/api/v1${cleanEndpoint}`;
  }

  return `${base}${cleanEndpoint}`;
}

/**
 * Core HTTP Request Wrapper
 */
async function request(endpoint, options = {}) {
  const url = buildUrl(endpoint);

  const config = {
    ...options,
    headers: {
      ...API_CONFIG.headers,
      ...getAuthHeaders(),
      ...options.headers
    }
  };

  // If body is FormData, do not set application/json Content-Type (browser sets boundary)
  if (config.body instanceof FormData) {
    delete config.headers['Content-Type'];
  } else if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  try {
    const response = await fetch(url, config);

    if (response.status === 204) {
      return null;
    }

    let payload;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
    } else {
      payload = await response.text();
    }

    // Handle HTTP errors or envelope { status: "error" }
    if (!response.ok || (payload && payload.status === 'error')) {
      const message = payload?.message || payload?.detail || `HTTP Error ${response.status}`;
      const error = new Error(message);
      error.status = response.status;
      error.errorCode = payload?.error_code;
      error.details = payload?.details;
      error.data = payload;
      throw error;
    }

    // Standard Operix envelope: extract data from { status: "success", data, meta }
    if (payload && typeof payload === 'object' && payload.status === 'success' && 'data' in payload) {
      return payload.data;
    }

    return payload;
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

  /**
   * Protected binary file download with Authorization token
   */
  downloadBlob: async (endpoint, filename) => {
    const url = buildUrl(endpoint);
    const authHeaders = getAuthHeaders();
    const res = await fetch(url, { headers: authHeaders });

    if (!res.ok) {
      let errDetail = `HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        errDetail = errJson.message || errJson.detail || errDetail;
      } catch {}
      throw new Error(`Download failed: ${errDetail}`);
    }

    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    if (filename) a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    return true;
  },

  buildUrl,
  config: API_CONFIG
};

export default apiClient;
