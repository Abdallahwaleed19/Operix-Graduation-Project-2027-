import apiClient, { isMockEnabled } from './apiClient.js';
import {
  initialMetrics,
  initialWorkforceMetrics,
  initialWorkforceDepartments,
  initialIdleTimeZones,
  initialTrackedWorkers
} from '../data/mockData.js';

/**
 * Workforce Analytics & Platform Metrics Service
 * Connects directly to FastAPI endpoints under `/api/v1/analytics`
 */
export const analyticsService = {
  /**
   * GET /api/v1/analytics/overview
   * Returns worker totals and role distribution
   */
  async getOverview() {
    if (isMockEnabled('analytics')) {
      return {
        total_workers: 24,
        active_workers: 22,
        inactive_workers: 2,
        role_breakdown: { operator: 18, safety_supervisor: 4, factory_manager: 2 }
      };
    }
    return apiClient.get('/api/v1/analytics/overview');
  },

  /**
   * GET /api/v1/analytics/summary?period_hours=720
   * Consolidated dashboard summary payload
   */
  async getSummary(options = {}) {
    const periodHours = options.periodHours || options.period_hours || 720;
    if (isMockEnabled('analytics')) {
      return {
        period_hours: periodHours,
        total_workers: 24,
        active_workers: 22,
        incidents_count: 5,
        resolved_incidents: 4,
        camera_coverage_pct: 98.2,
        average_resolution_minutes: 14.5
      };
    }
    const q = new URLSearchParams({ period_hours: String(periodHours) });
    if (options.startDate || options.start_date) q.set('start_date', options.startDate || options.start_date);
    if (options.endDate || options.end_date) q.set('end_date', options.endDate || options.end_date);
    return apiClient.get(`/api/v1/analytics/summary?${q}`);
  },

  /**
   * GET /api/v1/analytics/attendance
   * Attendance and worker activity metrics
   */
  async getAttendance(options = {}) {
    if (isMockEnabled('analytics')) {
      return initialWorkforceDepartments;
    }
    const q = new URLSearchParams();
    if (options.startDate || options.start_date) q.set('start_date', options.startDate || options.start_date);
    if (options.endDate || options.end_date) q.set('end_date', options.endDate || options.end_date);
    return apiClient.get(`/api/v1/analytics/attendance${q.toString() ? `?${q}` : ''}`);
  },

  /**
   * GET /api/v1/analytics/incidents
   * Incident counts, resolution rates, severity/state distributions
   */
  async getIncidents(options = {}) {
    if (isMockEnabled('analytics')) {
      return initialWorkforceMetrics;
    }
    const q = new URLSearchParams();
    if (options.startDate || options.start_date) q.set('start_date', options.startDate || options.start_date);
    if (options.endDate || options.end_date) q.set('end_date', options.endDate || options.end_date);
    return apiClient.get(`/api/v1/analytics/incidents${q.toString() ? `?${q}` : ''}`);
  },

  /**
   * GET /api/v1/analytics/productivity
   * Worker resolution and productivity stats
   */
  async getProductivity(options = {}) {
    if (isMockEnabled('analytics')) {
      return initialIdleTimeZones;
    }
    const q = new URLSearchParams();
    if (options.lowThreshold !== undefined) q.set('low_threshold', String(options.lowThreshold));
    if (options.highThreshold !== undefined) q.set('high_threshold', String(options.highThreshold));
    return apiClient.get(`/api/v1/analytics/productivity${q.toString() ? `?${q}` : ''}`);
  },

  /**
   * GET /api/v1/analytics/camera-coverage?period_hours=720
   * Camera coverage and uptime metrics
   */
  async getCameraCoverage(periodHours = 720) {
    if (isMockEnabled('analytics')) {
      return { uptime_percentage: 98.5, active_cameras: 12, total_cameras: 12 };
    }
    return apiClient.get(`/api/v1/analytics/camera-coverage?period_hours=${periodHours}`);
  },

  // -------------------------------------------------------------
  // UI Helper Wrappers for existing dashboard components
  // -------------------------------------------------------------

  async getOverviewMetrics() {
    if (isMockEnabled('analytics')) return initialMetrics;
    try {
      const summary = await this.getSummary();
      return {
        ...initialMetrics,
        workforce: {
          totalWorkers: summary.total_workers || 24,
          activeWorkers: summary.active_workers || 22,
          safetyCompliance: summary.camera_coverage_pct || 94.2
        }
      };
    } catch {
      return initialMetrics;
    }
  },

  async getWorkforceMetrics(timeRange = 'week') {
    if (isMockEnabled('analytics')) return initialWorkforceMetrics;
    try {
      return await this.getIncidents();
    } catch {
      return initialWorkforceMetrics;
    }
  },

  async getWorkforceDepartments() {
    if (isMockEnabled('analytics')) return initialWorkforceDepartments;
    try {
      return await this.getAttendance();
    } catch {
      return initialWorkforceDepartments;
    }
  },

  async getIdleTimeZones() {
    if (isMockEnabled('analytics')) return initialIdleTimeZones;
    try {
      return await this.getProductivity();
    } catch {
      return initialIdleTimeZones;
    }
  },

  async getTrackedWorkers(timeRange = 'Last 4 hours') {
    return initialTrackedWorkers;
  }
};

export default analyticsService;
