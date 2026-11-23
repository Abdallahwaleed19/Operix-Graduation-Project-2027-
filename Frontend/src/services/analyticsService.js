import apiClient, { API_CONFIG } from './apiClient';
import {
  initialMetrics,
  initialWorkforceMetrics,
  initialWorkforceDepartments,
  initialIdleTimeZones,
  initialTrackedWorkers
} from '../data/mockData';

/**
 * Analytics & Tracking Service
 * Connects to FastAPI endpoint `/analytics`
 */
export const analyticsService = {
  async getOverviewMetrics() {
    if (API_CONFIG.useMock) {
      return initialMetrics;
    }
    return apiClient.get('/analytics/overview');
  },

  async getWorkforceMetrics(timeRange = 'week') {
    if (API_CONFIG.useMock) {
      return initialWorkforceMetrics;
    }
    return apiClient.get(`/analytics/workforce?range=${timeRange}`);
  },

  async getWorkforceDepartments() {
    if (API_CONFIG.useMock) {
      return initialWorkforceDepartments;
    }
    return apiClient.get('/analytics/workforce/departments');
  },

  async getIdleTimeZones() {
    if (API_CONFIG.useMock) {
      return initialIdleTimeZones;
    }
    return apiClient.get('/analytics/workforce/idle-zones');
  },

  async getTrackedWorkers(timeRange = 'Last 4 hours') {
    if (API_CONFIG.useMock) {
      return initialTrackedWorkers;
    }
    return apiClient.get(`/analytics/heatmaps/workers?range=${encodeURIComponent(timeRange)}`);
  }
};

export default analyticsService;
