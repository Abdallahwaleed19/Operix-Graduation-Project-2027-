import apiClient, { API_CONFIG } from './apiClient';
import { initialIncidents, initialShiftIncidents } from '../data/mockData';

/**
 * Incidents Service
 * Connects to FastAPI endpoint `/incidents`
 */
export const incidentService = {
  /**
   * Fetch all incidents with optional filtering
   */
  async getIncidents(filters = {}) {
    if (API_CONFIG.useMock) {
      let result = [...initialIncidents];
      if (filters.status && filters.status !== 'All') {
        result = result.filter(i => i.status.toLowerCase() === filters.status.toLowerCase());
      }
      if (filters.severity && filters.severity !== 'All') {
        result = result.filter(i => i.severity.toLowerCase() === filters.severity.toLowerCase());
      }
      return result;
    }
    const params = new URLSearchParams(filters).toString();
    return apiClient.get(`/incidents${params ? `?${params}` : ''}`);
  },

  /**
   * Get single incident by ID
   */
  async getIncidentById(id) {
    if (API_CONFIG.useMock) {
      return initialIncidents.find(i => i.id === id) || null;
    }
    return apiClient.get(`/incidents/${id}`);
  },

  /**
   * Mark an incident as resolved
   */
  async resolveIncident(id) {
    if (API_CONFIG.useMock) {
      const inc = initialIncidents.find(i => i.id === id);
      if (inc) {
        inc.status = 'Resolved';
        inc.auditTrail.push({
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: 'Resolved by user',
          detail: 'Marked as resolved in dashboard'
        });
      }
      return { success: true, id };
    }
    return apiClient.post(`/incidents/${id}/resolve`);
  },

  /**
   * Fetch incident distribution along current shift
   */
  async getShiftIncidents() {
    if (API_CONFIG.useMock) {
      return initialShiftIncidents;
    }
    return apiClient.get('/analytics/shift-incidents');
  }
};

export default incidentService;
